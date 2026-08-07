import os
import shutil
import json
from datetime import datetime
from typing import List, Dict, Any
from fastapi import FastAPI, Request, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src import db, ocr, llm, parsers, fillers

# Initialize database
db.init_db()

# Initialize FastAPI
app = FastAPI(title="arc43 - Auto-Fill Form 100% On-Device")

# Setup static files directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "css"), exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "js"), exist_ok=True)

# Mount static folder
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Templates
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

def _try_repair_json(raw: str):
    """
    Attempt to repair truncated JSON array output from LLM.
    Returns the parsed list on success, or None if repair is not possible.
    """
    # Only attempt repair on arrays
    if not raw.startswith("["):
        return None
    
    # Strategy: find the last complete object "}" and close the array
    last_brace = raw.rfind("}")
    if last_brace == -1:
        return None
    
    candidate = raw[:last_brace + 1].rstrip().rstrip(",") + "\n]"
    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass
    return None

@app.get("/")
async def root():
    """Redirect to Tab 1 by default."""
    return RedirectResponse(url="/tab1")

@app.get("/tab1", response_class=HTMLResponse)
async def tab1(request: Request):
    """Render Tab 1 — Knowledge Base."""
    records = db.list_records()
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request=request, name="tab1.html", context={"records": records})
    return templates.TemplateResponse(request=request, name="tab1_full.html", context={"records": records, "active_tab": "tab1"})

@app.get("/tab2", response_class=HTMLResponse)
async def tab2(request: Request):
    """Render Tab 2 — Fill Form."""
    records = db.list_records()
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request=request, name="tab2.html", context={"records": records})
    return templates.TemplateResponse(request=request, name="tab2_full.html", context={"records": records, "active_tab": "tab2"})

