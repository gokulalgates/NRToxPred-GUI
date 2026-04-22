# NR-ToxPred

A desktop application and command-line tool for predicting the binding of chemical compounds to nine nuclear receptors (NRs) using pre-trained machine learning models.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue) ![License](https://img.shields.io/badge/License-MIT-green) ![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey)

---

## Quick Start (No Python experience needed)

**Step 1 — Download this repository**
Click the green **Code** button above → **Download ZIP** → Extract the ZIP folder anywhere on your computer

**Step 2 — Install** (one-time, ~10–20 minutes)
- **Windows:** Double-click `install.bat`
- **Mac / Linux:** Open a terminal in the folder and run `bash install.sh`

> The installer automatically downloads Python (Miniconda) and all required packages. No prior setup needed.

**Step 3 — Run the app**
- **Windows:** Double-click `run.bat`
- **Mac / Linux:** Run `bash run.sh`

On first launch, click **Download SVM only** when prompted to fetch the prediction models (~250 MB).

> Steps 1–2 are one-time only. After that, just use Step 3 every time.

---

## Overview

NR-ToxPred predicts whether a compound is **Active** or **Inactive** against the following nuclear receptors:

| Receptor | Full Name |
|----------|-----------|
| RXR | Retinoid X Receptor |
| PR | Progesterone Receptor |
| GR | Glucocorticoid Receptor |
| AR | Androgen Receptor |
| ERA | Estrogen Receptor Alpha |
| ERB | Estrogen Receptor Beta |
| FXR | Farnesoid X Receptor |
| PPARD | Peroxisome Proliferator-Activated Receptor Delta |
| PPARG | Peroxisome Proliferator-Activated Receptor Gamma |

Each prediction includes an **Applicability Domain (AD)** assessment — **Reliable** or **Unreliable** — based on Tanimoto fingerprint similarity to the training set.

---

## Features

- **GUI and CLI** — interactive desktop app or scriptable command-line interface
- **Single compound prediction** — enter a SMILES string and get instant results
- **Batch prediction** — upload a CSV/Excel file with a column of SMILES strings
- **Two fingerprint types** — Morgan (ECFP6, 1024 bits) and MACCS Keys (167 bits)
- **Two algorithms** — SVM (fast, ~250 MB) and SuperLearner (ensemble, ~12 GB)
- **Applicability Domain** — Tanimoto-based AD with adjustable similarity cutoff and neighbor count
- **2D structure viewer** — renders the molecule structure in the single prediction tab
- **Molecular descriptors** — MW, LogP, HBD, HBA, TPSA, RotBonds displayed per compound
- **Export results** — save batch predictions to Excel or CSV
- **Auto-download** — fetches models from Hugging Face Hub on first run

---

## Command-Line Interface

NR-ToxPred can be used without the GUI, which is useful for scripting and headless servers.

**Single compound:**
```bash
python pytox_gui.py --no-gui --smiles "CC(=O)Oc1ccccc1C(=O)O" --name Aspirin
```

**Batch from CSV:**
```bash
python pytox_gui.py --no-gui --csv compounds.csv --smiles-col SMILES --output results.xlsx
```

**Key options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--smiles SMILES` | — | SMILES string (single compound) |
| `--csv FILE` | — | CSV or Excel file (batch) |
| `--smiles-col COL` | `SMILES` | Column name containing SMILES |
| `--name NAME` | `Compound` | Label for the compound |
| `--fp {morgan,maccs}` | `morgan` | Fingerprint type |
| `--algo {svm,superlearner}` | `svm` | Prediction algorithm |
| `--receptors R [R ...]` | all nine | Subset of receptors to predict |
| `--scutoff FLOAT` | `0.25` | AD Tanimoto similarity cutoff |
| `--nsimilar INT` | `1` | AD minimum similar neighbours |
| `--output FILE` | stdout | Output file (`.csv` or `.xlsx`) |

Run `python pytox_gui.py --help` for the full option list.

---

## Requirements

### System dependencies (install via conda)
```bash
conda install -c conda-forge rdkit
```

### Python packages
```bash
pip install -r requirements.txt
```

`requirements.txt` includes: `molvs`, `scikit-learn==0.23.2`, `mlens`, `pandas`, `numpy`, `scipy`, `openpyxl`, `Pillow`, `huggingface_hub`

> **Note:** scikit-learn is pinned to 0.23.2 and mlens is required for SuperLearner models. Both are installed automatically by `requirements.txt`.

---

## Model Files

The pre-trained models are **not** included in this repository due to their size. On first launch the app offers to download them automatically from Hugging Face Hub.

| Model set | Size | Recommended for |
|-----------|------|-----------------|
| SVM only | ~250 MB | Most users — fast and accurate |
| SVM + SuperLearner | ~12 GB | Maximum accuracy; large download |

**Download location:**
- **Windows:** `%LOCALAPPDATA%\NRToxPred\` (never synced by OneDrive)
- **Mac / Linux:** same folder as `pytox_gui.py`

### Manual placement

If you prefer to copy model files yourself, place `MODELS/` and `X_train/` next to `pytox_gui.py`:

```
NRToxPred-GUI/
├── MODELS/
│   ├── morgan/
│   │   ├── ARsvm_best.model
│   │   └── ... (one per receptor)
│   ├── MACCS/
│   │   └── ... (one per receptor)
│   └── ARclasses.npy
└── X_train/
    ├── AR.xlsx
    └── ... (one per receptor)
```

---

## Installation & Running (Python users)

```bash
# 1. Clone the repository
git clone https://github.com/gokulalgates/NRToxPred-GUI.git
cd NRToxPred-GUI

# 2. Create and activate a conda environment
conda create -n nrtoxpred python=3.8
conda activate nrtoxpred

# 3. Install RDKit via conda
conda install -c conda-forge rdkit

# 4. Install remaining dependencies
pip install -r requirements.txt

# 5. Launch the application
python pytox_gui.py
```

The app will prompt you to download models on first run.

---

## Applicability Domain

Each prediction is tagged as:

- **Reliable** — the compound is similar to at least *N* training set compounds at a Tanimoto similarity ≥ *S*
- **Unreliable** — the compound falls outside the training set chemical space; predictions should be interpreted with caution

The **Scutoff** (similarity threshold) and **Nsimilar** (minimum neighbour count) parameters can be adjusted in the AD Parameters panel (GUI) or via `--scutoff` / `--nsimilar` (CLI).

---

## Citation

If you use NR-ToxPred in your research, please cite:

> Predicting the binding of small molecules to nuclear receptors using machine learning.
> *Brief Bioinform.* 2022 May 13;23(3):bbac114.
> doi: [10.1093/bib/bbac114](https://doi.org/10.1093/bib/bbac114)

---

## License

MIT License. See [LICENSE](LICENSE) for details.
