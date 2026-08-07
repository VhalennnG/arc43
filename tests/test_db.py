import os
import shutil
import pytest
from src import db

@pytest.fixture(autouse=True)
def setup_temp_db(monkeypatch):
    # Set a temporary knowledge directory for tests
    temp_dir = os.path.join(db.DATA_DIR, "temp_test_knowledge")
    monkeypatch.setattr(db, "KNOWLEDGE_DIR", temp_dir)
    monkeypatch.setattr(db, "INDEX_PATH", os.path.join(temp_dir, "index.json"))
    os.makedirs(temp_dir, exist_ok=True)
    db.init_db()
    
    yield
    
    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

def test_save_and_get_record():
    filename = "test_document.pdf"
    raw_text = "This is some raw extracted document text."
    category = "Data pribadi berupa KTP (Kartu Tanda Penduduk)"
    
    # Save record
    saved = db.save_record(
        filename=filename,
        source_type="pdf",
        extraction_method="parser",
        raw_text=raw_text,
        category=category
    )
    
    assert saved["original_filename"] == filename
    assert saved["category"] == category
    
    # Retrieve record
    retrieved = db.get_record(saved["id"])
    assert retrieved is not None
    assert retrieved["category"] == category
    assert retrieved["raw_text"] == raw_text
    
    # List records
    records = db.list_records()
    assert len(records) == 1
    assert records[0]["id"] == saved["id"]
    
    # Delete record
    deleted = db.delete_record(saved["id"])
    assert deleted is True
    assert db.get_record(saved["id"]) is None
    assert len(db.list_records()) == 0
