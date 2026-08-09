from src.fields.models import ResolutionMethod, CONFIDENCE_TABLE

def get_confidence(method: ResolutionMethod) -> float:
    """
    Returns the deterministic confidence score for a given resolution method.
    Scores are fixed constants based on the method reliability (A10).
    """
    return CONFIDENCE_TABLE.get(method, 0.0)
