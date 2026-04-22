"""
Upload SVM and SuperLearner models to Hugging Face Hub.

Usage:
    pip install huggingface_hub
    huggingface-cli login          # paste your HF write token
    python upload_models_to_hf.py --repo YOUR_HF_USERNAME/nrtoxpred-models

    # SVM only (~250 MB):
    python upload_models_to_hf.py --repo YOUR_HF_USERNAME/nrtoxpred-models --svm-only

Uploads:
  - SVM models:          MODELS/morgan/*svm_best.model, MODELS/MACCS/*svm_best.model  (~250 MB)
  - SuperLearner models: MODELS/morgan/*_SL.model,      MODELS/MACCS/*_SL.model       (~12 GB)
  - Label encoder:       MODELS/ARclasses.npy
  - AD training data:    X_train/*.xlsx

Excluded (not needed by the GUI):
  - Old-naming duplicates (*SL.model without underscore)
  - Distance/fp train matrices (*_train_*.model) — 4.7 GB total
"""

import argparse
import glob
import os
from pathlib import Path
from huggingface_hub import HfApi, create_repo

RECEPTORS = ["RXR", "PR", "GR", "AR", "ERA", "ERB", "FXR", "PPARD", "PPARG"]


def collect_files(base: Path, include_sl: bool = True):
    patterns = [
        # SVM models — morgan and MACCS
        ("MODELS/morgan/*svm_best.model", "MODELS/morgan"),
        ("MODELS/MACCS/*svm_best.model",  "MODELS/MACCS"),
        # Label encoder
        ("MODELS/ARclasses.npy",          "MODELS"),
        # X_train applicability-domain data
        ("X_train/*.xlsx",                "X_train"),
    ]

    if include_sl:
        # Only upload *_SL.model (with underscore) — the ones the GUI uses.
        # Restrict to the 9 known receptors to avoid stale or duplicate files.
        for rec in RECEPTORS:
            patterns.append((f"MODELS/morgan/{rec}_SL.model", "MODELS/morgan"))
            patterns.append((f"MODELS/MACCS/{rec}_SL.model",  "MODELS/MACCS"))

    files = []
    seen = set()
    for pattern, _ in patterns:
        for local in glob.glob(str(base / pattern)):
            rel = os.path.relpath(local, base)
            if rel not in seen and os.path.isfile(local):
                seen.add(rel)
                files.append((local, rel))
    return files


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True,
                        help="HF repo id, e.g. YourName/nrtoxpred-models")
    parser.add_argument("--private", action="store_true",
                        help="Create a private repository")
    parser.add_argument("--svm-only", action="store_true",
                        help="Upload SVM models only (~250 MB), skip SuperLearner")
    args = parser.parse_args()

    base = Path(__file__).parent
    api  = HfApi()

    print(f"Creating / verifying repo: {args.repo}")
    create_repo(args.repo, repo_type="model",
                private=args.private, exist_ok=True)

    include_sl = not args.svm_only
    files = collect_files(base, include_sl=include_sl)

    total_mb = sum(os.path.getsize(f) for f, _ in files) / 1e6
    print(f"\nFiles to upload: {len(files)}  ({total_mb/1024:.1f} GB)" if total_mb > 1000
          else f"\nFiles to upload: {len(files)}  ({total_mb:.0f} MB)")
    for _, rel in files:
        size_mb = os.path.getsize(base / rel) / 1e6
        print(f"  {rel:55s} {size_mb:7.0f} MB")

    print("\nStarting upload…")
    for i, (local, path_in_repo) in enumerate(files, 1):
        size_mb = os.path.getsize(local) / 1e6
        print(f"[{i}/{len(files)}]  {path_in_repo}  ({size_mb:.0f} MB)")
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
