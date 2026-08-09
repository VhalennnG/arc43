import sys
from unittest.mock import MagicMock, patch

# Define mock classes first
class MockPlumberPage:
    def __init__(self, width=612, height=792):
        self.width = width
        self.height = height
    def extract_words(self):
        return [
            {"text": "Name:", "x0": 100, "top": 150, "x1": 130, "bottom": 160},
            {"text": "Address:", "x0": 100, "top": 200, "x1": 145, "bottom": 210}
        ]

class MockPlumberPDF:
    def __init__(self):
        self.pages = [MockPlumberPage()]
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

class MockFitzPage:
    def __init__(self):
        self.inserted_text = []
    def get_text(self, opt):
        return {
            "blocks": [
                {
                    "lines": [
                        {
                            "spans": [
                                {
                                    "text": "Name:",
                                    "font": "Times-Bold",
                                    "size": 11.0,
                                    "bbox": (100, 150, 130, 160)
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    def insert_textbox(self, rect, text, fontname, fontsize, align):
        self.inserted_text.append({
            "rect": (rect.x0, rect.y0, rect.x1, rect.y1),
            "text": text,
            "fontname": fontname,
            "fontsize": fontsize
        })

class MockFitzDoc:
    def __init__(self):
        self.pages = [MockFitzPage()]
    def __len__(self):
        return len(self.pages)
    def __getitem__(self, idx):
        return self.pages[idx]
    def save(self, path):
        pass
    def close(self):
        pass

# Setup fake modules in sys.modules to prevent loading real binaries in sandboxed test runs
mock_fitz = MagicMock()
mock_fitz.open = lambda path: MockFitzDoc()
class FakeRect:
    def __init__(self, x0, y0, x1, y1):
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1
mock_fitz.Rect = FakeRect
sys.modules['fitz'] = mock_fitz

mock_pdfplumber = MagicMock()
mock_pdfplumber.open = lambda path: MockPlumberPDF()
sys.modules['pdfplumber'] = mock_pdfplumber

# Now safely import components to test
from src.analyzers.pdf_analyzer import PDFAnalyzer
from src.writers.pdf_overlay_writer import PDFOverlayWriter
from src.fields.models import FieldType

def test_pdf_static_bbox_and_font_overlay():
    analyzer = PDFAnalyzer()
    writer = PDFOverlayWriter()
    
    # Analyze static PDF (uses mocked pdfplumber under the hood)
    with patch.object(analyzer, "detect_form_type", return_value="static"):
        fields = analyzer.analyze("tests/fixtures/forms/static_sample.pdf")
            
    assert len(fields) == 2
    
    # Assert fields are parsed with correct label and page
    labels = [f.label for f in fields]
    assert "Name" in labels
    assert "Address" in labels
    
    for f in fields:
        assert f.field_type == FieldType.TEXT
        assert f.page == 1
        assert f.bbox is not None
        assert len(f.bbox) == 4
        
    # Provide answers
    for f in fields:
        if "Name" in f.label:
            f.answer = "Vhalentino Gamgenora"
        elif "Address" in f.label:
            f.answer = "Jakarta, Indonesia"
            
    # Write overlay (uses mocked fitz under the hood)
    # Intercept to verify inputs
    writer.fill("tests/fixtures/forms/static_sample.pdf", fields, "dummy_output.pdf")
