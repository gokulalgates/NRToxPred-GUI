
import os
import sys
import platform

HF_REPO = "gokulalgates/nrtoxpred-models"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# On Windows, download to AppData\Local\NRToxPred to avoid OneDrive sync issues
if platform.system() == "Windows":
    _appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    DEST_DIR = os.path.join(_appdata, "NRToxPred")
else:
    DEST_DIR = SCRIPT_DIR

def download_models_from_hf(svm_only=False):
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

    os.makedirs(DEST_DIR, exist_ok=True)
    print(f"Downloading {len(files)} files to: {DEST_DIR}")

    snapshot_download(
        repo_id=HF_REPO,
        repo_type="model",
        local_dir=DEST_DIR,
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
