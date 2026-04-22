"""
Upload SVM models and X_train data to Hugging Face Hub.

Usage:
    pip install huggingface_hub
    huggingface-cli login          # paste your HF write token
    python upload_models_to_hf.py --repo YOUR_HF_USERNAME/nrtoxpred-models

Uploads (~250 MB total):
  - SVM models: MODELS/morgan/*svm_best.model, MODELS/MACCS/*svm_best.model
  - Label encoder: MODELS/ARclasses.npy
  - AD training data: X_train/*.xlsx

Excluded (not needed by the GUI):
  - SuperLearner models (*_SL.model, *SL.model)  — 1-1.5 GB each
  - Distance/fp train matrices (*_train_*.model)  — 4.7 GB total
"""

import argparse
import os
from pathlib import Path
from huggingface_hub import HfApi, create_repo

# Files to upload: (local_path, path_in_repo)
def collect_files(base: Path):
    patterns = [
        # SVM models — morgan
        ("MODELS/morgan/*svm_best.model",   "MODELS/morgan"),
        # SVM models — MACCS
        ("MODELS/MACCS/*svm_best.model",    "MODELS/MACCS"),
        # Label encoder
        ("MODELS/ARclasses.npy",            "MODELS"),
        # X_train applicability-domain data
        ("X_train/*.xlsx",                  "X_train"),
    ]
    import glob
    files = []
    for pattern, repo_dir in patterns:
        for local in glob.glob(str(base / pattern)):
            rel = os.path.relpath(local, base)
            files.append((local, rel))
    return files


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True,
                        help="HF repo id, e.g. YourName/nrtoxpred-models")
    parser.add_argument("--private", action="store_true",
                        help="Create a private repository")
    args = parser.parse_args()

    base = Path(__file__).parent
    api  = HfApi()

    # Create repo if it doesn't exist
    print(f"Creating / verifying repo: {args.repo}")
    create_repo(args.repo, repo_type="model",
                private=args.private, exist_ok=True)

    files = collect_files(base)
    print(f"\nFiles to upload: {len(files)}")
    for _, rel in files:
        print(f"  {rel}")

    print("\nStarting upload…")
    for i, (local, path_in_repo) in enumerate(files, 1):
        size_mb = os.path.getsize(local) / 1e6
        print(f"[{i}/{len(files)}]  {path_in_repo}  ({size_mb:.1f} MB)")
        api.upload_file(
            path_or_fileobj=local,
            path_in_repo=path_in_repo,
            repo_id=args.repo,
            repo_type="model",
        )

    print(f"\nDone! Models available at:")
    print(f"  https://huggingface.co/{args.repo}")


if __name__ == "__main__":
    main()
