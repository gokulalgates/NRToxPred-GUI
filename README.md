# NR-ToxPred GUI

A standalone desktop application for predicting the toxicity of chemical compounds against nine nuclear receptors (NRs) using pre-trained machine learning models.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue) ![License](https://img.shields.io/badge/License-MIT-green) ![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey)

---

## Quick Start (No Python experience needed)

**Step 1 — Download this repository**
Click the green **Code** button above → **Download ZIP** → Extract the ZIP folder anywhere on your computer

**Step 2 — Install** (one-time, ~10–20 minutes)
- **Windows:** Double-click `install.bat`
- **Mac / Linux:** Open a terminal in the folder and run `bash install.sh`

> The installer automatically downloads Python (Miniconda) and all required packages for you. No prior setup needed.

**Step 3 — Run the app**
- **Windows:** Double-click `run.bat`
- **Mac / Linux:** Run `bash run.sh`

On first launch, click **Download** when prompted to fetch the prediction models (~250 MB).

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

- **Single compound prediction** — enter a SMILES string and get instant results
- **Batch prediction** — upload a CSV/Excel file with a column of SMILES strings
- **Two fingerprint types** — Morgan (ECFP6, 1024 bits) and MACCS Keys (167 bits)
- **Two algorithms** — SVM (fast) and SuperLearner (ensemble, requires large model files)
- **Applicability Domain** — Tanimoto-based AD with adjustable similarity cutoff and neighbor count
- **2D structure viewer** — renders the molecule structure in the single prediction tab
- **Molecular descriptors** — MW, LogP, HBD, HBA, TPSA, RotBonds displayed per compound
- **Export results** — save batch predictions to Excel
- **Auto-download** — fetches models from Hugging Face Hub on first run (when configured)
- **Pre-warming** — loads all models into memory at startup for instant subsequent predictions

---

## Requirements

### System dependencies (install via conda)
```bash
conda install -c conda-forge rdkit openbabel
```

### Python packages
```bash
pip install -r requirements.txt
```

`requirements.txt` includes: `rdkit-pypi`, `molvs`, `scikit-learn==0.23.2`, `pandas`, `numpy`, `scipy`, `openpyxl`, `Pillow`, `huggingface_hub`

---

## Model Files

The pre-trained models are **not** included in this repository due to their size. They must be placed in the following directories relative to `pytox_gui.py`:

```
NRToxPred-GUI/
├── MODELS/
│   ├── morgan/
│   │   ├── ARsvm_best.model
│   │   ├── ERAsvm_best.model
│   │   └── ... (one per receptor)
│   ├── MACCS/
│   │   └── ... (one per receptor)
│   └── ARclasses.npy
└── X_train/
    ├── AR.xlsx
    ├── ERA.xlsx
    └── ... (one per receptor)
```

### Option A — Download from Hugging Face (recommended)

If the model repository has been configured, the app will offer to auto-download on first launch. See [TUTORIAL.md](TUTORIAL.md) for instructions on setting up the Hugging Face repository.

### Option B — Manual placement

Copy your `MODELS/` and `X_train/` directories into the same folder as `pytox_gui.py`.

---

## Installation & Running

```bash
# 1. Clone the repository
git clone https://github.com/gokulalgates/NRToxPred-GUI.git
cd NRToxPred-GUI

# 2. Create and activate a conda environment
conda create -n nrtoxpred python=3.9
conda activate nrtoxpred

# 3. Install RDKit and OpenBabel via conda
conda install -c conda-forge rdkit openbabel

# 4. Install remaining dependencies
pip install -r requirements.txt

# 5. Place model files (see above)

# 6. Launch the application
python pytox_gui.py
```

---

## Quick Start

1. Open the **Single Prediction** tab
2. Paste a SMILES string (e.g., `CC(=O)Oc1ccccc1C(=O)O` for aspirin)
3. Select **Fingerprint** type and **Algorithm**
4. Click **Predict**
5. View results in the table and the 2D structure panel

For batch predictions, switch to the **Batch Prediction** tab and load a CSV or Excel file.

---

## Applicability Domain

Each prediction is tagged as:

- **Reliable** — the compound is similar to at least *N* training set compounds at a Tanimoto similarity ≥ *S*
- **Unreliable** — the compound falls outside the training set chemical space; predictions should be interpreted with caution

The **Scutoff** (similarity threshold) and **Nsimilar** (minimum neighbor count) parameters can be adjusted in the AD Parameters panel.

---

## Citation

If you use NR-ToxPred in your research, please cite:

> Predicting the binding of small molecules to nuclear receptors using machine learning.
> *Brief Bioinform.* 2022 May 13;23(3):bbac114.
> doi: [10.1093/bib/bbac114](https://doi.org/10.1093/bib/bbac114)

---

## License

MIT License. See [LICENSE](LICENSE) for details.
