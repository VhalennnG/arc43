import sys
from unittest.mock import MagicMock, patch

# Define Mock openpyxl classes to bypass sandbox lxml library blocks
class MockCell:
    def __init__(self, row, column, value=None):
        self.row = row
        self.column = column
        self.value = value
        
        # Determine standard coordinate name (e.g. B2, C2, B4, B5)
        col_letter = chr(64 + column)
        self.coordinate = f"{col_letter}{row}"

class MockWorksheet:
    def __init__(self, title="Form Sheet"):
        self.title = title
        self.max_row = 10
        self.max_column = 10
        self._cells = {}
        for r in range(1, 11):
            for c in range(1, 11):
                self._cells[(r, c)] = MockCell(r, c)
                
        # Inject standard test labels
        self._cells[(2, 2)].value = "Nama Lengkap:"
        self._cells[(4, 2)].value = "Alamat:"
        self._cells[(4, 3)].value = 1  # Numeric value blocks horizontal match without being treated as a label
        
    def cell(self, row, column):
        return self._cells[(row, column)]

class MockWorkbook:
    def __init__(self):
        self.worksheets = [MockWorksheet()]
        self.sheetnames = ["Form Sheet"]
        
    def __getitem__(self, name):
        return self.worksheets[0]
        
    def save(self, path):
        pass
        
    def close(self):
        pass

# Register mocked openpyxl module in sys.modules
mock_openpyxl = MagicMock()
mock_openpyxl.Workbook = lambda: MockWorkbook()
mock_openpyxl.load_workbook = lambda path, data_only=False: MockWorkbook()
sys.modules['openpyxl'] = mock_openpyxl

# Safely import components
from src.analyzers.xlsx_analyzer import XlsxAnalyzer
from src.writers.xlsx_writer import XlsxWriter
from src.fields.models import FieldType

def test_xlsx_detection_and_filling():
    doc_path = "tests/fixtures/forms/sample_form.xlsx"
    output_path = "tests/fixtures/forms/sample_form_filled.xlsx"
    
    analyzer = XlsxAnalyzer()
    writer = XlsxWriter()
    
    # 1. Analyze layout (uses mocked openpyxl under the hood)
    fields = analyzer.analyze(doc_path)
    assert len(fields) == 2
    
    # Verify labels
    labels = [f.label for f in fields]
    assert "Nama Lengkap" in labels
    assert "Alamat" in labels
    
    # Verify coordinate names and layout mapping
    c2_field = [f for f in fields if f.metadata["cell_coordinate"] == "C2"][0]
    assert c2_field.row == 2
    assert c2_field.column == 3
    assert c2_field.field_type == FieldType.TEXT
    
    b5_field = [f for f in fields if f.metadata["cell_coordinate"] == "B5"][0]
    assert b5_field.row == 5
    assert b5_field.column == 2
    assert b5_field.field_type == FieldType.TEXT
    
    # Provide answers
    c2_field.answer = "Vhalentino Gamgenora"
    b5_field.answer = "Jakarta, Indonesia"
    
    # 2. Fill cell values (uses mocked openpyxl under the hood)
    writer.fill(doc_path, fields, output_path)
