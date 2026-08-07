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
            
        # Classify document category using LLM (one sentence)
        category = ""
        if raw_text.strip() and os.path.exists(llm.LLM_PATH):
            prompt = (
                "Kamu bertugas membuat SATU kalimat singkat yang mendeskripsikan JENIS/KATEGORI dari dokumen berikut. "
                "Deskripsi ini akan dipakai sebagai clue konteks oleh sistem lain nantinya, BUKAN untuk meringkas isinya.\n\n"
                "ATURAN KETAT:\n"
                "1. Jawab HANYA dengan satu kalimat deskripsi kategori — tidak lebih, tidak ada penjelasan tambahan.\n"
                "2. JANGAN meringkas isi dokumen atau menyebutkan data spesifik di dalamnya "
                "(nama orang, tanggal, angka, alamat, dll). Cukup JENIS dokumennya secara umum.\n"
                "3. JANGAN pakai tanda kutip, markdown, atau format tambahan apapun. Teks polos saja.\n"
                "4. Gunakan Bahasa Indonesia, meskipun isi dokumennya berbahasa lain.\n"
                "5. Kalau dokumennya berisi campuran beberapa jenis informasi, sebutkan semuanya secara singkat.\n\n"
                "Contoh jawaban yang benar:\n"
                "- Data pribadi berupa KTP (Kartu Tanda Penduduk)\n"
                "- Data riwayat pekerjaan, pendidikan, dan pencapaian profesional (CV/Resume)\n"
                "- Data NPWP (Nomor Pokok Wajib Pajak) perusahaan\n"
                "- Daftar menu makanan dan harga\n"
                "- Data akta kelahiran\n\n"
                f"DOKUMEN:\n---\n{raw_text}\n---\n\n"
                "Kategori dokumen ini:"
            )
            db.log_process(file.filename, "LLM_CATEGORY_PROMPT", {"prompt": prompt})
            
            try:
                llm_output = llm.generate_text(prompt, max_tokens=128)
                category = llm_output.strip()
                # Clean up: take only the first line (in case model outputs more)
                category = category.split("\n")[0].strip()
                # Remove leading dash/bullet if present
                if category.startswith("- "):
                    category = category[2:]
                db.log_process(file.filename, "LLM_CATEGORY_SUCCESS", {
                    "raw_output": llm_output,
                    "category": category
                })
            except Exception as e:
                print(f"Error classifying document: {e}")
                db.log_process(file.filename, "LLM_CATEGORY_FAILED", {
                    "error": str(e)
                })
                
        # Save record as .txt (category + raw_text)
        saved_rec = db.save_record(
            filename=file.filename,
            source_type=source_type,
            extraction_method=extraction_method,
            raw_text=raw_text,
            category=category
        )
        db.log_process(file.filename, "RECORD_SAVED", {
            "record_id": saved_rec["id"],
            "category": category
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
            
            # Match field value using LLM with category-prefixed source context
            if os.path.exists(llm.LLM_PATH):
                context_texts = []
                for rec in records:
                    category_line = rec.get("category", "")
                    raw = rec.get("raw_text", "")
                    header = f"[{category_line}] " if category_line else ""
                    context_texts.append(f"{header}Source: {rec.get('original_filename', '')}\n{raw}")
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
                        llm_val = llm.generate_text(prompt, max_tokens=128).strip()
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
