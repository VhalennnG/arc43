import os
import urllib.request
from huggingface_hub import HfApi, hf_hub_download

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "models")
STATIC_JS_DIR = os.path.join(BASE_DIR, "static", "js")

# Repositories
LLM_REPO = "aisingapore/Apertus-SEA-LION-v4-8B-IT-GGUF"
EMBEDDING_REPO = "gpustack/bge-m3-GGUF"

def setup_directories():
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(STATIC_JS_DIR, exist_ok=True)
    print(f"Directories verified: {MODELS_DIR}, {STATIC_JS_DIR}")

def download_htmx():
    htmx_url = "https://unpkg.com/htmx.org@2.0.1/dist/htmx.min.js"
    target_path = os.path.join(STATIC_JS_DIR, "htmx.min.js")
    
    if os.path.exists(target_path):
        print("htmx.min.js already exists. Skipping download.")
        return

    print(f"Downloading HTMX from {htmx_url}...")
    try:
        urllib.request.urlretrieve(htmx_url, target_path)
        print(f"HTMX downloaded successfully to {target_path}")
    except Exception as e:
        print(f"Failed to download HTMX: {e}")

def find_and_download_gguf(repo_id, pattern, target_filename=None):
    api = HfApi()
    print(f"\nScanning repository: {repo_id} for pattern: '{pattern}'...")
    try:
        files = api.list_repo_files(repo_id=repo_id)
    except Exception as e:
        print(f"Failed to list files in repository {repo_id}: {e}")
        return None

    matching_files = [f for f in files if pattern.lower() in f.lower() and f.endswith(".gguf")]
    
    if not matching_files:
        print(f"No files matching '{pattern}' found in {repo_id}. Available files: {files}")
        return None
    
    # Select the first matching file
    selected_file = matching_files[0]
    print(f"Found matching file: {selected_file}")
    
    dest_filename = target_filename if target_filename else os.path.basename(selected_file)
    dest_path = os.path.join(MODELS_DIR, dest_filename)
    
    if os.path.exists(dest_path):
        print(f"{dest_filename} already exists at {dest_path}. Skipping download.")
        return dest_path

    print(f"Downloading {selected_file} from {repo_id} to {dest_path}...")
    try:
        downloaded_path = hf_hub_download(
            repo_id=repo_id,
            filename=selected_file,
            local_dir=MODELS_DIR,
            local_dir_use_symlinks=False
        )
        # Rename if a specific target name was requested
        if target_filename and os.path.basename(downloaded_path) != target_filename:
            actual_dest = os.path.join(MODELS_DIR, target_filename)
            os.rename(downloaded_path, actual_dest)
            print(f"Renamed {downloaded_path} to {actual_dest}")
            return actual_dest
        print(f"Downloaded successfully to {downloaded_path}")
        return downloaded_path
    except Exception as e:
        print(f"Failed to download {selected_file}: {e}")
        return None

def main():
    setup_directories()
    download_htmx()
    
    # 1. Download LLM model (Q4_K_M quant)
    find_and_download_gguf(
        repo_id=LLM_REPO,
        pattern="q4_k_m",
        target_filename="apertus-sea-lion-v4-8b-it-q4_k_m.gguf"
    )
    
    # 2. Download Embedding model (f16 quant)
    find_and_download_gguf(
        repo_id=EMBEDDING_REPO,
        pattern="f16",
        target_filename="bge-m3-f16.gguf"
    )
    
    print("\nSetup complete.")

if __name__ == "__main__":
    main()
