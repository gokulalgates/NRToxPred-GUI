# NR-ToxPred — Tutorial

This guide walks you through installing, configuring, and using NR-ToxPred in both GUI and command-line modes.

> **Citation:** If you use NR-ToxPred in your research, please cite:
> Predicting the binding of small molecules to nuclear receptors using machine learning.
> *Brief Bioinform.* 2022 May 13;23(3):bbac114. doi: [10.1093/bib/bbac114](https://doi.org/10.1093/bib/bbac114)

---

## Table of Contents

1. [Installation](#1-installation)
2. [Setting Up Model Files](#2-setting-up-model-files)
3. [Single Compound Prediction](#3-single-compound-prediction)
4. [Batch Prediction](#4-batch-prediction)
5. [Command-Line Interface](#5-command-line-interface)
6. [Understanding the Results](#6-understanding-the-results)
7. [Applicability Domain Parameters](#7-applicability-domain-parameters)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Installation

### Option A — One-click install (recommended for non-Python users)

1. Download or clone this repository and extract it anywhere on your computer.
2. Run the installer for your platform:
   - **Windows:** double-click `install.bat`
   - **Mac / Linux:** open a terminal in the folder and run `bash install.sh`

The installer downloads Miniconda (if needed) and creates a self-contained `nrtoxpred` environment with all dependencies. This is a one-time step that takes 10–20 minutes.

To launch the app afterwards:
- **Windows:** double-click `run.bat`
- **Mac / Linux:** `bash run.sh`

### Option B — Manual conda setup

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

# 5. Verify the installation
python -c "from rdkit import Chem; print('OK')"
```

If you see `OK`, the core dependencies are ready.

> **Note:** scikit-learn is pinned to 0.23.2 in `requirements.txt` because the model files were trained with that version. numpy is pinned to 1.23 for compatibility.

---

## 2. Setting Up Model Files

The application needs pre-trained model files to make predictions. These are **not** included in the GitHub repository due to their size.

### Option A — Auto-download from Hugging Face (recommended)

On first launch, the app detects that models are missing and shows a download dialog:

- **Download SVM only (~250 MB)** — fast download, recommended for most users
- **Download All (~12 GB)** — includes SuperLearner models for higher accuracy

Click your preferred option and wait for the download to complete. The app will show a progress indicator.

**Download location:**
- **Windows:** `C:\Users\<you>\AppData\Local\NRToxPred\` (deliberately outside OneDrive to prevent sync interference)
- **Mac / Linux:** same folder as `pytox_gui.py`

You do not need to edit any configuration files — the Hugging Face repository is already configured.

### Option B — Manual placement

Copy the `MODELS/` and `X_train/` directories into the same folder as `pytox_gui.py`:

```
NRToxPred-GUI/
├── pytox_gui.py
├── MODELS/
│   ├── ARclasses.npy
│   ├── morgan/
│   │   ├── ARsvm_best.model
│   │   ├── ERAsvm_best.model
│   │   ├── ERBsvm_best.model
│   │   ├── FXRsvm_best.model
│   │   ├── GRsvm_best.model
│   │   ├── PPARDsvm_best.model
│   │   ├── PPARGsvm_best.model
│   │   ├── PRsvm_best.model
│   │   └── RXRsvm_best.model
│   └── MACCS/
│       └── (same pattern as morgan/)
└── X_train/
    ├── AR.xlsx
    ├── ERA.xlsx
    ├── ERB.xlsx
    ├── FXR.xlsx
    ├── GR.xlsx
    ├── PPARD.xlsx
    ├── PPARG.xlsx
    ├── PR.xlsx
    └── RXR.xlsx
```

---

## 3. Single Compound Prediction

1. **Launch the application**
   ```bash
   python pytox_gui.py
   ```
   The app pre-warms the model cache in the background while you set up your query.

2. **Open the Single Prediction tab** (active by default).

3. **Enter a SMILES string** in the input box.
   - Example (aspirin): `CC(=O)Oc1ccccc1C(=O)O`
   - Example (bisphenol A): `CC(C)(c1ccc(O)cc1)c1ccc(O)cc1`

   You can find SMILES strings from databases such as [PubChem](https://pubchem.ncbi.nlm.nih.gov/) or [ChemSpider](https://www.chemspider.com/).

4. **Enter a compound name** (optional, for labeling results).

5. **Select a Fingerprint type:**
   - **Morgan** — Circular fingerprint (ECFP6, 1024 bits). Generally more informative; default choice.
   - **MACCS** — 167 predefined structural keys. Faster and more interpretable.

6. **Select an Algorithm:**
   - **SVM** — Support Vector Machine. Fast and accurate; recommended for most use cases. Requires SVM models (~250 MB).
   - **SuperLearner** — Ensemble of multiple classifiers. More accurate but requires much larger model files (~12 GB total). Only select this if you downloaded the full model set.

7. **Adjust AD Parameters** if needed (see [Section 7](#7-applicability-domain-parameters)).

8. **Click Predict.**

   Results appear in the table below, and the 2D molecular structure is drawn in the right panel.

---

## 4. Batch Prediction

Use batch mode when you have multiple compounds to screen.

### Prepare your input file

Create a CSV or Excel (.xlsx) file with at least one column containing SMILES strings. Example:

| Name | SMILES |
|------|--------|
| Aspirin | CC(=O)Oc1ccccc1C(=O)O |
| Bisphenol A | CC(C)(c1ccc(O)cc1)c1ccc(O)cc1 |
| Estradiol | OC1CC2CC(O)CCC2(C)C2CCC3=CC(=O)CCC3=C12 |

The column containing SMILES can have any header name — you will select it in the app.

### Running batch prediction

1. Switch to the **Batch Prediction** tab.
2. Click **Load File** and select your CSV or Excel file.
3. Use the **SMILES Column** dropdown to choose the column that contains SMILES strings.
4. Select **Fingerprint** type and **Algorithm**.
5. Adjust **AD Parameters** if needed.
6. Click **Run Batch**.

A progress bar tracks the prediction. When done, results appear in the table.

### Exporting results

Click **Export to Excel** to save the full results table to an `.xlsx` file. The file includes:
- Input SMILES and compound name
- Predicted class (Active/Inactive) for each receptor
- Applicability Domain label (Reliable/Unreliable) for each receptor

---

## 5. Command-Line Interface

NR-ToxPred can run without the GUI using the `--no-gui` flag. This is useful for scripting, pipelines, and headless servers.

### Single compound

```bash
python pytox_gui.py --no-gui --smiles "CC(=O)Oc1ccccc1C(=O)O" --name Aspirin
```

Output (printed to the terminal):
```
Predicting: Aspirin  [morgan / svm]

Compound : Aspirin
SMILES   : CC(=O)Oc1ccccc1C(=O)O

Molecular Descriptors:
  MW            : 180.16
  LogP          : 1.31
  ...

Prediction Results:
  Receptor   Activity      Active%  Inactive%  AD
  ------------------------------------------------
  AR         Inactive          3.1       96.9  Reliable
  ERA        Inactive          8.4       91.6  Reliable
  ...
```

Save to a file instead:
```bash
python pytox_gui.py --no-gui --smiles "CC(=O)Oc1ccccc1C(=O)O" --name Aspirin --output aspirin.csv
```

### Batch prediction

```bash
python pytox_gui.py --no-gui --csv compounds.csv --smiles-col SMILES --output results.xlsx
```

- **CSV output** (`.csv`): one row per compound × receptor combination (long format)
- **Excel output** (`.xlsx`): one sheet per receptor

If `--smiles-col` is omitted, the tool looks for a column named `SMILES` (case-insensitive).

### All options

| Option | Default | Description |
|--------|---------|-------------|
| `--no-gui` | — | Run without the desktop window |
| `--smiles SMILES` | — | SMILES string (single compound mode) |
| `--csv FILE` | — | Input CSV or Excel file (batch mode) |
| `--smiles-col COL` | `SMILES` | Column name containing SMILES |
| `--name NAME` | `Compound` | Compound name label |
| `--fp {morgan,maccs}` | `morgan` | Fingerprint type |
| `--algo {svm,superlearner}` | `svm` | Prediction algorithm |
| `--receptors R [R ...]` | all nine | Predict only these receptors (e.g. `AR ERA GR`) |
| `--scutoff FLOAT` | `0.25` | AD Tanimoto similarity cutoff (0–1) |
| `--nsimilar INT` | `1` | AD minimum similar neighbours |
| `--output FILE` | stdout | Output file (`.csv` or `.xlsx`) |

```bash
python pytox_gui.py --help
```

### Examples

```bash
# MACCS fingerprint, specific receptors
python pytox_gui.py --no-gui --smiles "CC(C)(c1ccc(O)cc1)c1ccc(O)cc1" \
    --fp maccs --receptors AR ERA ERB --output bpa.csv

# Strict AD settings
python pytox_gui.py --no-gui --smiles "..." --scutoff 0.5 --nsimilar 3

# Batch with a non-default SMILES column name
python pytox_gui.py --no-gui --csv library.xlsx --smiles-col "Canonical_SMILES" \
    --output results.xlsx
```

---

## 6. Understanding the Results

### Result table columns

| Column | Description |
|--------|-------------|
| Receptor | The nuclear receptor being predicted |
| Activity | Active or Inactive |
| Active % | Model confidence that the compound is Active |
| Inactive % | Model confidence that the compound is Inactive |
| AD | Reliable or Unreliable |

### Molecular descriptors (Single Prediction tab / CLI)

| Descriptor | Meaning |
|------------|---------|
| MW | Molecular weight (g/mol) |
| LogP | Octanol-water partition coefficient (lipophilicity) |
| HBD | Hydrogen bond donors |
| HBA | Hydrogen bond acceptors |
| TPSA | Topological polar surface area (Å²) |
| RotBonds | Number of rotatable bonds |

### Color coding (GUI)

- **Active** — highlighted in green
- **Inactive** — highlighted in red
- **Reliable** — teal label; prediction is within the training chemical space
- **Unreliable** — orange label; compound is outside the training chemical space; interpret with caution

---

## 7. Applicability Domain Parameters

The **AD Parameters** panel controls when a prediction is considered **Reliable**.

### Scutoff (Similarity Cutoff)

- Range: 0.0 – 1.0 (default: **0.25**)
- A Tanimoto similarity of 1.0 means the compound is identical to a training compound.
- Higher values → stricter AD → fewer compounds are Reliable.
- **Recommended:** 0.25 for general screening; 0.4–0.6 for high-confidence assessments.

### Nsimilar (Minimum Neighbors)

- Range: 1 – 20 (default: **1**)
- The compound must be similar to at least this many training compounds at the Scutoff threshold to be Reliable.
- Higher values → stricter AD.
- **Recommended:** 1 for permissive screening; 3–5 for conservative assessments.

### How the AD works

For each compound × receptor pair:
1. Tanimoto similarity is computed between the compound's fingerprint and every training set compound's fingerprint.
2. The number of training compounds with similarity ≥ Scutoff is counted.
3. If that count ≥ Nsimilar, the prediction is **Reliable**; otherwise **Unreliable**.

---

## 8. Troubleshooting

### The app starts but no models are found

Make sure `MODELS/` and `X_train/` are in the expected location (see [Section 2](#2-setting-up-model-files)). If the download dialog appeared but you dismissed it, restart the app — it will offer to download again.

### "No SVM models found" error when clicking Predict

The model files were not downloaded or are in an unexpected location. Restart the app — the download dialog will appear. If it does not appear, the app found the folders but they may be incomplete. Delete the `MODELS/` folder and restart to trigger a fresh download.

### "SuperLearner models not downloaded" error

You selected the **SuperLearner** algorithm but only downloaded the SVM models. Either:
- Switch the **Algorithm** dropdown back to **SVM**, or
- Restart the app and click **Download All (~12 GB)** to get the SuperLearner models.

### Prediction is slow the first time

The first prediction loads all models and computes applicability domain training matrices. This can take 10–30 seconds depending on your machine. Subsequent predictions in the same session are near-instant because everything is cached in memory.

### My SMILES is rejected / no structure shown

- Make sure the SMILES is valid. Test it at [PubChem Structure Search](https://pubchem.ncbi.nlm.nih.gov/#input_type=structure&query_type=search).
- Stereochemistry (`@`, `/`, `\`) is automatically stripped before prediction.
- Salts and mixtures (`.`-separated components) are handled by taking the largest fragment.

### `ImportError: No module named 'rdkit'`

Install RDKit via conda:

```bash
conda install -c conda-forge rdkit
```

Do **not** install with pip — it is not the same package.

### The Excel export fails

Make sure `openpyxl` is installed:

```bash
pip install openpyxl
```

### scikit-learn version mismatch warning

The models were trained with scikit-learn 0.23.2. Using a different version may produce a warning or incorrect results. The `requirements.txt` pins the correct version:

```bash
pip install scikit-learn==0.23.2
```

### CLI: "Model files not found" error

The CLI cannot auto-download models. Run the GUI first to download them:

```bash
python pytox_gui.py
```

Once the GUI has downloaded the models, `--no-gui` will find them automatically.

### CLI: batch output has no results for some compounds

Compounds that fail SMILES parsing are recorded with `Activity: ERROR: <reason>` in the output file. Check the SMILES strings for those rows — common causes are unsupported atom types or malformed notation.
