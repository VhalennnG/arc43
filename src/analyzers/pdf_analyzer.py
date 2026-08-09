import os
import re
from typing import List, Literal, Dict, Any
from pypdf import PdfReader
from src.analyzers.base import AbstractAnalyzer
from src.fields.models import FormField, FieldType

class PDFAnalyzer(AbstractAnalyzer):
    """
    Layout analyzer for PDF documents.
    Determines if a document is an AcroForm or static PDF, and extracts input fields.
    """

    def detect_form_type(self, file_path: str) -> Literal["acroform", "static"]:
        """
        Determines form type by checking if interactive fields are present (A4).
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")
            
        try:
            reader = PdfReader(file_path)
            fields = reader.get_fields()
            return "acroform" if fields else "static"
        except Exception as e:
            print(f"Error detecting PDF form type: {e}")
            return "static"

    def clean_label(self, text: str) -> str:
        text = re.sub(r'[:：_．\.\-\s]+$', '', text)
        return text.strip()

    def analyze_static_pdf(self, file_path: str) -> List[FormField]:
        """
        Extracts candidate fields from a static PDF using label-anchoring heuristics (A5).
        """
        import pdfplumber
        fields = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_idx, page in enumerate(pdf.pages):
                    page_num = page_idx + 1
                    words = page.extract_words()
                    if not words:
                        continue
                        
                    # Group words into lines by matching vertical coordinates (within 3 points)
                    lines_dict: Dict[int, List[Dict[str, Any]]] = {}
                    for w in words:
                        top_rounded = int(w["top"] / 3) * 3
                        if top_rounded not in lines_dict:
                            lines_dict[top_rounded] = []
                        lines_dict[top_rounded].append(w)
                        
                    # Process each line sorted by top coordinate
                    for top_y in sorted(lines_dict.keys()):
                        line_words = sorted(lines_dict[top_y], key=lambda w: w["x0"])
                        
                        # Find colons or label text
                        for idx, w in enumerate(line_words):
                            text = w["text"].strip()
                            
                            # Heuristic: if word ends with a colon, or the next word is a colon
                            has_colon = False
                            label_word_count = 1
                            
                            if text.endswith(":") or text.endswith("："):
                                has_colon = True
                            elif idx < len(line_words) - 1 and line_words[idx + 1]["text"].strip() in (":", "："):
                                has_colon = True
                                label_word_count = 2
                                
                            if has_colon:
                                # Candidate label found. Reconstruct label from preceding words in same line
                                # Let's combine preceding words that are close by
                                label_parts = []
                                for k in range(max(0, idx - 3), idx + 1):
                                    label_parts.append(line_words[k]["text"])
                                    
                                raw_label = " ".join(label_parts)
                                label = self.clean_label(raw_label)
                                if not label:
                                    continue
                                    
                                # Calculate bbox for input field immediately to the right of this label
                                last_label_word = line_words[idx + label_word_count - 1]
                                x0_field = last_label_word["x1"] + 5
                                
                                # Default right boundary to page width minus margin
                                x1_field = page.width - 50
                                
                                # If there is a next word on the same line, stop the field before it
                                next_word_idx = idx + label_word_count
                                if next_word_idx < len(line_words):
                                    next_word_x0 = line_words[next_word_idx]["x0"]
                                    # Only bound it if the next word is far enough to represent a new label
                                    if next_word_x0 > x0_field + 20:
                                        x1_field = next_word_x0 - 5
                                        
                                # Bounding box coordinates: (x0, top, x1, bottom)
                                bbox = (x0_field, w["top"], x1_field, w["bottom"])
                                
                                fields.append(FormField(
                                    id=f"page_{page_num}_bbox_{int(x0_field)}_{int(w['top'])}",
                                    label=label,
                                    field_type=FieldType.TEXT,
                                    page=page_num,
                                    bbox=bbox,
                                    metadata={"form_type": "static", "page_height": page.height}
                                ))
        except Exception as e:
            print(f"Error parsing static PDF layout with pdfplumber: {e}")
            
        return fields

    def analyze(self, file_path: str) -> List[FormField]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF template not found: {file_path}")
            
        form_type = self.detect_form_type(file_path)
        if form_type == "acroform":
            reader = PdfReader(file_path)
            pdf_fields = reader.get_fields() or {}
            fields = []
            
            for key, field_dict in pdf_fields.items():
                ft = field_dict.get("/FT", "")
                field_type = FieldType.TEXT
                checkbox_kind = None
                
                if ft == "/Btn":
                    field_type = FieldType.CHECKBOX
                    checkbox_kind = "acroform"
                    
                field = FormField(
                    id=key,
                    label=key,
                    field_type=field_type,
                    checkbox_kind=checkbox_kind,
                    metadata={
                        "form_type": "acroform",
                        "pdf_field_name": key,
                        "field_dict": str(field_dict)
                    }
                )
                fields.append(field)
            return fields
        else:
            return self.analyze_static_pdf(file_path)
