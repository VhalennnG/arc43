import pytest
from src.analyzers.docx_analyzer import DocxAnalyzer
from src.fields.models import FieldType

def test_docx_detection_on_peepl_biodata():
    doc_path = "tests/fixtures/forms/peepl_biodata.docx"
    analyzer = DocxAnalyzer()
    
    fields = analyzer.analyze(doc_path)
    
    # Assert we found fields
    assert len(fields) > 0
    
    # Check text fields in tables/paragraphs
    text_labels = [f.label for f in fields if f.field_type == FieldType.TEXT]
    
    # Verify that the core text fields are detected (using substring checks because of multi-language labels)
    assert any("Nama Lengkap" in lbl for lbl in text_labels)
    assert any("Alamat" in lbl for lbl in text_labels)
    assert any("Kota" in lbl for lbl in text_labels)
    
    # Check checkboxes in tables
    checkboxes = [f for f in fields if f.field_type == FieldType.CHECKBOX]
    assert len(checkboxes) > 0
    
    # In peepl_biodata.docx, checkboxes are cell-based (empty cell with border next to choice label)
    cell_checkboxes = [f for f in checkboxes if f.checkbox_kind == "cell"]
    assert len(cell_checkboxes) > 0
    
    checkbox_labels = [f.label for f in cell_checkboxes]
    assert any("Laki-laki" in lbl for lbl in checkbox_labels)
    assert any("Perempuan" in lbl for lbl in checkbox_labels)
    assert any("WNI" in lbl for lbl in checkbox_labels)
    assert any("WNA" in lbl for lbl in checkbox_labels)
