
import os
import sys

HF_REPO = "gokulalgates/nrtoxpred-models"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def download_models_from_hf(progress_cb=None, svm_only=False):
    if not HF_REPO:
        raise ValueError("HF_REPO is not set")
    try:
        from huggingface_hub import snapshot_download, list_repo_files
    except ImportError:
        raise ImportError("huggingface_hub is not installed")

    print("Connecting to Hugging Face...")
    all_files = [f for f in list_repo_files(HF_REPO, repo_type="model")
                 if not f.startswith(".") and f != "README.md"]

    if svm_only:
        files = [f for f in all_files if "_SL.model" not in f]
        ignore = ["*_SL.model", "README.md", ".gitattributes"]
    else:
        files = all_files
        ignore = ["README.md", ".gitattributes"]

    total = len(files)
    print(f"Downloading {total} files to {SCRIPT_DIR}...")

    snapshot_download(
        repo_id=HF_REPO,
        repo_type="model",
        local_dir=SCRIPT_DIR,
        ignore_patterns=ignore,
    )
    print("Download complete!")

if __name__ == "__main__":
    try:
        download_models_from_hf(svm_only=True)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
