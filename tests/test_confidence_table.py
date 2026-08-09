import pytest
from src.fields.models import ResolutionMethod, CONFIDENCE_TABLE
from src.resolvers.confidence import get_confidence

def test_confidence_table_mappings():
    # Verify exact mappings from blueprint section A10
    assert get_confidence(ResolutionMethod.EXACT_MATCH) == 0.98
    assert get_confidence(ResolutionMethod.FUZZY_MATCH) == 0.85
    assert get_confidence(ResolutionMethod.LLM_SEMANTIC_MAPPING) == 0.75
    assert get_confidence(ResolutionMethod.LLM_GENERATED) == 0.60
    assert get_confidence(ResolutionMethod.HUMAN_OVERRIDE) == 1.00
    assert get_confidence(ResolutionMethod.LLM_FAILED) == 0.00
    
    # Verify fallback for unknown method
    assert get_confidence("unknown_method") == 0.0
