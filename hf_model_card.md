---
language: en
license: mit
tags:
  - toxicity
  - cheminformatics
  - nuclear-receptors
  - sklearn
  - svm
  - rdkit
  - drug-discovery
library_name: sklearn
---

# NR-ToxPred Models

Pre-trained machine learning models for predicting the binding activity of small molecules against **nine human nuclear receptors (NRs)**.

These models are used by the [NR-ToxPred GUI application](https://github.com/gokulalgates/NRToxPred-GUI) — a desktop app that requires no coding experience.

---

## What this repository contains

| Folder | Contents |
|--------|----------|
| `MODELS/morgan/` | SVM classifiers trained on Morgan (ECFP6) fingerprints — one per receptor |
| `MODELS/MACCS/` | SVM classifiers trained on MACCS Keys — one per receptor |
| `MODELS/ARclasses.npy` | Label encoder (Active / Inactive) |
| `X_train/` | Training set SMILES used for Applicability Domain assessment |

> SuperLearner ensemble models are not included here due to their size (1–1.5 GB each).

---

## Receptors covered

| Receptor | Full Name |
|----------|-----------|
| AR | Androgen Receptor |
| ERA | Estrogen Receptor Alpha |
| ERB | Estrogen Receptor Beta |
| FXR | Farnesoid X Receptor |
| GR | Glucocorticoid Receptor |
| PPARD | Peroxisome Proliferator-Activated Receptor Delta |
| PPARG | Peroxisome Proliferator-Activated Receptor Gamma |
| PR | Progesterone Receptor |
| RXR | Retinoid X Receptor |

---

## How to use

### Option A — Desktop GUI (recommended, no coding needed)

Download the NR-ToxPred GUI from GitHub and run the installer. The app will download these models automatically on first launch.

👉 **[NR-ToxPred GUI on GitHub](https://github.com/gokulalgates/NRToxPred-GUI)**

### Option B — Python (programmatic use)

```python
from huggingface_hub import hf_hub_download
import pickle, numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem

# Download a model
model_path = hf_hub_download(
    repo_id="gokulalgates/nrtoxpred-models",
    filename="MODELS/morgan/ARsvm_best.model",
    repo_type="model",
)

# Load model
model = pickle.load(open(model_path, "rb"))

# Generate Morgan fingerprint (ECFP6, 1024 bits)
mol = Chem.MolFromSmiles("CC(C)(c1ccc(O)cc1)c1ccc(O)cc1")  # bisphenol A
fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius=3, nBits=1024)
X = np.array(fp).reshape(1, -1)

# Predict
label_enc = {0: "Inactive", 1: "Active"}
pred = model.predict(X)[0]
print(f"AR prediction: {pred}")
```

---

## Model details

| Property | Value |
|----------|-------|
| Algorithm | Support Vector Machine (SVM) |
| Fingerprints | Morgan ECFP6 (radius=3, 1024 bits) and MACCS Keys (167 bits) |
| Framework | scikit-learn 0.23.2 |
| Task | Binary classification (Active / Inactive) |
| Applicability Domain | Tanimoto fingerprint similarity to training set |

---

## Applicability Domain

Each prediction comes with a reliability label:

- **Reliable** — the compound is similar (Tanimoto ≥ 0.25) to at least one training set compound
- **Unreliable** — the compound lies outside the training chemical space; interpret with caution

The `X_train/` folder contains the training set SMILES used to compute these assessments.

---

## Citation

If you use these models in your research, please cite:

> Predicting the binding of small molecules to nuclear receptors using machine learning.
> *Brief Bioinform.* 2022 May 13;23(3):bbac114.
> doi: [10.1093/bib/bbac114](https://doi.org/10.1093/bib/bbac114)

---

## License

MIT License
