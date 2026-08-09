import os
import json
from typing import Dict, Any, List
from src import db

# Paths
KNOWLEDGE_DIR = os.path.dirname(os.path.abspath(__file__))
STRUCTURED_PROFILE_PATH = os.path.join(KNOWLEDGE_DIR, "structured", "profile.json")

def load_profile() -> Dict[str, Any]:
    """
    Loads the structured canonical profile data from profile.json.
    """
    if not os.path.exists(STRUCTURED_PROFILE_PATH):
        # Return empty dictionary if profile.json does not exist
        return {}
    try:
        with open(STRUCTURED_PROFILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading profile.json: {e}")
        return {}

def load_raw_texts() -> List[Dict[str, Any]]:
    """
    Retrieves all raw text documents and their metadata from the database index.
    """
    records = db.list_records()
    results = []
    for meta in records:
        rec_id = meta.get("id")
        rec = db.get_record(rec_id)
        if rec:
            results.append(rec)
    return results