@app.post("/upload-doc")
async def upload_doc(request: Request, file: UploadFile = File(...)):
    """Upload a document to Knowledge Base, perform local parser/OCR and local LLM extraction."""
    temp_dir = os.path.join(db.DATA_DIR, "temp_uploads")
    os.makedirs(temp_dir, exist_ok=True)
    
    file_path = os.path.join(temp_dir, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    db.log_process(file.filename, "FILE_UPLOADED", {"temp_path": file_path})
        
    try:
        # Determine extraction method
        ext = os.path.splitext(file.filename)[1].lower()
        if ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff"):
            # Run local macOS Vision OCR
            raw_text = ocr.recognize_text(file_path)
            source_type = "image"
            extraction_method = "ocr"
        else:
            # Parse text programmatically
            doc_data = parsers.parse_document(file_path)
            raw_text = doc_data["raw_text"]
            source_type = doc_data["source_type"]
            extraction_method = doc_data["extraction_method"]
            
        db.log_process(file.filename, "TEXT_EXTRACTED", {
            "source_type": source_type,
            "extraction_method": extraction_method,
            "raw_text": raw_text
        })
            
        fields = []
        # If GGUF LLM model is available, structure raw text into fields
        if raw_text.strip() and os.path.exists(llm.LLM_PATH):
            prompt = (
                "You are a data extraction assistant. Extract individual key-value pairs from the raw text below.\n\n"
                "RULES:\n"
                "1. Each piece of information MUST be its own separate object.\n"
                "2. Use SHORT, specific labels. Do NOT combine multiple items into one value.\n"
                "3. Extract values VERBATIM from the text. Do not summarize, translate, or guess.\n"
                "4. If no clear label-value patterns are found, return an empty JSON array [].\n"
                "5. Output ONLY a valid JSON array — no markdown, no explanations, no extra text.\n\n"
                "EXAMPLE of correct output:\n"
                "[\n"
                '  {"label": "Name", "value": "John Doe"},\n'
                '  {"label": "Email", "value": "john@example.com"},\n'
                '  {"label": "Phone", "value": "+62 812-3456-7890"},\n'
                '  {"label": "Position", "value": "Software Engineer"},\n'
                '  {"label": "Company", "value": "PT Example"},\n'
                '  {"label": "Period", "value": "01/2023 - 12/2023"},\n'
                '  {"label": "Education", "value": "Informatics, Universitas Example"},\n'
                '  {"label": "GPA", "value": "3.84 / 4.0"}\n'
                "]\n\n"
                f"Raw Text:\n---\n{raw_text}\n---\n\n"
                "JSON Output:"
            )
            db.log_process(file.filename, "LLM_EXTRACTION_PROMPT", {"prompt": prompt})
            
            llm_output = ""
            try:
                llm_output = llm.generate_text(prompt)
                llm_output = llm_output.strip()
                # Clean any markdown block wrappers if generated
                if llm_output.startswith("```json"):
                    llm_output = llm_output[7:]
                elif llm_output.startswith("```"):
                    llm_output = llm_output[3:]
                if llm_output.endswith("```"):
                    llm_output = llm_output[:-3]
                llm_output = llm_output.strip()
                
                # Strategy D: Attempt JSON repair if parsing fails
                try:
                    extracted = json.loads(llm_output)
                except json.JSONDecodeError:
                    repaired = _try_repair_json(llm_output)
                    if repaired is not None:
                        extracted = repaired
                        db.log_process(file.filename, "JSON_REPAIR_SUCCESS", {
                            "original_output": llm_output,
                            "repaired_result_count": len(extracted) if isinstance(extracted, list) else 0
                        })
                    else:
                        raise
                
                if isinstance(extracted, list):
                    for item in extracted:
                        if isinstance(item, dict) and "label" in item and "value" in item:
                            fields.append({
                                "label": str(item["label"]),
                                "value": str(item["value"])
                            })
                db.log_process(file.filename, "LLM_EXTRACTION_SUCCESS", {
                    "raw_output": llm_output,
                    "extracted_fields": fields
                })
            except Exception as e:
                print(f"Error parsing LLM extraction output: {e}")
                db.log_process(file.filename, "LLM_EXTRACTION_FAILED", {
                    "raw_output": llm_output,
                    "error": str(e)
                })
                
        # Save record
        saved_rec = db.save_record(
            filename=file.filename,
            source_type=source_type,
            extraction_method=extraction_method,
            raw_text=raw_text,
            fields=fields
        )
        db.log_process(file.filename, "RECORD_SAVED", {
            "record_id": saved_rec["id"],
            "saved_fields_count": len(fields)
        })
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
            
    records = db.list_records()
    return templates.TemplateResponse(request=request, name="tab1.html", context={"records": records})

@app.delete("/delete-doc/{record_id}")
async def delete_doc(request: Request, record_id: str):
    """Delete a document from Knowledge Base."""
    db.delete_record(record_id)
    records = db.list_records()
    return templates.TemplateResponse(request=request, name="tab1.html", context={"records": records})

@app.post("/process-form")
async def process_form(
    request: Request,
    selected_sources: List[str] = Form([]),
    form_file: UploadFile = File(...)
):
    """Detect fields in target form and match them against selected source documents using Local AI."""
    temp_dir = os.path.join(db.DATA_DIR, "temp_uploads")
    os.makedirs(temp_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    target_filename = f"target_{timestamp}_{form_file.filename}"
    file_path = os.path.join(temp_dir, target_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(form_file.file, buffer)
        
    try:
        # Detect fields in target form template
        detected = fillers.detect_fields(file_path)
        
        # Load selected source records
        records = []
        for src_id in selected_sources:
            rec = db.get_record(src_id)
            if rec:
                records.append(rec)
                
        # Sort by uploaded_at ascending so later files override earlier ones (chronological resolution)
        records.sort(key=lambda r: r.get("uploaded_at", ""))
        
        fields_with_values = []
        for field in detected:
            field_id = field["id"]
            field_label = field["label"]
            matched_value = ""
            
            # Layer 1: Look up exact label match in pre-structured fields
            for rec in records:
                for f in rec.get("fields", []):
                    if f.get("label", "").strip().lower() == field_label.strip().lower():
                        matched_value = f.get("value", "")
                        
            # Layer 2: Fallback to searching verbatim raw_text using LLM
            if not matched_value and os.path.exists(llm.LLM_PATH):
                context_texts = []
                for rec in records:
                    context_texts.append(f"Source file: {rec['original_filename']}\n{rec['raw_text']}")
                context_str = "\n\n".join(context_texts)
                
                if context_str.strip():
                    prompt = (
                        "You are an AI assistant helping to auto-fill form fields.\n"
                        f"Based ONLY on the context documents below, retrieve the value for the form field: '{field_label}'.\n"
                        "Rules:\n"
                        "- Extract the exact value verbatim. Do not summarize, do not guess, do not add filler words.\n"
                        "- If the value is not explicitly present in the context, output only the word: EMPTY\n"
                        "- Do not output any explanation, markdown, or intros.\n\n"
                        f"Context Documents:\n---\n{context_str}\n---\n\n"
                        f"Value for '{field_label}':"
                    )
                    try:
                        llm_val = llm.generate_text(prompt, max_tokens=128, temperature=0.1).strip()
                        if llm_val.upper() != "EMPTY":
                            matched_value = llm_val
                    except Exception as e:
                        print(f"Error matching field '{field_label}' with LLM: {e}")
                        
            fields_with_values.append({
                "id": field_id,
                "label": field_label,
                "value": matched_value
            })
            
        all_records = db.list_records()
        return templates.TemplateResponse(request=request, name="tab2.html", context={
            "records": all_records,
            "fields": fields_with_values,
            "form_filename": target_filename,
            "selected_sources": selected_sources
        })
        
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Failed to process form: {e}")

@app.post("/generate-output")
async def generate_output(
    request: Request,
    form_filename: str = Form(...),
    selected_sources: List[str] = Form([])
):
    """Write user-reviewed field values back to form template copy."""
    temp_dir = os.path.join(db.DATA_DIR, "temp_uploads")
    form_path = os.path.join(temp_dir, form_filename)
    
    if not os.path.exists(form_path):
        raise HTTPException(status_code=400, detail="Form template session expired.")
        
    form_data = await request.form()
    fields_to_fill = {}
    for key, value in form_data.items():
        if key.startswith("field_"):
            field_id = key[6:]
            fields_to_fill[field_id] = str(value)
            
    output_dir = os.path.join(db.DATA_DIR, "outputs")
    os.makedirs(output_dir, exist_ok=True)
    
    # Extract original name (skip target_timestamp_)
    original_name = form_filename.split("_", 2)[-1]
    output_filename = f"filled_{original_name}"
    output_path = os.path.join(output_dir, output_filename)
    
    try:
        fillers.fill_form(form_path, fields_to_fill, output_path)
    finally:
        if os.path.exists(form_path):
            os.remove(form_path)
            
    all_records = db.list_records()
    return templates.TemplateResponse(request=request, name="tab2.html", context={
        "records": all_records,
        "output_file": output_filename
    })

@app.get("/download-file/{filename}")
async def download_file(filename: str):
    """Serve filled output files for download."""
    output_path = os.path.join(db.DATA_DIR, "outputs", filename)
    if not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(output_path, filename=filename)
