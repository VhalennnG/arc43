from typing import List, Dict, Any, Optional
from src.fields.models import FormField, ResolutionMethod, CONFIDENCE_TABLE
from src.fields.canonical_map import resolve_canonical_key, clean_mapping_label, CANONICAL_MAP
from src.knowledge.store import load_profile, load_raw_texts
from src.resolvers.llm_resolver import resolve_semantic_mapping, resolve_open_ended

def resolve_field(field: FormField, profile: Dict[str, Any] = None, raw_docs: List[Dict[str, Any]] = None) -> None:
    """
    Resolves the value of a FormField based on structured profile information
    and unstructured context documents. Mutates the field in-place (A9/A10).
    """
    if profile is None:
        profile = load_profile()
    if raw_docs is None:
        raw_docs = load_raw_texts()
        
    cleaned_label = clean_mapping_label(field.label)
    
    # 1. Exact or Fuzzy Label lookup directly in canonical structured profile (A9.1)
    canonical_key = resolve_canonical_key(field.label, threshold=90.0)
    if canonical_key and canonical_key in profile:
        field.answer = profile[canonical_key]
        field.source = f"profile.{canonical_key}"
        
        # Exact match check
        from src.fields.canonical_map import get_canonical_map_cache
        if cleaned_label in CANONICAL_MAP or cleaned_label in get_canonical_map_cache():
            field.method = ResolutionMethod.EXACT_MATCH
        else:
            field.method = ResolutionMethod.FUZZY_MATCH
            
        field.confidence = CONFIDENCE_TABLE[field.method]
        return

    # 2. Semantic mapping via local LLM lookup (A9.2)
    semantic_key = resolve_semantic_mapping(field.label, field.context_labels)
    if semantic_key and semantic_key in profile:
        field.answer = profile[semantic_key]
        field.source = f"profile.{semantic_key}"
        field.method = ResolutionMethod.LLM_SEMANTIC_MAPPING
        field.confidence = CONFIDENCE_TABLE[field.method]
        return

    # 3. Open-ended generative LLM search over raw documents context (A9.3)
    llm_answer = resolve_open_ended(field.label, raw_docs)
    if llm_answer:
        field.answer = llm_answer
        field.source = "llm_generated"
        field.method = ResolutionMethod.LLM_GENERATED
        field.confidence = CONFIDENCE_TABLE[field.method]
    else:
        field.answer = None
        field.source = None
        field.method = ResolutionMethod.LLM_FAILED
        field.confidence = CONFIDENCE_TABLE[field.method]

def resolve_all_fields(fields: List[FormField], profile: Dict[str, Any] = None, raw_docs: List[Dict[str, Any]] = None) -> None:
    """
    Orchestrates the resolution of a list of FormFields.
    Preloads the LLM once for batch operations to prevent load/unload loops.
    """
    if profile is None:
        profile = load_profile()
    if raw_docs is None:
        raw_docs = load_raw_texts()
        
    from src import llm
    import os
    
    # Preload the LLM once if the model path exists
    llm_exists = os.path.exists(llm.LLM_PATH)
    if llm_exists:
        try:
            llm.preload_llm()
        except Exception as e:
            print(f"Failed to preload LLM: {e}")
            
    try:
        for field in fields:
            resolve_field(field, profile, raw_docs)
    finally:
        if llm_exists:
            llm.unload_llm()
