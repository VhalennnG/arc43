import pytest
from unittest.mock import patch
from src.fields.models import FormField, FieldType, ResolutionMethod
from src.resolvers.router import resolve_field
from src.fields.canonical_map import get_canonical_map_cache

def test_known_label_never_calls_llm():
    # "Nama Lengkap" exists in the pre-defined CANONICAL_MAP
    field = FormField(id="f1", label="Nama Lengkap", field_type=FieldType.TEXT)
    sample_profile = {"full_name": "Vhalentino Gamgenora"}
    
    with patch("src.resolvers.router.resolve_semantic_mapping") as mock_semantic:
        with patch("src.resolvers.router.resolve_open_ended") as mock_open:
            resolve_field(field, profile=sample_profile, raw_docs=[])
            
            mock_semantic.assert_not_called()
            mock_open.assert_not_called()
            
    assert field.answer == "Vhalentino Gamgenora"
    assert field.method == ResolutionMethod.EXACT_MATCH

def test_unknown_label_uses_llm_then_caches():
    # "Hobi dan Kegemaran" is not in the static map or prefix matches
    field1 = FormField(id="f2", label="Hobi dan Kegemaran", field_type=FieldType.TEXT)
    field2 = FormField(id="f3", label="Hobi dan Kegemaran", field_type=FieldType.TEXT)
    
    sample_profile = {"full_name": "Vhalentino Gamgenora"}
    cache = get_canonical_map_cache()
    # Clear cache entry to ensure clean test
    cache.pop("hobi dan kegemaran", None)
    
    with patch("src.resolvers.router.resolve_semantic_mapping", return_value="full_name") as mock_semantic:
        resolve_field(field1, profile=sample_profile, raw_docs=[])
        assert mock_semantic.call_count == 1
        assert field1.answer == "Vhalentino Gamgenora"
        assert field1.method == ResolutionMethod.LLM_SEMANTIC_MAPPING
        
        # Simulate LLM resolver side-effect of saving mapping to cache
        cache["hobi dan kegemaran"] = "full_name"
        
        # Second resolution of the same label should hit the cache, avoiding LLM calls
        resolve_field(field2, profile=sample_profile, raw_docs=[])
        assert mock_semantic.call_count == 1  # Call count remains 1
        
    assert field2.answer == "Vhalentino Gamgenora"
    assert field2.method == ResolutionMethod.EXACT_MATCH
