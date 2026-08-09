import os
from typing import Optional, List, Dict, Any
from src import llm, config
from src.fields.models import ResolutionMethod
from src.fields.canonical_map import get_canonical_map_cache, add_to_cache

CANONICAL_KEYS = [
    "full_name", "email", "phone", "website", "address", 
    "city", "zip_code", "nationality", "marital_status", 
    "religion", "occupation", "gpa", "education"
]

def resolve_semantic_mapping(label: str, context_labels: List[str] = None) -> Optional[str]:
    """
    Asks the LLM to semantically map a raw label to one of our canonical keys (A9.2).
    If a match is found, it is saved to the persistent mapping cache for future O(1) matching.
    """
    if not os.path.exists(llm.LLM_PATH):
        return None
        
    context_str = ", ".join(context_labels) if context_labels else "None"
    
    prompt = (
        "You are an expert data mapper. Map the following document field label to one of the canonical profile keys.\n\n"
        f"Field Label: {label}\n"
        f"Context Info: {context_str}\n\n"
        "Available Canonical Keys:\n"
        "- full_name\n"
        "- email\n"
        "- phone\n"
        "- website\n"
        "- address\n"
        "- city\n"
        "- zip_code\n"
        "- nationality\n"
        "- marital_status\n"
        "- religion\n"
        "- occupation\n"
        "- gpa\n"
        "- education\n\n"
        "Rules:\n"
        "- Output ONLY the canonical key name (e.g., full_name) and nothing else.\n"
        "- If no canonical key matches, output only: NONE\n"
        "- Do not use markdown, do not write explanations.\n\n"
        "Canonical Key: "
    )
    
    try:
        output = llm.generate_text(prompt, max_tokens=16, temperature=0.1).strip().lower()
        # Clean any markdown or punctuation
        output = output.replace("`", "").replace("'", "").replace("\"", "").strip()
        
        # Verify the key is valid
        for key in CANONICAL_KEYS:
            if key in output:
                # Cache the result persistently (A9.2)
                clean_lbl = label.lower().strip()
                add_to_cache(clean_lbl, key)
                return key
    except Exception as e:
        print(f"Error in LLM semantic mapping for '{label}': {e}")
        
    return None

def _estimate_token_count(text: str) -> int:
    """Rough token estimate: ~4 chars per token for multilingual text."""
    return len(text) // 4

def resolve_open_ended(label: str, context_documents: List[Dict[str, Any]]) -> Optional[str]:
    """
    Queries the local LLM to extract open-ended field answers from the raw document context (A9.3).
    Truncates context to fit within the model's context window.
    """
    if not os.path.exists(llm.LLM_PATH):
        return None
        
    # Build context string
    context_parts = []
    for doc in context_documents:
        cat = doc.get("category", "")
        filename = doc.get("original_filename", "")
        raw = doc.get("raw_text", "")
        header = f"[{cat}] " if cat else ""
        context_parts.append(f"{header}Source: {filename}\n{raw}")
    context_str = "\n\n".join(context_parts)
    
    if not context_str.strip():
        return None
    
    # Guard: truncate context to fit within n_ctx budget
    # Budget = n_ctx - max_tokens - prompt_instructions_overhead (~300 tokens)
    max_context_tokens = config.LLM_N_CTX - config.LLM_MAX_TOKENS - 300
    if max_context_tokens < 100:
        max_context_tokens = 100
    estimated_tokens = _estimate_token_count(context_str)
    if estimated_tokens > max_context_tokens:
        # Truncate to roughly max_context_tokens * 4 characters
        max_chars = max_context_tokens * 4
        context_str = context_str[:max_chars] + "\n... [truncated due to context limit]"
        
    prompt = (
        "You are an AI assistant helping to auto-fill form fields.\n"
        f"Based ONLY on the context documents below, retrieve the value for the form field: '{label}'.\n\n"
        "Rules:\n"
        "- Extract the exact value verbatim. Do not summarize, do not guess, do not add filler words.\n"
        "- If the value is not explicitly present in the context, output only: EMPTY\n"
        "- Do not output any explanation, markdown, or intros.\n\n"
        f"Context Documents:\n---\n{context_str}\n---\n\n"
        f"Value for '{label}': "
    )
    
    # Retry loop (max 2 times) to ensure reliable output
    for attempt in range(2):
        try:
            output = llm.generate_text(prompt, max_tokens=128, temperature=0.1).strip()
            # Clean output
            clean = output.strip()
            if clean.upper() == "EMPTY" or "empty" in clean.lower():
                return None
            return clean
        except Exception as e:
            print(f"LLM extraction attempt {attempt+1} failed for field '{label}': {e}")
            
    return None
