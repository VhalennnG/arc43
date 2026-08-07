import os
from typing import List, Dict, Any

def detect_fields(form_path: str) -> List[Dict[str, Any]]:
    """
    Detects input fields in a target form file based on its extension.
    Returns a list of dicts: [{'id': field_id, 'label': field_label, 'value': current_value}]
    (To be implemented in later stages)
    """
    ext = os.path.splitext(form_path)[1].lower()
    print(f"Detecting fields for form: {form_path} ({ext})")
    
    # Mock return values for verification baseline
    return [
        {"id": "field_name", "label": "Nama Lengkap", "value": ""},
        {"id": "field_nik", "label": "NIK", "value": ""},
        {"id": "field_address", "label": "Alamat", "value": ""}
    ]

def fill_form(form_path: str, fields_data: Dict[str, str], output_path: str) -> str:
    """
    Fills the detected fields back into a copy of the original form.
    Returns the path to the generated file.
    (To be implemented in later stages)
    """
    # Simple mock copy or dummy write for baseline setup
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"MOCK FILL OUTPUT for {os.path.basename(form_path)}\n")
        for k, v in fields_data.items():
            f.write(f"{k} = {v}\n")
            
    print(f"Generated filled form output at: {output_path}")
    return output_path
