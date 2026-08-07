import pytest
from src import llm

def test_llm_sequential_context_missing_file():
    """Verify that SequentialLLMContext raises FileNotFoundError for missing model weights."""
    context = llm.SequentialLLMContext(model_path="nonexistent_llm_model.gguf")
    with pytest.raises(FileNotFoundError):
        with context as _:
            pass

def test_embeddings_missing_file():
    """Verify that generate_embeddings raises FileNotFoundError when the embedding model is missing."""
    # We patch the global path or temporarily point it to a nonexistent path
    original_path = llm.EMBEDDING_PATH
    llm.EMBEDDING_PATH = "nonexistent_embedding_model.gguf"
    try:
        with pytest.raises(FileNotFoundError):
            llm.generate_embeddings(["test text"])
    finally:
        llm.EMBEDDING_PATH = original_path
