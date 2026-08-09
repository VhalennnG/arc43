import os
from docx import Document
from src.analyzers.docx_analyzer import DocxAnalyzer
from src.writers.docx_writer import DocxWriter

def test_docx_checkbox_cell_and_text_filling():
    doc_path = "tests/fixtures/forms/peepl_biodata.docx"
    output_path = "tests/fixtures/forms/peepl_biodata_filled_test.docx"
    
    analyzer = DocxAnalyzer()
    writer = DocxWriter()
    
    fields = analyzer.analyze(doc_path)
    
    # Provide answers to select fields based on actual detected labels
    for f in fields:
        if "Laki-laki" in f.label:
            f.answer = "Laki-laki"  # Set to option label -> checks it
        elif "WNI" in f.label:
            f.answer = "yes"        # Set to truthy string -> checks it
        elif "Nama Lengkap" in f.label:
            f.answer = "Vhalentino Gamgenora"
            
    # Mutate template and save output
    writer.fill(doc_path, fields, output_path)
    
    # Read back and verify mutation
    filled_doc = Document(output_path)
    
    # Verify text field in Table 1 Row 1 Column 2
    # In peepl_biodata.docx, Table 1 has the personal details
    t1 = filled_doc.tables[1]
    name_cell_text = t1.rows[1].cells[2].text.strip()
    assert name_cell_text == "Vhalentino Gamgenora", f"Expected name in Table 1 Row 1 Col 2, got: {name_cell_text}"
    
    # Verify cell checkbox is filled with 'X'
    # Gender (Laki-laki) is at Row 15, cell-based checkbox at Column 2
    gender_cell_text = t1.rows[15].cells[2].text.strip()
    assert gender_cell_text == "X", f"Expected checkbox 'X' in Table 1 Row 15 Col 2, got: {gender_cell_text}"
    
    # Verify Nationality (WNI) is checked (Row 17 Column 2)
    nationality_cell_text = t1.rows[17].cells[2].text.strip()
    assert nationality_cell_text == "X", f"Expected checkbox 'X' in Table 1 Row 17 Col 2, got: {nationality_cell_text}"
    
    # Clean up output file
    if os.path.exists(output_path):
        os.remove(output_path)
