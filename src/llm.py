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

# Global reference to resident LLM model (for batch processing)
_llm_instance: Optional[Llama] = None

def preload_llm(model_path: str = None, n_ctx: int = None) -> Llama:
    """
    Preloads and caches the LLM model globally for batch processing.
    """
    global _llm_instance
    if _llm_instance is None:
        path = model_path or config.LLM_PATH
        ctx = n_ctx or config.LLM_N_CTX
        if not os.path.exists(path):
            raise FileNotFoundError(f"LLM model GGUF not found at: {path}")
        print(f"Preloading LLM model for batch processing: {path}...")
        _llm_instance = Llama(
            model_path=path,
            n_ctx=ctx,
            n_gpu_layers=-1,  # Use Metal acceleration on Apple Silicon macOS
            verbose=False
        )
    return _llm_instance

def unload_llm():
    """
    Unloads the globally cached LLM model to release memory.
    """
    global _llm_instance
    if _llm_instance is not None:
        print("Unloading globally cached LLM model...")
        del _llm_instance
        _llm_instance = None
        gc.collect()

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
    Generates text using the cached LLM model if preloaded,
    otherwise loads and unloads the model on-demand.
    """
    global _llm_instance
    if max_tokens is None:
        max_tokens = config.LLM_MAX_TOKENS
    if temperature is None:
        temperature = config.LLM_TEMPERATURE
        
    if _llm_instance is not None:
        res = _llm_instance.create_completion(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop
        )
        return res["choices"][0]["text"]
        
    with SequentialLLMContext() as model:
        res = model.create_completion(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop
        )
        return res["choices"][0]["text"]

