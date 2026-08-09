import os
import re
import json
from typing import Optional

# Pre-defined mapping of common form labels to canonical profile JSON keys
CANONICAL_MAP = {
    "nama": "full_name",
    "nama lengkap": "full_name",
    "name": "full_name",
    "full name": "full_name",
    "nama lengkap full name": "full_name",
    "nik": "nik",
    "no ktp": "nik",
    "nomor ktp": "nik",
    "identity number": "nik",
    "alamat": "address",
    "alamat sekarang": "address",
    "current address": "address",
    "alamat sekarang current address": "address",
    "alamat original address": "address",
    "email": "email",
    "email address": "email",
    "hp": "phone",
    "no hp": "phone",
    "telepon": "phone",
    "phone": "phone",
    "mobile": "phone",
    "kota": "city",
    "city": "city",
    "kota city": "city",
    "kode pos": "zip_code",
    "zip code": "zip_code",
    "kode pos zip code": "zip_code",
    "pekerjaan": "occupation",
    "occupation": "occupation",
    "pekerjaan occupation": "occupation",
    "agama": "religion",
    "religion": "religion",
    "agama religion": "religion",
    "kewarganegaraan": "nationality",
    "nationality": "nationality",
    "kewarganegaraan nationality": "nationality",
    "status": "marital_status",
    "status pernikahan": "marital_status",
    "marital status": "marital_status",
    "status pernikahan marital status": "marital_status",
    "status perkawinan": "marital_status",
    "gpa": "gpa",
    "ipk": "gpa",
    "education": "education",
    "pendidikan": "education",
    "pendidikan terakhir": "education",
}

# Persistent semantic mapping cache file path
_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "knowledge")
_CACHE_PATH = os.path.join(_CACHE_DIR, "semantic_cache.json")

# Self-learning memory cache for semantic mapping results (A9.2)
_semantic_mapping_cache = {}

def _load_persistent_cache() -> dict:
    """Load the semantic mapping cache from disk."""
    if os.path.exists(_CACHE_PATH):
        try:
            with open(_CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_persistent_cache():
    """Flush the current in-memory cache to disk."""
    try:
        os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)
        with open(_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(_semantic_mapping_cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# Load any previously persisted cache entries on module import
_semantic_mapping_cache.update(_load_persistent_cache())

def get_canonical_map_cache():
    return _semantic_mapping_cache

def add_to_cache(clean_label: str, canonical_key: str):
    """Add a mapping to the in-memory cache and persist to disk."""
    _semantic_mapping_cache[clean_label] = canonical_key
    _save_persistent_cache()

def clean_mapping_label(label: str) -> str:
    # Lowercase, replace newlines/tabs with space, remove symbols
    lbl = label.lower().replace("\n", " ").replace("\r", " ").strip()
    lbl = re.sub(r'[:：_．\.\-\(\)\s]+$', '', lbl)
    return lbl.strip()

def resolve_canonical_key(label: str, threshold: float = 90.0) -> Optional[str]:
    """
    Resolves a raw field label to a canonical key in profile.json.
    1. Exact match against semantic cache (persisted across restarts).
    2. Exact match against static CANONICAL_MAP.
    3. Token-aware fuzzy matching (rapidfuzz token_sort_ratio) with threshold >= 90%.
    No unsafe substring/startswith matching is performed.
    """
    clean_lbl = clean_mapping_label(label)
    if not clean_lbl:
        return None

    # 1. Check exact match in persistent cache first
    if clean_lbl in _semantic_mapping_cache:
        return _semantic_mapping_cache[clean_lbl]

    # 2. Check exact match in static map
    if clean_lbl in CANONICAL_MAP:
        return CANONICAL_MAP[clean_lbl]

    # 3. Token-aware fuzzy matching (no startswith — review fix #4)
    try:
        from rapidfuzz import process, fuzz
        res = process.extractOne(clean_lbl, CANONICAL_MAP.keys(), scorer=fuzz.token_sort_ratio)
        if res and res[1] >= threshold:
            return CANONICAL_MAP[res[0]]
    except ImportError:
        import difflib
        best_match = None
        best_ratio = 0.0
        for key in CANONICAL_MAP.keys():
            ratio = difflib.SequenceMatcher(None, clean_lbl, key).ratio() * 100
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = key
        if best_match and best_ratio >= threshold:
            return CANONICAL_MAP[best_match]

    return None
