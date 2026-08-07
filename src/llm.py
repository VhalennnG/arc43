import os
import gc
from typing import List, Optional
from llama_cpp import Llama

from src import config

# Re-export paths for external consumers (e.g. app.py checks os.path.exists(llm.LLM_PATH))
LLM_PATH = config.LLM_PATH
EMBEDDING_PATH = config.EMBEDDING_PATH

# Global reference to resident embedding model
_embedding_model: Optional[Llama] = None

def get_embedding_model() -> Llama:
    """
    Returns the resident embedding model. Loads it if not already resident.
    """
    global _embedding_model
    if _embedding_model is None:
        if not os.path.exists(EMBEDDING_PATH):
            raise FileNotFoundError(
                f"Embedding model GGUF not found at: {EMBEDDING_PATH}. Please run scripts/download_models.py first."
            )
        print(f"Loading resident embedding model: {EMBEDDING_PATH}...")
        _embedding_model = Llama(
            model_path=EMBEDDING_PATH,
            embedding=True,
            n_ctx=config.EMBEDDING_N_CTX,
            verbose=False,
            n_gpu_layers=-1  # Use Metal acceleration on Apple Silicon macOS
        )
    return _embedding_model

class SequentialLLMContext:
    """
    A context manager to load the LLM model sequentially and unload it upon exit.
    This helps keep memory usage within limits on 8GB RAM devices.
    """
    def __init__(self, model_path: str = None, n_ctx: int = None):
        self.model_path = model_path or config.LLM_PATH
        self.n_ctx = n_ctx or config.LLM_N_CTX
        self.llm: Optional[Llama] = None

    def __enter__(self) -> Llama:
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"LLM model GGUF not found at: {self.model_path}. Please run scripts/download_models.py first."
            )
        print(f"Loading LLM model: {self.model_path}...")
        self.llm = Llama(
            model_path=self.model_path,
            n_ctx=self.n_ctx,
            n_gpu_layers=-1,  # Use Metal acceleration on Apple Silicon macOS
            verbose=False
        )
        return self.llm

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.llm:
            print("Unloading LLM model to free memory...")
            del self.llm
            self.llm = None
            gc.collect()

def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generates text embeddings for a list of strings using the resident embedding model.
    """
    model = get_embedding_model()
    res = model.create_embedding(texts)
    return [item["embedding"] for item in res["data"]]

def generate_text(
    prompt: str,
    max_tokens: int = None,
    temperature: float = None,
    stop: Optional[List[str]] = None
) -> str:
    """
    Loads the LLM model, performs text completion, and unloads it to release resources.
    """
    if max_tokens is None:
        max_tokens = config.LLM_MAX_TOKENS
    if temperature is None:
        temperature = config.LLM_TEMPERATURE
        
    with SequentialLLMContext() as llm:
        res = llm.create_completion(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop
        )
        return res["choices"][0]["text"]

