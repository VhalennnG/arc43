import pytest
from src.analyzers.pdf_analyzer import PDFAnalyzer
from src.fields.models import FieldType

def test_pdf_form_type_detection():
    analyzer = PDFAnalyzer()
    
    # 1. Verify acroform_sample.pdf is detected as 'acroform'
    assert analyzer.detect_form_type("tests/fixtures/forms/acroform_sample.pdf") == "acroform"
    
    # 2. Verify static_sample.pdf is detected as 'static'
    assert analyzer.detect_form_type("tests/fixtures/forms/static_sample.pdf") == "static"

def test_acroform_fields_extracted():
    analyzer = PDFAnalyzer()
    fields = analyzer.analyze("tests/fixtures/forms/acroform_sample.pdf")
    
    # We should have extracted 'full_name' and 'email'
    assert len(fields) == 2
    labels = [f.label for f in fields]
    assert "full_name" in labels
    assert "email" in labels
    
    for f in fields:
        assert f.field_type == FieldType.TEXT
        assert f.metadata["form_type"] == "acroform"
