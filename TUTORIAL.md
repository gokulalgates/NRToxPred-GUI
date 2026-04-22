# NR-ToxPred GUI — Tutorial

This guide walks you through installing, configuring, and using the NR-ToxPred desktop application.

> **Citation:** If you use NR-ToxPred in your research, please cite:
> Predicting the binding of small molecules to nuclear receptors using machine learning.
> *Brief Bioinform.* 2022 May 13;23(3):bbac114. doi: [10.1093/bib/bbac114](https://doi.org/10.1093/bib/bbac114)

---

## Table of Contents

1. [Installation](#1-installation)
2. [Setting Up Model Files](#2-setting-up-model-files)
3. [Single Compound Prediction](#3-single-compound-prediction)
4. [Batch Prediction](#4-batch-prediction)
5. [Understanding the Results](#5-understanding-the-results)
6. [Applicability Domain Parameters](#6-applicability-domain-parameters)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Installation

### Step 1 — Clone the repository

```bash
git clone https://github.com/gokulalgates/NRToxPred-GUI.git
cd NRToxPred-GUI
```

### Step 2 — Create a conda environment

Using conda is strongly recommended because RDKit and OpenBabel are easiest to install through it.

```bash
conda create -n nrtoxpred python=3.9
conda activate nrtoxpred
```

### Step 3 — Install RDKit and OpenBabel

```bash
conda install -c conda-forge rdkit openbabel
```

### Step 4 — Install remaining Python packages

```bash
pip install -r requirements.txt
```

This installs: `molvs`, `scikit-learn==0.23.2`, `pandas`, `numpy`, `scipy`, `openpyxl`, `Pillow`, `huggingface_hub`.

### Step 5 — Verify the installation

```bash
python -c "from rdkit import Chem; print('OK')"
```

If you see `OK`, the core dependencies are ready.

---

## 2. Setting Up Model Files

The application needs pre-trained model files to make predictions. These are **not** included in the GitHub repository due to their size (~310 MB for SVM models).

### Option A — Auto-download from Hugging Face (recommended)

If the Hugging Face repository is configured, the app will show a **Download Models** dialog on first launch and fetch everything automatically.

To enable this, open `pytox_gui.py` in a text editor and find line 22:

```python
HF_REPO = ""   # set to "YourName/nrtoxpred-models" after uploading
```

Change it to the actual Hugging Face repository ID:

```python
HF_REPO = "gokulalgates/nrtoxpred-models"
```

Then launch the app — it will offer to download models if they are missing.

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
│   │   ├── PPARD svm_best.model
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
   - **SVM** — Support Vector Machine. Fast and accurate; recommended for most use cases.
   - **SuperLearner** — Ensemble of multiple classifiers. More accurate but requires much larger model files (~1.5 GB per receptor).

7. **Adjust AD Parameters** if needed (see [Section 6](#6-applicability-domain-parameters)).

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

## 5. Understanding the Results

### Result table columns

| Column | Description |
|--------|-------------|
| Receptor | The nuclear receptor being predicted |
| Prediction | Active or Inactive |
| AD | Reliable or Unreliable |

### Molecular descriptors (Single Prediction tab)

| Descriptor | Meaning |
|------------|---------|
| MW | Molecular weight (g/mol) |
| LogP | Octanol-water partition coefficient (lipophilicity) |
| HBD | Hydrogen bond donors |
| HBA | Hydrogen bond acceptors |
| TPSA | Topological polar surface area (Å²) |
| RotBonds | Number of rotatable bonds |

### Color coding

- **Active** — highlighted in green
- **Inactive** — highlighted in red
- **Reliable** — teal label; prediction is within the training chemical space
- **Unreliable** — orange label; compound is outside the training chemical space; interpret with caution

---

## 6. Applicability Domain Parameters

The **AD Parameters** panel is visible in both tabs. It controls when a prediction is considered **Reliable**.

### Scutoff (Similarity Cutoff)

- Range: 0.0 – 1.0 (default: **0.25**)
- A Tanimoto similarity score of 1.0 means the compound is identical to a training compound.
- Higher values → stricter AD → fewer compounds are Reliable.
- **Recommended:** 0.25 for general screening; 0.4–0.6 for high-confidence assessments.

### Nsimilar (Minimum Neighbors)

- Range: 1 – 10 (default: **1**)
- The compound must be similar to at least this many training compounds at the Scutoff threshold to be Reliable.
- Higher values → stricter AD.
- **Recommended:** 1 for permissive screening; 3–5 for conservative assessments.

### How the AD works

For each compound × receptor pair:
1. Tanimoto similarity is computed between the compound's fingerprint and every training set compound's fingerprint.
2. The number of training compounds with similarity ≥ Scutoff is counted.
3. If that count ≥ Nsimilar, the prediction is **Reliable**; otherwise **Unreliable**.

---

## 7. Troubleshooting

### The app starts but no models are found

Make sure `MODELS/` and `X_train/` exist next to `pytox_gui.py`. If `HF_REPO` is set, click **Download** in the dialog that appears at startup.

### `ImportError: No module named 'rdkit'`

Install RDKit via conda:

```bash
conda install -c conda-forge rdkit
```

### Prediction is slow the first time

The first prediction loads all models and computes the applicability domain training matrices. This can take 10–30 seconds depending on your machine. Subsequent predictions in the same session are near-instant because everything is cached in memory.

### My SMILES is rejected / no structure shown

- Make sure the SMILES is valid. Test it at [https://www.cheminfo.org/Chemistry/Cheminformatics/SMILES_parser/index.html](https://www.cheminfo.org/Chemistry/Cheminformatics/SMILES_parser/index.html)
- Stereochemistry (`@`, `/`, `\`) is automatically stripped before prediction.
- Salts and mixtures (`.`-separated components) are handled by taking the largest fragment.

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
