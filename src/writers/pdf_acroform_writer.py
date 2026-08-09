import os
from typing import List
from pypdf import PdfReader, PdfWriter
from src.writers.base import DocumentWriter
from src.fields.models import FormField, FieldType

class PDFAcroFormWriter(DocumentWriter):
    """
    Writer for PDF AcroForms (interactive PDF documents).
    Fills in form field values programmatically without altering the document layout.
    Derives checkbox export values dynamically from the field's /_States_ list (#8).
    """

    def is_checked(self, field: FormField) -> bool:
        if not field.answer:
            return False
        ans_str = str(field.answer).strip().lower()
        label_str = field.label.strip().lower()
        return ans_str == label_str or ans_str in ("yes", "true", "1", "ya", "checked")

    def fill(self, source_path: str, fields: List[FormField], output_path: str) -> None:
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"PDF template not found: {source_path}")
            
        reader = PdfReader(source_path)
        writer = PdfWriter()
        writer.append(reader)
        
        # Pre-read all field definitions to derive checkbox export values
        pdf_fields = reader.get_fields() or {}
        
        # Build dictionary of fields to fill
        field_values = {}
        for field in fields:
            if field.answer is None:
                continue
                
            pdf_field_name = field.metadata.get("pdf_field_name", field.id)
            
            if field.field_type == FieldType.CHECKBOX:
                checked = self.is_checked(field)
                if checked:
                    # Derive the actual export value from the field's /_States_ list (#8)
                    field_dict = pdf_fields.get(pdf_field_name, {})
                    states = []
                    if hasattr(field_dict, 'get'):
                        states = field_dict.get("/_States_", [])
                    on_value = next((s for s in states if s != "/Off"), "/Yes")
                    field_values[pdf_field_name] = on_value
                else:
                    field_values[pdf_field_name] = "/Off"
            else:
                field_values[pdf_field_name] = str(field.answer)
                
        # Update values on all pages
        for page in writer.pages:
            writer.update_page_form_field_values(page, field_values)
            
        with open(output_path, "wb") as f:
            writer.write(f)
