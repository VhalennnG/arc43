import os
import re
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

_VALID_RECORD_ID = re.compile(r'^[a-zA-Z0-9_\-]+$')

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
KNOWLEDGE_DIR = os.path.join(DATA_DIR, "knowledge")
INDEX_PATH = os.path.join(KNOWLEDGE_DIR, "index.json")

def init_db():
    """
    Initializes storage directories and index file.
    """
    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
    if not os.path.exists(INDEX_PATH):
        with open(INDEX_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)

def load_index() -> List[Dict[str, Any]]:
    """
    Loads the database index metadata.
    """
    init_db()
    try:
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading index: {e}")
        return []

def save_index(index_data: List[Dict[str, Any]]):
    """
    Saves the database index metadata.
    """
    init_db()
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)

def generate_record_id(filename: str) -> str:
    """
    Generates a unique ID for a record.
    Replaces spaces/special chars and appends the current date/time.
    """
    base = os.path.splitext(filename)[0]
    # Clean up name: keep alphanumeric and underscores
    clean_base = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in base)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"{clean_base}_{timestamp}"

def save_record(
    filename: str,
    source_type: str,
    extraction_method: str,
    raw_text: str,
    category: str = ""
) -> Dict[str, Any]:
    """
    Creates and saves a new document record as a .txt file.
    Line 1: category, Line 2: blank, Line 3+: raw_text.
    """
    init_db()
    record_id = generate_record_id(filename)
    uploaded_at = datetime.now().isoformat()
    
    # Save as .txt: category \n\n raw_text
    record_path = os.path.join(KNOWLEDGE_DIR, f"{record_id}.txt")
    with open(record_path, "w", encoding="utf-8") as f:
        f.write(category + "\n\n" + raw_text)
        
    # Update index with lightweight metadata
    index = load_index()
    index_entry = {
        "id": record_id,
        "original_filename": filename,
        "uploaded_at": uploaded_at,
        "source_type": source_type,
        "extraction_method": extraction_method,
        "category": category
    }
    index.append(index_entry)
    save_index(index)
    
    return index_entry

def get_record(record_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a single record by its ID.
    Reads the .txt file and parses line 1 as category, rest as raw_text.
    Also merges metadata from index.json.
    """
    if not _VALID_RECORD_ID.match(record_id):
        return None
    record_path = os.path.join(KNOWLEDGE_DIR, f"{record_id}.txt")
    if not os.path.exists(record_path):
        return None
    try:
        with open(record_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Split: first line = category, rest (after blank line) = raw_text
        parts = content.split("\n\n", 1)
        category = parts[0].strip() if len(parts) > 0 else ""
        raw_text = parts[1] if len(parts) > 1 else ""
        
        # Merge with index metadata
        index = load_index()
        meta = next((e for e in index if e["id"] == record_id), {})
        
        return {
            **meta,
            "id": record_id,
            "category": category,
            "raw_text": raw_text
        }
    except Exception as e:
        print(f"Error loading record {record_id}: {e}")
        return None

def delete_record(record_id: str) -> bool:
    """
    Deletes a record (.txt file) and its index entry.
    """
    if not _VALID_RECORD_ID.match(record_id):
        return False
    # Delete individual record file
    record_path = os.path.join(KNOWLEDGE_DIR, f"{record_id}.txt")
    deleted = False
    if os.path.exists(record_path):
        try:
            os.remove(record_path)
            deleted = True
        except Exception as e:
            print(f"Error deleting file {record_path}: {e}")
            
    # Update index
    index = load_index()
    new_index = [entry for entry in index if entry["id"] != record_id]
    if len(new_index) < len(index):
        save_index(new_index)
        deleted = True
        
    return deleted

def list_records() -> List[Dict[str, Any]]:
    """
    Returns all metadata records from the index.
    """
    return load_index()

def log_process(filename: str, event: str, details: Any):
    """
    Writes detailed processing steps to data/process_audit.log for developer/user evaluation.
    """
    init_db()
    log_path = os.path.join(DATA_DIR, "process_audit.log")
    
    timestamp = datetime.now().isoformat()
    log_entry = {
        "timestamp": timestamp,
        "filename": filename,
        "event": event,
        "details": details
    }
    
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"Failed to write process audit log: {e}")


