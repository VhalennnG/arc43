"""
Centralized configuration for arc43.
Reads from .env file (if present) and falls back to sensible defaults.
"""
import os
from dotenv import load_dotenv

# Load .env from project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# --- LLM Model ---
LLM_N_CTX = int(os.environ.get("LLM_N_CTX", "20480"))
LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "4096"))
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.1"))
LLM_MODEL_FILENAME = os.environ.get("LLM_MODEL_FILENAME", "apertus-sea-lion-v4-8b-it-q4_k_m.gguf")

# --- Embedding Model ---
EMBEDDING_MODEL_FILENAME = os.environ.get("EMBEDDING_MODEL_FILENAME", "bge-m3-f16.gguf")
EMBEDDING_N_CTX = int(os.environ.get("EMBEDDING_N_CTX", "1024"))

# --- OCR ---
OCR_RECOGNITION_LEVEL = int(os.environ.get("OCR_RECOGNITION_LEVEL", "0"))

# --- Derived Paths ---
MODELS_DIR = os.path.join(BASE_DIR, "models")
LLM_PATH = os.path.join(MODELS_DIR, LLM_MODEL_FILENAME)
EMBEDDING_PATH = os.path.join(MODELS_DIR, EMBEDDING_MODEL_FILENAME)
