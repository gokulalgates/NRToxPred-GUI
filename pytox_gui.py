"""
NR-ToxPred GUI — standalone tkinter application.
Run from the Pytox directory:  python pytox_gui.py
"""

import argparse
import datetime
import os
import sys
import re
import pickle
import warnings
import queue
import threading

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    _HAS_TK = True
except ImportError:
    _HAS_TK = False

warnings.filterwarnings("ignore")

# ── Crash log: written before every major import so a C-level segfault leaves
# a breadcrumb trail in crash.log next to pytox_gui.py ───────────────────────
_CRASH_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash.log")

def _log(msg: str):
    try:
        with open(_CRASH_LOG, "a", encoding="utf-8") as _f:
            _f.write(f"[{datetime.datetime.now():%H:%M:%S}] {msg}\n")
            _f.flush()
    except Exception:
        pass

import traceback as _traceback

def _excepthook(et, ev, tb):
    _log("UNHANDLED EXCEPTION:\n" + "".join(_traceback.format_exception(et, ev, tb)))
    sys.__excepthook__(et, ev, tb)

sys.excepthook = _excepthook
_log("--- startup ---")

# ── make sure relative model/X_train paths resolve correctly ──────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

# ── Model storage location ────────────────────────────────────────────────────
# On Windows, download to AppData\Local\NRToxPred so OneDrive never interferes.
# On Mac/Linux, use the script directory as before.
import platform as _platform
if _platform.system() == "Windows":
    _appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    _DEFAULT_MODELS_BASE = os.path.join(_appdata, "NRToxPred")
else:
    _DEFAULT_MODELS_BASE = SCRIPT_DIR

def _get_models_base() -> str:
    """Return the directory that contains the MODELS/ and X_train/ folders.
    Checks the AppData location first (downloaded), then falls back to
    the script directory (manual placement)."""
    probe = os.path.join("MODELS", "morgan", "ARsvm_best.model")
    for base in [_DEFAULT_MODELS_BASE, SCRIPT_DIR]:
        if os.path.exists(os.path.join(base, probe)):
            return base
    return _DEFAULT_MODELS_BASE  # default destination for new downloads

# ── Hugging Face model auto-download ─────────────────────────────────────────
HF_REPO = "gokulalgates/nrtoxpred-models"

def _models_present() -> bool:
    """Return True if the minimum required SVM models exist in any known location."""
    probe = [
        os.path.join("MODELS", "morgan", "ARsvm_best.model"),
        os.path.join("MODELS", "ARclasses.npy"),
        os.path.join("X_train", "AR.xlsx"),
    ]
    for base in [_DEFAULT_MODELS_BASE, SCRIPT_DIR]:
        if all(os.path.exists(os.path.join(base, p)) for p in probe):
            return True
    return False


def download_models_from_hf(progress_cb=None, svm_only=False):
    """
    Download models from Hugging Face Hub using snapshot_download.
    svm_only=True  → SVM models + X_train (~250 MB)
    svm_only=False → SVM + SuperLearner   (~12 GB)
    progress_cb(msg, current, total) is called for status updates.
    """
    if not HF_REPO:
        raise ValueError(
            "HF_REPO is not set in pytox_gui.py.\n"
            "Edit the file and set HF_REPO = 'YourName/nrtoxpred-models'.")
    try:
        from huggingface_hub import snapshot_download, list_repo_files
    except ImportError:
        raise ImportError(
            "huggingface_hub is not installed.\n"
            "Run:  pip install huggingface_hub")

    # Show immediately so the UI isn't frozen while the file list loads
    if progress_cb:
        progress_cb("Connecting to Hugging Face…", 0, 1)

    all_files = [f for f in list_repo_files(HF_REPO, repo_type="model")
                 if not f.startswith(".") and f != "README.md"]

    if svm_only:
        files = [f for f in all_files if "_SL.model" not in f]
        ignore = ["*_SL.model", "README.md", ".gitattributes"]
    else:
        files = all_files
        ignore = ["README.md", ".gitattributes"]

    total = len(files)
    if progress_cb:
        progress_cb(f"Downloading {total} files — please wait…", 0, total)

    # Download to AppData\Local\NRToxPred on Windows (avoids OneDrive sync issues),
    # or to the script directory on Mac/Linux.
    dest = _DEFAULT_MODELS_BASE
    os.makedirs(dest, exist_ok=True)

    try:
        # local_dir_use_symlinks=False forces real file copies instead of
        # symlinks to the HF cache, so files are visible in the folder.
        snapshot_download(
            repo_id=HF_REPO,
            repo_type="model",
            local_dir=dest,
            local_dir_use_symlinks=False,
            ignore_patterns=ignore,
        )
    except TypeError:
        # Older huggingface_hub doesn't have local_dir_use_symlinks
        snapshot_download(
            repo_id=HF_REPO,
            repo_type="model",
            local_dir=dest,
            ignore_patterns=ignore,
        )

    # Verify files actually landed in dest
    probe = os.path.join(dest, "MODELS", "morgan", "ARsvm_best.model")
    if not os.path.exists(probe):
        raise FileNotFoundError(
            f"Download finished but model files were not found in:\n  {dest}\n\n"
            "Try updating huggingface_hub:\n  pip install -U huggingface_hub")

    if progress_cb:
        progress_cb("Download complete!", total, total)

# ── heavy scientific imports ──────────────────────────────────────────────────
IMPORTS_OK = False
IMPORT_ERROR = ""
_standardize_smiles_fn = None  # set below if molvs is available

try:
    _log("importing numpy")
    import numpy as np
    _log("importing pandas")
    import pandas as pd
    _log("importing PIL")
    from PIL import Image, ImageTk
    _log("importing rdkit.Chem")
    from rdkit import Chem
    _log("importing rdkit.Chem submodules")
    from rdkit.Chem import AllChem, MACCSkeys, Descriptors, rdMolDescriptors, Draw
    from rdkit.Chem.MolStandardize import rdMolStandardize
    _log("importing rdkit RDLogger")
    from rdkit import RDLogger as _RDLogger
    _RDLogger.DisableLog("rdApp.warning")
    _RDLogger.DisableLog("rdApp.error")
    _log("importing sklearn")
    from sklearn.preprocessing import LabelEncoder
    _log("importing pyAppDomain")
    sys.path.insert(0, SCRIPT_DIR)
    from toxi.pyAppDomain import AppDomainFpSimilarity
    _log("all core imports OK")
    IMPORTS_OK = True
except Exception as _e:
    IMPORT_ERROR = str(_e)
    _log(f"IMPORT FAILED: {_e}")

# molvs is optional — fall back to rdkit-only standardization if absent
try:
    from molvs import standardize_smiles as _molvs_standardize
    _standardize_smiles_fn = _molvs_standardize
    _log("molvs OK")
except Exception:
    _standardize_smiles_fn = None
    _log("molvs not available — using rdkit-only standardization")

# SyGMa is optional — enables Phase I metabolite prediction
try:
    from syGMa.molecule import Molecule as _SyGMaMolecule
    from syGMa.scenario import Scenario as _SyGMaScenario
    _HAS_SYGMA = True
    _log("syGMa OK")
except Exception:
    _HAS_SYGMA = False
    _log("syGMa not available — metabolite prediction disabled")

# ─────────────────────────────────────────────────────────────────────────────
# Core prediction helpers  (no Django / Celery dependency)
# ─────────────────────────────────────────────────────────────────────────────

from concurrent.futures import ThreadPoolExecutor, as_completed

BINARY_RECEPTORS  = ["RXR", "PR", "GR", "AR", "ERA", "ERB", "FXR", "PPARD", "PPARG"]
FINGERPRINT_TYPES = ["morgan", "maccs"]
ALGORITHMS        = ["svm", "superlearner"]

# ── In-memory caches (populated once, reused forever) ─────────────────────────
# Key: model file path  →  loaded sklearn model object
_model_cache: dict = {}
# Key: (fp_type, receptor)  →  AppDomainFpSimilarity already fitted on X_train
_adfs_cache: dict  = {}
# Simple lock so the background pre-warm thread and the UI thread don't race
import threading as _threading
_cache_lock = _threading.Lock()

# Thread-safe UI update queue: background threads post callables here;
# the main thread drains it via NRToxPredApp._poll_ui_queue().
_ui_queue: queue.Queue = queue.Queue()

_encoder = None


def _get_encoder():
    global _encoder
    if _encoder is None:
        enc = LabelEncoder()
        enc.fit(["Active", "Inactive"])
        _encoder = enc
    return _encoder


def _sl_predict_scores(model, X) -> "np.ndarray":
    """
    SuperLearner.predict may return shape (N,), (N,1), (N, k), or a list of rows.
    Return a 1D float64 array with one score per input row.
    X must be float (some stacks fail on uint8 bit vectors).
    """
    X = np.ascontiguousarray(X, dtype=np.float64)
    n = int(X.shape[0])
    y = model.predict(X)
    a = np.asarray(y)
    if a.shape == ():
        return np.array([float(a)], dtype=np.float64)
    try:
        a = np.asarray(a, dtype=np.float64, order="C")
        a = a.reshape(n, -1)
    except (TypeError, ValueError):
        raw = a.ravel() if a.size else a
        seq = [float(np.ravel(x, order="C")[0]) for x in raw] if np.size(raw) else []
        a = np.asarray(seq, dtype=np.float64).reshape(n, -1)
    return a[:, 0]


# ── Cached loaders ────────────────────────────────────────────────────────────

def _load_model(path: str):
    """Load and cache a pickle model; subsequent calls return the cached object."""
    with _cache_lock:
        if path not in _model_cache:
            _model_cache[path] = pickle.load(open(path, "rb"))
        return _model_cache[path]


def _load_adfs(fp_type: str, receptor: str):
    """
    Load X_train, build + fit AppDomainFpSimilarity, and cache it.
    The expensive part (reading Excel + computing all pairwise training
    fingerprint similarities) only runs once per (fp_type, receptor) pair.
    Returns None if the X_train file is missing.
    """
    key = (fp_type, receptor)
    with _cache_lock:
        if key in _adfs_cache:
            return _adfs_cache[key]

    xtrain_file = os.path.join(_get_models_base(), "X_train", f"{receptor}.xlsx")
    if not os.path.exists(xtrain_file):
        with _cache_lock:
            _adfs_cache[key] = None
        return None

    X_train = pd.read_excel(xtrain_file, sheet_name="X_train", engine="openpyxl")
    adfs = AppDomainFpSimilarity(X_train, smiCol="SMILES")
    if fp_type == "morgan":
        adfs.fpSimilarity_analyze("Morgan(bit)", nBits=1024, radius=3)
    else:
        adfs.fpSimilarity_analyze("MACCS_keys")

    with _cache_lock:
        _adfs_cache[key] = adfs
    return adfs


def prewarm_cache(fp_types=("morgan", "maccs"), algorithm="svm",
                  status_cb=None):
    """
    Load all models and AD training data into memory.
    Call once in a background thread at startup so the first prediction
    is instant.  status_cb(msg) is called with progress strings.
    """
    tasks = []
    for fp in fp_types:
        for rec in BINARY_RECEPTORS:
            path = _model_path(fp, rec, algorithm)
            if os.path.exists(path):
                tasks.append(("model", fp, rec, path))
            tasks.append(("adfs", fp, rec, None))

    for kind, fp, rec, path in tasks:
        try:
            if kind == "model":
                _load_model(path)
                if status_cb:
                    status_cb(f"Loaded model: {rec} ({fp})")
            else:
                _load_adfs(fp, rec)
                if status_cb:
                    status_cb(f"Loaded AD data: {rec} ({fp})")
        except Exception:
            pass


# ── Chemistry helpers ─────────────────────────────────────────────────────────

def _model_path(fp_type: str, receptor: str, algorithm: str) -> str:
    folder = "morgan" if fp_type == "morgan" else "MACCS"
    fname  = (receptor + "svm_best.model") if algorithm == "svm" else (receptor + "_SL.model")
    return os.path.join(_get_models_base(), "MODELS", folder, fname)


def _rdkit_canonical(smi: str) -> str:
    """Return RDKit canonical SMILES, or raise ValueError if unparseable."""
    mol = Chem.MolFromSmiles(smi)
    if mol is None:
        raise ValueError(f"Could not parse SMILES: {smi}")
    return Chem.MolToSmiles(mol)


def _standardize_smiles(smiles: str):
    """Return (rdkit_mol, can_smiles_str, data_df) for a single SMILES."""
    data = pd.DataFrame({"SMILES": [smiles]})
    data["STEROREMOVED"] = [re.sub(r"[/@\\]", "", s) for s in data["SMILES"]]
    data["can_smiles"] = [_rdkit_canonical(s) for s in data["STEROREMOVED"]]
    can = data["can_smiles"][0]
    if _standardize_smiles_fn is not None:
        try:
            can = _standardize_smiles_fn(can)
        except Exception:
            pass
    mol1 = Chem.MolFromSmiles(can)
    if mol1 is None:
        raise ValueError("RDKit could not parse the standardized SMILES.")
    mol = rdMolStandardize.ChargeParent(mol1)
    return mol, data["can_smiles"][0], data


def _make_fp_array(mol, fp_type: str):
    """Return (numpy bit-array, nBits) for a single molecule."""
    if fp_type == "morgan":
        # Pass radius as positional arg — newer RDKit made it positional-only
        fp = AllChem.GetMorganFingerprintAsBitVect(mol, 3, nBits=1024)
        return np.array(list(fp), dtype=np.uint8), 1024
    fp = MACCSkeys.GenMACCSKeys(mol)
    return np.array(list(fp), dtype=np.uint8), 167


def _calc_descriptors(mol) -> dict:
    return {
        "HeavyAtomCount": int(Descriptors.HeavyAtomCount(mol)),
        "LogP":           round(Descriptors.MolLogP(mol), 3),
        "MolWt":          round(Descriptors.MolWt(mol), 3),
        "RingCount":      int(Descriptors.RingCount(mol)),
        "TPSA":           round(Descriptors.TPSA(mol), 3),
        "NumAmideBonds":  rdMolDescriptors.CalcNumAmideBonds(mol),
        "NumHBA":         int(rdMolDescriptors.CalcNumHBA(mol)),
        "NumHBD":         int(rdMolDescriptors.CalcNumHBD(mol)),
    }


def _ad_labels(data_df: pd.DataFrame, fp_type: str, receptor: str,
               Nsimilar: int, Scutoff: float) -> list:
    """
    Return a list of 'Reliable'/'Unreliable'/'N/A' strings, one per row.
    Uses the cached AppDomainFpSimilarity — no disk I/O after first call.
    """
    adfs = _load_adfs(fp_type, receptor)
    if adfs is None:
        return ["N/A"] * len(data_df)
    SM_ext    = adfs.fpSimilarity_xenoCheck(data_df, "can_smiles")
    in_ad_idx = adfs.fpSimilarity_xenoFilter(data_df, SM_ext, Scutoff, Nsimilar)
    labels    = ["Unreliable"] * len(data_df)
    for idx in in_ad_idx:
        labels[data_df.index.get_loc(idx)] = "Reliable"
    return labels


# ── Single prediction ─────────────────────────────────────────────────────────

def _predict_one_receptor(rec, fp_type, algorithm, fp_arr, nBits,
                          data_df, Nsimilar, Scutoff):
    """Run AD + model for one receptor; returns a result dict."""
    # AD (cached, fast after first call)
    try:
        ad = _ad_labels(data_df, fp_type, rec, Nsimilar, Scutoff)[0]
    except Exception:
        ad = "N/A"

    model_file = _model_path(fp_type, rec, algorithm)
    if not os.path.exists(model_file):
        return {"Receptor": rec, "Activity": "Model not found",
                "Active%": "-", "Inactive%": "-", "AD": ad}

    model    = _load_model(model_file)   # cached
    fp_vals  = fp_arr.reshape(1, -1)
    encoder  = _get_encoder()

    if algorithm == "svm":
        y_pred      = model.predict(fp_vals)
        y_pred_prob = model.predict_proba(fp_vals)
        activity    = encoder.classes_[y_pred][0]
        active_pct  = round(y_pred_prob[0][0] * 100, 1)
        inact_pct   = round(y_pred_prob[0][1] * 100, 1)
    else:
        cols   = [f"Bit_{i}" for i in range(nBits)]
        df0    = pd.DataFrame([np.asarray(fp_arr, dtype=np.float64)], columns=cols)
        df_rep = pd.concat([df0.copy() for _ in range(10)], ignore_index=True)
        scores_1d = _sl_predict_scores(model, df_rep.values)
        score  = float(scores_1d[0])
        activity   = "Active" if score >= 0.6 else "Inactive"
        active_pct = round(score * 100, 1)
        inact_pct  = round((1 - score) * 100, 1)

    return {"Receptor": rec, "Activity": activity,
            "Active%": active_pct, "Inactive%": inact_pct, "AD": ad}


def predict_single(smiles: str, name: str, fp_type: str, algorithm: str,
                   receptors: list, Nsimilar: int = 1,
                   Scutoff: float = 0.25) -> tuple:
    """
    Returns (descriptors_dict, results_list).
    Receptors are evaluated in parallel using a thread pool.
    """
    mol, can_smiles, data = _standardize_smiles(smiles)
    descriptors = _calc_descriptors(mol)
    fp_arr, nBits = _make_fp_array(mol, fp_type)

    # SVM: parallel (cached models are small + thread-safe). SuperLearner:
    # one receptor at a time to avoid OOM and mlens/parallel edge cases.
    n_workers = (1 if algorithm == "superlearner"
                 else min(len(receptors), os.cpu_count() or 4))
    results_map = {}
    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        futures = {
            pool.submit(_predict_one_receptor,
                        rec, fp_type, algorithm, fp_arr, nBits,
                        data, Nsimilar, Scutoff): rec
            for rec in receptors
        }
        for fut in as_completed(futures):
            rec = futures[fut]
            try:
                results_map[rec] = fut.result()
            except Exception as e:
                results_map[rec] = {"Receptor": rec, "Activity": f"ERROR: {e}",
                                    "Active%": "-", "Inactive%": "-", "AD": "N/A"}

    # Preserve the user-selected receptor order
    results = [results_map[r] for r in receptors if r in results_map]
    return descriptors, results


# ── Batch prediction ──────────────────────────────────────────────────────────

def _standardize_one(args):
    """Worker for parallel SMILES standardization."""
    idx, smi, nm = args
    try:
        mol, can_smi, _ = _standardize_smiles(smi)
        fp_morgan, _ = _make_fp_array(mol, "morgan")
        fp_maccs,  _ = _make_fp_array(mol, "maccs")
        return idx, nm, smi, can_smi, mol, fp_morgan, fp_maccs, None
    except Exception as e:
        return idx, nm, smi, None, None, None, None, str(e)


def predict_batch(df: pd.DataFrame, fp_type: str, algorithm: str,
                  receptors: list, Nsimilar: int = 1, Scutoff: float = 0.25,
                  progress_cb=None) -> dict:
    """
    Vectorized batch prediction.
    • All SMILES are standardized once (in parallel threads).
    • Fingerprint matrix is built once and reused across all receptors.
    • AD is evaluated per-receptor on the whole batch at once (no per-row loop).
    • Model inference runs on the full matrix in one call.
    """
    # ── normalise column names ────────────────────────────────────────────────
    col_map  = {c: c.upper() for c in df.columns}
    df       = df.rename(columns=col_map)
    smi_col  = next((c for c in df.columns if c == "SMILES"), None)
    name_col = next((c for c in df.columns if c in ("NAME", "NAMES")), None)
    if smi_col is None:
        raise ValueError("CSV must have a SMILES column.")
    if name_col is None:
        df["NAME"] = [f"Compound_{i}" for i in range(len(df))]
        name_col = "NAME"

    # ── Step 1: standardize all SMILES in parallel ────────────────────────────
    if progress_cb:
        progress_cb(0, len(receptors) + 1, "Standardizing SMILES…")

    tasks = [(i, row[smi_col], row[name_col])
             for i, (_, row) in enumerate(df.iterrows())]

    n_workers = min(len(tasks), os.cpu_count() or 4)
    std_results = [None] * len(tasks)
    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        for res in pool.map(_standardize_one, tasks):
            std_results[res[0]] = res

    # ── Step 2: split into passed / failed, build shared data structures ──────
    passed, failed = [], []
    for res in std_results:
        idx, nm, smi, can_smi, mol, fp_morgan, fp_maccs, err = res
        if err:
            failed.append({"NAME": nm, "SMILES": smi,
                           "Active%": "-", "Inactive%": "-",
                           "Activity": f"ERROR: {err}", "AD": "N/A"})
        else:
            passed.append({"idx": idx, "NAME": nm, "SMILES": smi,
                           "can_smiles": can_smi, "mol": mol,
                           "fp_morgan": fp_morgan, "fp_maccs": fp_maccs})

    if not passed:
        if progress_cb:
            progress_cb(len(receptors) + 1, len(receptors) + 1, "Done")
        return {rec: pd.DataFrame(failed) for rec in receptors}

    # Build the fingerprint matrix and the can_smiles DataFrame once
    fp_key = "fp_morgan" if fp_type == "morgan" else "fp_maccs"
    nBits  = 1024 if fp_type == "morgan" else 167
    fp_matrix  = np.vstack([p[fp_key] for p in passed])        # shape (N, nBits)
    bit_cols   = [f"Bit_{i}" for i in range(nBits)]
    can_smi_df = pd.DataFrame({"can_smiles": [p["can_smiles"] for p in passed]})

    encoder = _get_encoder()
    results_by_rec = {}
    total = len(receptors)

    # ── Step 3: per-receptor vectorized inference ─────────────────────────────
    for r_idx, rec in enumerate(receptors):
        if progress_cb:
            progress_cb(r_idx + 1, total + 1, rec)

        model_file = _model_path(fp_type, rec, algorithm)
        if not os.path.exists(model_file):
            results_by_rec[rec] = pd.DataFrame(failed)
            continue

        model = _load_model(model_file)

        # AD for the whole batch at once (no per-row loop)
        try:
            ad_labels = _ad_labels(can_smi_df, fp_type, rec, Nsimilar, Scutoff)
        except Exception:
            ad_labels = ["N/A"] * len(passed)

        # Batch model inference
        if algorithm == "svm":
            y_pred      = model.predict(fp_matrix)
            y_pred_prob = model.predict_proba(fp_matrix)
            activities  = encoder.classes_[y_pred].tolist()
            active_pcts = (y_pred_prob[:, 0] * 100).round(1).tolist()
            inact_pcts  = (y_pred_prob[:, 1] * 100).round(1).tolist()
        else:
            df_fp = pd.DataFrame(
                np.asarray(fp_matrix, dtype=np.float64), columns=bit_cols
            )
            if len(passed) <= 10:
                df_rep = pd.concat([df_fp.copy() for _ in range(10)], ignore_index=True)
                scores_1d = _sl_predict_scores(model, df_rep.values)
            else:
                scores_1d = _sl_predict_scores(model, df_fp.values)
            # 10x replication stacks row blocks; first N outputs match the N compounds.
            block = scores_1d[: len(passed)]
            activities  = [
                "Active" if float(s) >= 0.6 else "Inactive" for s in block
            ]
            active_pcts = [round(float(s) * 100, 1) for s in block]
            inact_pcts  = [round((1 - float(s)) * 100, 1) for s in block]

        rows = [
            {"NAME": p["NAME"], "SMILES": p["SMILES"],
             "Active%": active_pcts[i], "Inactive%": inact_pcts[i],
             "Activity": activities[i], "AD": ad_labels[i]}
            for i, p in enumerate(passed)
        ] + failed

        results_by_rec[rec] = pd.DataFrame(rows)

    if progress_cb:
        progress_cb(total + 1, total + 1, "Done")
    return results_by_rec


def mol_to_pil(smiles: str, size=(310, 220)):
    """Return a PIL Image for the molecule — safe to call from any thread."""
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        return Draw.MolToImage(mol, size=size)
    except Exception:
        return None


def pil_to_photo(pil_img) -> "ImageTk.PhotoImage | None":
    """Convert a PIL Image to ImageTk.PhotoImage — must run on the main thread."""
    if pil_img is None:
        return None
    try:
        return ImageTk.PhotoImage(pil_img)
    except Exception:
        return None


def generate_metabolites(smiles: str, n_steps: int = 1,
                         max_mets: int = 5) -> list:
    """
    Predict Phase I metabolites using SyGMa reaction rules.
    Returns list of (smiles, probability) sorted by probability descending.
    Returns [] if SyGMa is not installed.
    """
    if not _HAS_SYGMA:
        return []
    try:
        parent = _SyGMaMolecule(smiles)
        scenario = _SyGMaScenario([("phase1", n_steps)])
        metabolites = scenario.run(parent)
        seen = {smiles}
        results = []
        for m in metabolites:
            if m.smiles and m.smiles not in seen:
                seen.add(m.smiles)
                results.append((m.smiles, m.probability))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:max_mets]
    except Exception:
        return []


# ─────────────────────────────────────────────────────────────────────────────
# GUI theme
# ─────────────────────────────────────────────────────────────────────────────

COLORS = {
    "bg":        "#f5f5f5",
    "surface":   "#ffffff",
    "surface2":  "#e8e8e8",
    "accent":    "#1565c0",   # deep blue
    "accent2":   "#00796b",   # teal
    "text":      "#212121",
    "subtext":   "#616161",
    "active":    "#2e7d32",   # dark green
    "inactive":  "#c62828",   # dark red
    "reliable":  "#00695c",   # dark teal
    "unreliable":"#e65100",   # dark orange
    "border":    "#bdbdbd",
    "entry_bg":  "#ffffff",
}

FONT_TITLE = ("Helvetica", 18, "bold")
FONT_HEAD  = ("Helvetica", 11, "bold")
FONT_BODY  = ("Helvetica", 10)
FONT_MONO  = ("Courier", 10)
FONT_SMALL = ("Helvetica", 9)


class NRToxPredApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NR-ToxPred  |  Nuclear Receptor Toxicity Predictor")
        self.geometry("1150x740")
        self.minsize(920, 640)
        self.configure(bg=COLORS["bg"])
        self._apply_style()
        self._build_menu()
        self._build_header()
        self._build_tabs()
        self._start_prewarm()
        self._poll_ui_queue()

    def _poll_ui_queue(self):
        """Drain _ui_queue on the main thread so background threads can post UI updates safely."""
        try:
            while True:
                fn = _ui_queue.get_nowait()
                fn()
        except queue.Empty:
            pass
        self.after(50, self._poll_ui_queue)

    # ── theming ───────────────────────────────────────────────────────────────
    def _apply_style(self):
        s = ttk.Style(self)
        available = s.theme_names()
        # vista/winnative (Windows native) ignore custom button foreground colors,
        # so we skip them and use clam which respects all style settings.
        for preferred in ("aqua", "clam", "alt", "default"):
            if preferred in available:
                s.theme_use(preferred)
                break
        s.configure(".",
                    background=COLORS["bg"], foreground=COLORS["text"],
                    fieldbackground=COLORS["entry_bg"], troughcolor=COLORS["surface2"],
                    bordercolor=COLORS["border"], focuscolor=COLORS["accent"],
                    font=FONT_BODY)
        s.configure("TNotebook", background=COLORS["bg"], borderwidth=0)
        s.configure("TNotebook.Tab",
                    background=COLORS["surface2"], foreground=COLORS["subtext"],
                    padding=(16, 6), font=FONT_HEAD)
        s.map("TNotebook.Tab",
              background=[("selected", COLORS["surface"])],
              foreground=[("selected", COLORS["accent"])])
        for name, bg in (("TFrame", COLORS["bg"]),
                         ("Surface.TFrame",  COLORS["surface"]),
                         ("Surface2.TFrame", COLORS["surface2"])):
            s.configure(name, background=bg)
        s.configure("TLabel",
                    background=COLORS["bg"], foreground=COLORS["text"], font=FONT_BODY)
        s.configure("Head.TLabel",
                    background=COLORS["bg"], foreground=COLORS["text"], font=FONT_HEAD)
        s.configure("Sub.TLabel",
                    background=COLORS["bg"], foreground=COLORS["subtext"], font=FONT_SMALL)
        s.configure("Accent.TLabel",
                    background=COLORS["bg"], foreground=COLORS["accent"], font=FONT_HEAD)
        s.configure("TEntry",
                    fieldbackground=COLORS["entry_bg"], foreground=COLORS["text"],
                    insertcolor=COLORS["text"], bordercolor=COLORS["border"], font=FONT_BODY)
        s.configure("TCombobox",
                    fieldbackground=COLORS["entry_bg"], foreground=COLORS["text"],
                    background=COLORS["surface2"], selectbackground=COLORS["accent"],
                    selectforeground="#ffffff")
        s.map("TCombobox",
              fieldbackground=[("readonly", COLORS["entry_bg"])],
              foreground=[("readonly", COLORS["text"])])
        s.configure("TButton",
                    background=COLORS["accent"], foreground="#ffffff",
                    font=FONT_HEAD, padding=(14, 6), borderwidth=0, relief="flat")
        s.map("TButton",
              background=[("active", "#1976d2"), ("pressed", "#0d47a1")])
        s.configure("Secondary.TButton",
                    background=COLORS["surface2"], foreground=COLORS["text"])
        s.map("Secondary.TButton",
              background=[("active", COLORS["border"])])
        s.configure("TProgressbar",
                    troughcolor=COLORS["surface2"], background=COLORS["accent"], thickness=6)
        s.configure("Treeview",
                    background=COLORS["surface"], foreground=COLORS["text"],
                    fieldbackground=COLORS["surface"], rowheight=24,
                    font=FONT_BODY, borderwidth=1)
        s.configure("Treeview.Heading",
                    background=COLORS["surface2"], foreground=COLORS["accent"],
                    font=FONT_HEAD, relief="flat")
        s.map("Treeview",
              background=[("selected", COLORS["accent"])],
              foreground=[("selected", "#ffffff")])
        s.configure("TScrollbar",
                    background=COLORS["surface2"], troughcolor=COLORS["bg"],
                    borderwidth=0, arrowcolor=COLORS["subtext"])
        s.configure("TScale",
                    background=COLORS["bg"], troughcolor=COLORS["surface2"],
                    sliderlength=14)
        s.configure("TSpinbox",
                    fieldbackground=COLORS["entry_bg"], foreground=COLORS["text"],
                    background=COLORS["surface2"], arrowcolor=COLORS["subtext"])

    # ── menu bar ──────────────────────────────────────────────────────────────
    def _build_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Download Models…",
                              command=self._show_download_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(
            label="About",
            command=lambda: messagebox.showinfo(
                "About NR-ToxPred",
                "NR-ToxPred\n\nPredicts binding of small molecules to nine "
                "nuclear receptors using pre-trained SVM / SuperLearner models.\n\n"
                "Citation:\nPredicting the binding of small molecules to nuclear "
                "receptors using machine learning.\n"
                "Brief Bioinform. 2022;23(3):bbac114.\n"
                "doi: 10.1093/bib/bbac114"))

    def _show_download_dialog(self):
        dlg = DownloadDialog(self)
        self.wait_window(dlg)
        if _models_present():
            self._cache_lbl.config(text="⏳ Reloading models…",
                                   fg=COLORS["subtext"])
            self._start_prewarm()

    # ── header ────────────────────────────────────────────────────────────────
    def _build_header(self):
        hdr = ttk.Frame(self, style="Surface.TFrame")
        hdr.pack(fill="x", pady=(0, 1))
        inner = ttk.Frame(hdr, style="Surface.TFrame")
        inner.pack(padx=20, pady=10, fill="x")
        tk.Label(inner, text="NR-ToxPred",
                 bg=COLORS["surface"], fg=COLORS["accent"],
                 font=FONT_TITLE).pack(side="left")
        tk.Label(inner, text="  Nuclear Receptor Toxicity Predictor",
                 bg=COLORS["surface"], fg=COLORS["subtext"],
                 font=("Helvetica", 12)).pack(side="left", padx=(6, 0))
        self._cache_lbl = tk.Label(inner, text="⏳ Loading models…",
                                   bg=COLORS["surface"], fg=COLORS["subtext"],
                                   font=FONT_SMALL)
        self._cache_lbl.pack(side="right", padx=8)
        ttk.Button(inner, text="Download Models",
                   style="Secondary.TButton",
                   command=self._show_download_dialog).pack(side="right", padx=(0, 6))

    def _start_prewarm(self):
        """Load all models and AD data in a background thread."""
        def _run():
            def _cb(msg):
                _ui_queue.put(lambda m=msg: self._cache_lbl.config(text=m))
            prewarm_cache(status_cb=_cb)
            _ui_queue.put(lambda: self._cache_lbl.config(
                text="✓ Models ready", fg=COLORS["active"]))
        _threading.Thread(target=_run, daemon=True).start()

    def _build_tabs(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=8)
        self.tab_single = SinglePredTab(nb)
        self.tab_batch  = BatchPredTab(nb)
        self.tab_about  = AboutTab(nb)
        nb.add(self.tab_single, text="  Single Prediction  ")
        nb.add(self.tab_batch,  text="  Batch Prediction   ")
        nb.add(self.tab_about,  text="  About  ")


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _scrolled_tree(parent, columns, heights=12):
    frame = ttk.Frame(parent)
    tree  = ttk.Treeview(frame, columns=columns, show="headings", height=heights)
    vsb   = ttk.Scrollbar(frame, orient="vertical",   command=tree.yview)
    hsb   = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)
    return frame, tree


def _entry(parent, **kw):
    return tk.Entry(parent,
                    bg=COLORS["entry_bg"], fg=COLORS["text"],
                    insertbackground=COLORS["text"], relief="sunken",
                    highlightthickness=1,
                    highlightbackground=COLORS["border"],
                    highlightcolor=COLORS["accent"],
                    font=FONT_BODY, **kw)


def _color_legend(parent, items: list, bg: str):
    """
    Draw a compact legend using small colored canvas squares instead of
    unicode bullet characters (which may not render on all system fonts).
    items: list of (label_text, color_hex)
    """
    for label, color in items:
        swatch = tk.Canvas(parent, width=12, height=12,
                           bg=bg, highlightthickness=0)
        swatch.create_rectangle(1, 1, 11, 11, fill=color, outline=color)
        swatch.pack(side="left", padx=(8, 2))
        tk.Label(parent, text=label, bg=bg, fg=COLORS["text"],
                 font=FONT_SMALL).pack(side="left", padx=(0, 6))


def _ad_tag(tree: ttk.Treeview):
    tree.tag_configure("reliable",   foreground=COLORS["reliable"])
    tree.tag_configure("unreliable", foreground=COLORS["unreliable"])
    tree.tag_configure("na",         foreground=COLORS["subtext"])


def _row_tags(activity: str, ad: str) -> tuple:
    """Return treeview tags for activity + AD colouring."""
    act_tag = "active" if activity == "Active" else "inactive"
    if ad == "Reliable":
        ad_tag = "reliable"
    elif ad == "Unreliable":
        ad_tag = "unreliable"
    else:
        ad_tag = "na"
    return (act_tag, ad_tag)


# ─────────────────────────────────────────────────────────────────────────────
# AD parameter widget (reused in both tabs)
# ─────────────────────────────────────────────────────────────────────────────

class ADParamFrame(ttk.Frame):
    """A compact widget for Nsimilar + Scutoff with live labels."""

    def __init__(self, parent, bg=COLORS["surface"], **kw):
        super().__init__(parent, style="Surface.TFrame", **kw)
        self._bg = bg
        self._build()

    def _build(self):
        tk.Label(self, text="Applicability Domain", font=FONT_HEAD,
                 bg=self._bg, fg=COLORS["accent2"]).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=0, pady=(4, 6))

        # Scutoff (similarity threshold)
        tk.Label(self, text="Similarity cutoff (Scutoff):", font=FONT_SMALL,
                 bg=self._bg, fg=COLORS["subtext"]).grid(
            row=1, column=0, sticky="w", padx=(0, 6))
        self.scutoff_var = tk.DoubleVar(value=0.25)
        scutoff_scale = ttk.Scale(self, from_=0.0, to=1.0,
                                   variable=self.scutoff_var, orient="horizontal",
                                   length=160,
                                   command=lambda v: self._update_sc_lbl(v))
        scutoff_scale.grid(row=1, column=1, sticky="w", padx=4)
        self._sc_lbl = tk.Label(self, text="0.25", width=5, font=FONT_SMALL,
                                 bg=self._bg, fg=COLORS["text"])
        self._sc_lbl.grid(row=1, column=2, sticky="w")

        # Nsimilar
        tk.Label(self, text="Min. similar neighbours (Nsimilar):", font=FONT_SMALL,
                 bg=self._bg, fg=COLORS["subtext"]).grid(
            row=2, column=0, sticky="w", padx=(0, 6), pady=(4, 0))
        self.nsimilar_var = tk.IntVar(value=1)
        ns_spin = tk.Spinbox(self, from_=1, to=20, textvariable=self.nsimilar_var,
                              width=5, bg=COLORS["entry_bg"], fg=COLORS["text"],
                              buttonbackground=COLORS["surface2"],
                              relief="flat", font=FONT_SMALL,
                              highlightthickness=1,
                              highlightbackground=COLORS["border"],
                              highlightcolor=COLORS["accent"])
        ns_spin.grid(row=2, column=1, sticky="w", padx=4, pady=(4, 0))

        tk.Label(self, text="(compound is Reliable if ≥ Nsimilar training\n"
                            " compounds share similarity ≥ Scutoff)",
                 font=("Helvetica", 8), bg=self._bg,
                 fg=COLORS["subtext"], justify="left").grid(
            row=3, column=0, columnspan=4, sticky="w", pady=(4, 0))

    def _update_sc_lbl(self, v):
        self._sc_lbl.config(text=f"{float(v):.2f}")

    @property
    def Scutoff(self) -> float:
        return round(self.scutoff_var.get(), 3)

    @property
    def Nsimilar(self) -> int:
        return int(self.nsimilar_var.get())


# ─────────────────────────────────────────────────────────────────────────────
# Single prediction tab
# ─────────────────────────────────────────────────────────────────────────────

class SinglePredTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._photo = None
        self._last_results = []
        self._last_met_data = []
        self._build()

    def _build(self):
        # ── left panel ───────────────────────────────────────────────────────
        left = ttk.Frame(self, style="Surface.TFrame")
        left.pack(side="left", fill="y", padx=(10, 4), pady=10,
                  ipadx=10, ipady=10)

        def _lbl(text, fg=COLORS["subtext"]):
            ttk.Label(left, text=text, background=COLORS["surface"],
                      font=FONT_SMALL, foreground=fg).pack(anchor="w", padx=8)

        ttk.Label(left, text="Input", style="Accent.TLabel",
                  background=COLORS["surface"]).pack(anchor="w", padx=8, pady=(6, 2))

        _lbl("SMILES")
        self.smiles_var = tk.StringVar(value="CC(=O)Oc1ccccc1C(=O)O")
        _entry(left, textvariable=self.smiles_var, width=38).pack(
            fill="x", padx=8, pady=(0, 6))

        _lbl("Compound Name")
        self.name_var = tk.StringVar(value="Aspirin")
        _entry(left, textvariable=self.name_var, width=38).pack(
            fill="x", padx=8, pady=(0, 8))

        ttk.Separator(left, orient="horizontal").pack(fill="x", padx=8, pady=4)

        _lbl("Fingerprint")
        self.fp_var = tk.StringVar(value="morgan")
        ttk.Combobox(left, textvariable=self.fp_var,
                     values=FINGERPRINT_TYPES, state="readonly",
                     width=20).pack(anchor="w", padx=8, pady=(0, 6))

        _lbl("Algorithm")
        self.algo_var = tk.StringVar(value="svm")
        ttk.Combobox(left, textvariable=self.algo_var,
                     values=ALGORITHMS, state="readonly",
                     width=20).pack(anchor="w", padx=8, pady=(0, 8))

        ttk.Separator(left, orient="horizontal").pack(fill="x", padx=8, pady=4)

        _lbl("Receptors")
        rec_f = ttk.Frame(left, style="Surface.TFrame")
        rec_f.pack(anchor="w", padx=8, pady=(0, 4))
        self.rec_vars = {}
        for i, rec in enumerate(BINARY_RECEPTORS):
            v = tk.BooleanVar(value=True)
            self.rec_vars[rec] = v
            tk.Checkbutton(rec_f, text=rec, variable=v,
                           bg=COLORS["surface"], fg=COLORS["text"],
                           selectcolor=COLORS["entry_bg"],
                           activebackground=COLORS["surface"],
                           activeforeground=COLORS["accent"],
                           font=FONT_SMALL).grid(
                               row=i // 3, column=i % 3, sticky="w", padx=4, pady=1)

        btn_row = ttk.Frame(left, style="Surface.TFrame")
        btn_row.pack(anchor="w", padx=8, pady=(0, 8))
        for label, fn in (("All", self._select_all), ("None", self._select_none)):
            tk.Button(btn_row, text=label, command=fn,
                      bg=COLORS["surface2"], fg=COLORS["accent"],
                      relief="flat", font=FONT_SMALL, padx=6).pack(side="left", padx=2)

        ttk.Separator(left, orient="horizontal").pack(fill="x", padx=8, pady=4)

        # AD parameters
        self.ad_params = ADParamFrame(left, bg=COLORS["surface"])
        self.ad_params.pack(anchor="w", padx=8, pady=(0, 8))

        ttk.Separator(left, orient="horizontal").pack(fill="x", padx=8, pady=4)

        # ── Metabolite prediction ─────────────────────────────────────────────
        tk.Label(left, text="Metabolite Prediction", font=FONT_HEAD,
                 bg=COLORS["surface"], fg=COLORS["accent2"]).pack(
            anchor="w", padx=8, pady=(4, 2))
        self.met_var = tk.BooleanVar(value=False)
        met_cb = tk.Checkbutton(left, text="Predict Phase I metabolites",
                                variable=self.met_var,
                                bg=COLORS["surface"], fg=COLORS["text"],
                                selectcolor=COLORS["entry_bg"],
                                activebackground=COLORS["surface"],
                                activeforeground=COLORS["accent"],
                                font=FONT_SMALL)
        if not _HAS_SYGMA:
            met_cb.config(state="disabled")
            tk.Label(left, text="(install syGMa to enable)",
                     bg=COLORS["surface"], fg=COLORS["unreliable"],
                     font=("Helvetica", 8)).pack(anchor="w", padx=24)
        met_cb.pack(anchor="w", padx=8)

        met_row = ttk.Frame(left, style="Surface.TFrame")
        met_row.pack(anchor="w", padx=8, pady=(2, 6))
        tk.Label(met_row, text="Max metabolites:", font=FONT_SMALL,
                 bg=COLORS["surface"], fg=COLORS["subtext"]).pack(side="left")
        self.met_max_var = tk.IntVar(value=5)
        tk.Spinbox(met_row, from_=1, to=10, textvariable=self.met_max_var,
                   width=4, bg=COLORS["entry_bg"], fg=COLORS["text"],
                   relief="flat", font=FONT_SMALL,
                   highlightthickness=1,
                   highlightbackground=COLORS["border"],
                   highlightcolor=COLORS["accent"]).pack(side="left", padx=4)
        tk.Label(met_row, text="Steps:", font=FONT_SMALL,
                 bg=COLORS["surface"], fg=COLORS["subtext"]).pack(side="left", padx=(8, 0))
        self.met_steps_var = tk.IntVar(value=1)
        tk.Spinbox(met_row, from_=1, to=3, textvariable=self.met_steps_var,
                   width=4, bg=COLORS["entry_bg"], fg=COLORS["text"],
                   relief="flat", font=FONT_SMALL,
                   highlightthickness=1,
                   highlightbackground=COLORS["border"],
                   highlightcolor=COLORS["accent"]).pack(side="left", padx=4)

        ttk.Separator(left, orient="horizontal").pack(fill="x", padx=8, pady=4)

        self.predict_btn = ttk.Button(left, text="Predict",
                                      command=self._run_prediction)
        self.predict_btn.pack(fill="x", padx=8, pady=6)

        self.status_lbl = ttk.Label(left, text="", style="Sub.TLabel",
                                    background=COLORS["surface"], wraplength=220)
        self.status_lbl.pack(padx=8)

        # ── right panel ──────────────────────────────────────────────────────
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=(4, 10), pady=10)

        # molecule image
        img_f = ttk.Frame(right, style="Surface.TFrame")
        img_f.pack(fill="x", pady=(0, 6), ipady=4)
        ttk.Label(img_f, text="Structure", style="Accent.TLabel",
                  background=COLORS["surface"]).pack(anchor="w", padx=10, pady=(4, 0))
        self.mol_canvas = tk.Canvas(img_f, width=310, height=220,
                                    bg=COLORS["surface"], highlightthickness=0)
        self.mol_canvas.pack(padx=10, pady=4)
        self._draw_placeholder()

        # descriptors
        prop_f = ttk.Frame(right, style="Surface.TFrame")
        prop_f.pack(fill="x", pady=(0, 6), ipady=4)
        ttk.Label(prop_f, text="Molecular Properties", style="Accent.TLabel",
                  background=COLORS["surface"]).pack(anchor="w", padx=10, pady=(4, 0))
        pf, self.prop_tree = _scrolled_tree(prop_f, ("Property", "Value"), heights=5)
        pf.pack(fill="x", padx=10, pady=4)
        for col, w in (("Property", 150), ("Value", 120)):
            self.prop_tree.heading(col, text=col)
            self.prop_tree.column(col, width=w)

        # results  (now includes AD column)
        res_f = ttk.Frame(right, style="Surface.TFrame")
        res_f.pack(fill="both", expand=True, ipady=4)
        ttk.Label(res_f, text="Prediction Results", style="Accent.TLabel",
                  background=COLORS["surface"]).pack(anchor="w", padx=10, pady=(4, 0))

        # AD legend
        legend = ttk.Frame(res_f, style="Surface.TFrame")
        legend.pack(anchor="w", padx=10)
        _color_legend(legend, [
            ("Reliable",   COLORS["reliable"]),
            ("Unreliable", COLORS["unreliable"]),
            ("Active",     COLORS["active"]),
            ("Inactive",   COLORS["inactive"]),
        ], bg=COLORS["surface"])

        cols = ("Source", "Receptor", "Activity", "Active %", "Inactive %", "AD")
        rf, self.res_tree = _scrolled_tree(res_f, cols, heights=10)
        rf.pack(fill="both", expand=True, padx=10, pady=4)
        for col, w, anc in (("Source", 110, "w"), ("Receptor", 80, "center"),
                             ("Activity", 90, "center"), ("Active %", 80, "center"),
                             ("Inactive %", 90, "center"), ("AD", 90, "center")):
            self.res_tree.heading(col, text=col)
            self.res_tree.column(col, width=w, anchor=anc)

        self.res_tree.tag_configure("active",     foreground=COLORS["active"])
        self.res_tree.tag_configure("inactive",   foreground=COLORS["inactive"])
        self.res_tree.tag_configure("reliable",   foreground=COLORS["reliable"])
        self.res_tree.tag_configure("unreliable", foreground=COLORS["unreliable"])
        self.res_tree.tag_configure("na",         foreground=COLORS["subtext"])
        self.res_tree.tag_configure("met_sep",    foreground=COLORS["subtext"],
                                    background=COLORS["surface2"])
        self.res_tree.tag_configure("metabolite", foreground=COLORS["text"])

        ttk.Button(right, text="Export Results to CSV",
                   command=self._export_csv,
                   style="Secondary.TButton").pack(anchor="e", padx=10, pady=4)

    # ── helpers ──────────────────────────────────────────────────────────────
    def _draw_placeholder(self):
        self.mol_canvas.delete("all")
        self.mol_canvas.create_text(155, 110,
                                    text="Structure will appear here",
                                    fill=COLORS["subtext"], font=FONT_SMALL)

    def _select_all(self):
        for v in self.rec_vars.values():
            v.set(True)

    def _select_none(self):
        for v in self.rec_vars.values():
            v.set(False)

    def _run_prediction(self):
        if not IMPORTS_OK:
            messagebox.showerror("Import Error", IMPORT_ERROR)
            return
        smiles = self.smiles_var.get().strip()
        name   = self.name_var.get().strip() or "Compound"
        fp     = self.fp_var.get()
        algo   = self.algo_var.get()
        recs   = [r for r, v in self.rec_vars.items() if v.get()]
        if not smiles:
            messagebox.showwarning("Missing Input", "Please enter a SMILES string.")
            return
        if not recs:
            messagebox.showwarning("No Receptors", "Select at least one receptor.")
            return
        # Check that at least one model file exists for this algorithm
        probe = _model_path(fp, BINARY_RECEPTORS[0], algo)
        if not os.path.exists(probe):
            messagebox.showerror(
                "Models Not Found",
                f"No {algo.upper()} models found for '{fp}' fingerprint.\n\n"
                + ("SuperLearner models (~12 GB) were not downloaded.\n"
                   "Switch the Algorithm to SVM, or restart the app and\n"
                   "choose 'Download All' to get the SuperLearner models."
                   if algo == "superlearner" else
                   "Restart the app and download the models when prompted."))
            return
        Nsimilar    = self.ad_params.Nsimilar
        Scutoff     = self.ad_params.Scutoff
        include_mets = self.met_var.get() and _HAS_SYGMA
        met_steps   = self.met_steps_var.get()
        met_max     = self.met_max_var.get()
        self.predict_btn.config(state="disabled")
        self.status_lbl.config(text="Running prediction…")
        threading.Thread(target=self._thread_predict,
                         args=(smiles, name, fp, algo, recs, Nsimilar, Scutoff,
                               include_mets, met_steps, met_max),
                         daemon=True).start()

    def _thread_predict(self, smiles, name, fp, algo, recs, Nsimilar, Scutoff,
                        include_mets, met_steps, met_max):
        try:
            desc, results = predict_single(smiles, name, fp, algo, recs,
                                           Nsimilar, Scutoff)
            pil_img = mol_to_pil(smiles)

            met_data = []  # list of (label, smiles, prob, results_list)
            if include_mets:
                _ui_queue.put(lambda: self.status_lbl.config(
                    text="Generating metabolites…"))
                mets = generate_metabolites(smiles, n_steps=met_steps,
                                            max_mets=met_max)
                for i, (met_smi, prob) in enumerate(mets, start=1):
                    _ui_queue.put(lambda i=i, n=len(mets): self.status_lbl.config(
                        text=f"Predicting metabolite {i}/{n}…"))
                    try:
                        _, met_results = predict_single(
                            met_smi, f"Met.{i}", fp, algo, recs, Nsimilar, Scutoff)
                        met_data.append((f"Met.{i} ({prob:.0%})", met_smi,
                                         prob, met_results))
                    except Exception:
                        pass

            _ui_queue.put(lambda d=desc, r=results, img=pil_img, m=met_data:
                          self._show_results(d, r, pil_to_photo(img), m))
        except Exception as e:
            msg = str(e)
            _ui_queue.put(lambda m=msg: self._show_error(m))

    def _show_results(self, desc, results, photo, met_data=None):
        # molecule image
        self.mol_canvas.delete("all")
        if photo:
            self._photo = photo
            self.mol_canvas.create_image(155, 110, image=self._photo)
        else:
            self.mol_canvas.create_text(155, 110,
                                        text="Could not render structure",
                                        fill=COLORS["inactive"], font=FONT_SMALL)

        # properties
        for row in self.prop_tree.get_children():
            self.prop_tree.delete(row)
        for k, v in desc.items():
            self.prop_tree.insert("", "end", values=(k, v))

        # results + metabolites
        for row in self.res_tree.get_children():
            self.res_tree.delete(row)

        # parent rows
        for r in results:
            tags = _row_tags(r["Activity"], r["AD"])
            self.res_tree.insert("", "end",
                                 values=("Parent", r["Receptor"], r["Activity"],
                                         r["Active%"], r["Inactive%"], r["AD"]),
                                 tags=tags)

        # metabolite rows
        if met_data:
            for label, met_smi, prob, met_results in met_data:
                # separator row
                self.res_tree.insert("", "end",
                                     values=(f"── {label} ──", "", "", "", "", ""),
                                     tags=("met_sep",))
                for r in met_results:
                    tags = _row_tags(r["Activity"], r["AD"]) + ("metabolite",)
                    self.res_tree.insert("", "end",
                                         values=(label, r["Receptor"], r["Activity"],
                                                 r["Active%"], r["Inactive%"], r["AD"]),
                                         tags=tags)

        self._last_results = results
        self._last_met_data = met_data or []
        self.predict_btn.config(state="normal")
        n_active   = sum(1 for r in results if r["Activity"] == "Active")
        n_reliable = sum(1 for r in results if r["AD"] == "Reliable")
        met_txt    = f"  │  Metabolites: {len(met_data)}" if met_data else ""
        self.status_lbl.config(
            text=f"Done.  Active: {n_active}/{len(results)}  "
                 f"│  AD Reliable: {n_reliable}/{len(results)}{met_txt}")

    def _show_error(self, msg):
        self.predict_btn.config(state="normal")
        self.status_lbl.config(text=f"Error: {msg}")
        messagebox.showerror("Prediction Error", msg)

    def _export_csv(self):
        if not self._last_results:
            messagebox.showinfo("No Results", "Run a prediction first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("All", "*.*")],
            initialfile="nrtoxpred_single_results.csv")
        if not path:
            return
        rows = [{"Source": "Parent", **r} for r in self._last_results]
        for label, met_smi, prob, met_results in self._last_met_data:
            for r in met_results:
                rows.append({"Source": label, "SMILES": met_smi,
                             "Probability": round(prob, 4), **r})
        pd.DataFrame(rows).to_csv(path, index=False)
        messagebox.showinfo("Saved", f"Results saved to:\n{path}")


# ─────────────────────────────────────────────────────────────────────────────
# Batch prediction tab
# ─────────────────────────────────────────────────────────────────────────────

class BatchPredTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._results_by_rec = {}
        self._build()

    def _build(self):
        # ── controls ─────────────────────────────────────────────────────────
        ctrl = ttk.Frame(self, style="Surface.TFrame")
        ctrl.pack(fill="x", padx=10, pady=(10, 4), ipadx=10, ipady=10)

        ttk.Label(ctrl, text="Batch Prediction", style="Accent.TLabel",
                  background=COLORS["surface"]).grid(
            row=0, column=0, columnspan=6, sticky="w", padx=8, pady=(4, 6))

        # CSV
        ttk.Label(ctrl, text="CSV File:", background=COLORS["surface"],
                  font=FONT_SMALL).grid(row=1, column=0, sticky="w", padx=8)
        self.csv_var = tk.StringVar()
        _entry(ctrl, textvariable=self.csv_var, width=48).grid(
            row=1, column=1, columnspan=3, sticky="ew", padx=4, pady=3)
        ttk.Button(ctrl, text="Browse…", command=self._browse_csv,
                   style="Secondary.TButton").grid(row=1, column=4, padx=4)

        # Fingerprint / Algorithm
        ttk.Label(ctrl, text="Fingerprint:", background=COLORS["surface"],
                  font=FONT_SMALL).grid(row=2, column=0, sticky="w", padx=8, pady=3)
        self.fp_var = tk.StringVar(value="morgan")
        ttk.Combobox(ctrl, textvariable=self.fp_var,
                     values=FINGERPRINT_TYPES, state="readonly",
                     width=14).grid(row=2, column=1, sticky="w", padx=4)

        ttk.Label(ctrl, text="Algorithm:", background=COLORS["surface"],
                  font=FONT_SMALL).grid(row=2, column=2, sticky="w", padx=8)
        self.algo_var = tk.StringVar(value="svm")
        ttk.Combobox(ctrl, textvariable=self.algo_var,
                     values=ALGORITHMS, state="readonly",
                     width=16).grid(row=2, column=3, sticky="w", padx=4)

        ctrl.columnconfigure(1, weight=1)

        # Receptors
        ttk.Label(ctrl, text="Receptors:", background=COLORS["surface"],
                  font=FONT_SMALL).grid(row=3, column=0, sticky="nw", padx=8, pady=(6, 2))
        rec_f = ttk.Frame(ctrl, style="Surface.TFrame")
        rec_f.grid(row=3, column=1, columnspan=4, sticky="w", padx=4)
        self.rec_vars = {}
        for i, rec in enumerate(BINARY_RECEPTORS):
            v = tk.BooleanVar(value=True)
            self.rec_vars[rec] = v
            tk.Checkbutton(rec_f, text=rec, variable=v,
                           bg=COLORS["surface"], fg=COLORS["text"],
                           selectcolor=COLORS["entry_bg"],
                           activebackground=COLORS["surface"],
                           font=FONT_SMALL).grid(row=0, column=i, sticky="w", padx=4)

        # AD parameters inline
        ad_f = ttk.Frame(ctrl, style="Surface.TFrame")
        ad_f.grid(row=4, column=0, columnspan=6, sticky="w", padx=8, pady=(6, 4))
        self.ad_params = ADParamFrame(ad_f, bg=COLORS["surface"])
        self.ad_params.pack(anchor="w")

        # Run / progress
        run_row = ttk.Frame(ctrl, style="Surface.TFrame")
        run_row.grid(row=5, column=0, columnspan=6, sticky="ew", padx=8, pady=8)
        self.run_btn = ttk.Button(run_row, text="Run Batch Prediction",
                                  command=self._run_batch)
        self.run_btn.pack(side="left")
        self.prog = ttk.Progressbar(run_row, length=280, mode="determinate")
        self.prog.pack(side="left", padx=16)
        self.prog_lbl = ttk.Label(run_row, text="", style="Sub.TLabel",
                                  background=COLORS["surface"])
        self.prog_lbl.pack(side="left")

        # ── per-receptor result tabs ──────────────────────────────────────────
        self.rec_nb = ttk.Notebook(self)
        self.rec_nb.pack(fill="both", expand=True, padx=10, pady=(0, 4))

        self._rec_trees = {}
        for rec in BINARY_RECEPTORS:
            f = ttk.Frame(self.rec_nb)
            self.rec_nb.add(f, text=rec)

            # AD legend
            legend = ttk.Frame(f)
            legend.pack(anchor="w", padx=6, pady=(4, 0))
            _color_legend(legend, [
                ("Reliable",   COLORS["reliable"]),
                ("Unreliable", COLORS["unreliable"]),
                ("Active",     COLORS["active"]),
                ("Inactive",   COLORS["inactive"]),
            ], bg=COLORS["bg"])

            cols = ("NAME", "SMILES", "Active %", "Inactive %", "Activity", "AD")
            tf, tree = _scrolled_tree(f, cols, heights=13)
            tf.pack(fill="both", expand=True, padx=6, pady=4)
            for col, w in zip(cols, [120, 280, 80, 85, 90, 90]):
                tree.heading(col, text=col)
                tree.column(col, width=w)
            tree.tag_configure("active",     foreground=COLORS["active"])
            tree.tag_configure("inactive",   foreground=COLORS["inactive"])
            tree.tag_configure("reliable",   foreground=COLORS["reliable"])
            tree.tag_configure("unreliable", foreground=COLORS["unreliable"])
            tree.tag_configure("na",         foreground=COLORS["subtext"])
            self._rec_trees[rec] = tree

        # Export buttons
        exp_row = ttk.Frame(self)
        exp_row.pack(fill="x", padx=10, pady=(0, 8))
        ttk.Button(exp_row, text="Export All Results to Excel",
                   command=self._export_excel).pack(side="right")
        ttk.Button(exp_row, text="Export Current Tab to CSV",
                   command=self._export_current_csv,
                   style="Secondary.TButton").pack(side="right", padx=6)

    # ── helpers ──────────────────────────────────────────────────────────────
    def _browse_csv(self):
        path = filedialog.askopenfilename(
            filetypes=[("CSV files", "*.csv"), ("All", "*.*")])
        if path:
            self.csv_var.set(path)

    def _run_batch(self):
        if not IMPORTS_OK:
            messagebox.showerror("Import Error", IMPORT_ERROR)
            return
        csv_path = self.csv_var.get().strip()
        if not csv_path or not os.path.exists(csv_path):
            messagebox.showwarning("No File", "Select a valid CSV file.")
            return
        recs = [r for r, v in self.rec_vars.items() if v.get()]
        if not recs:
            messagebox.showwarning("No Receptors", "Select at least one receptor.")
            return
        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            messagebox.showerror("CSV Error", str(e))
            return

        Nsimilar = self.ad_params.Nsimilar
        Scutoff  = self.ad_params.Scutoff

        self.run_btn.config(state="disabled")
        self.prog["value"]   = 0
        self.prog["maximum"] = len(recs)
        self._results_by_rec = {}
        for tree in self._rec_trees.values():
            for row in tree.get_children():
                tree.delete(row)

        def progress(idx, total, rec_name):
            _ui_queue.put(lambda i=idx, t=total, r=rec_name: self._update_progress(i, t, r))

        threading.Thread(
            target=self._thread_batch,
            args=(df, self.fp_var.get(), self.algo_var.get(),
                  recs, Nsimilar, Scutoff, progress),
            daemon=True).start()

    def _thread_batch(self, df, fp, algo, recs, Nsimilar, Scutoff, progress_cb):
        try:
            results = predict_batch(df, fp, algo, recs, Nsimilar, Scutoff, progress_cb)
            _ui_queue.put(lambda r=results: self._show_batch_results(r))
        except Exception as e:
            msg = str(e)
            _ui_queue.put(lambda m=msg: self._batch_error(m))

    def _update_progress(self, idx, total, rec_name):
        self.prog["value"] = idx
        self.prog_lbl.config(text=f"{rec_name}  ({idx}/{total})")

    def _show_batch_results(self, results):
        self._results_by_rec = results
        for rec, df in results.items():
            tree = self._rec_trees.get(rec)
            if tree is None:
                continue
            for row in tree.get_children():
                tree.delete(row)
            for _, r in df.iterrows():
                tags = _row_tags(r["Activity"], r["AD"])
                tree.insert("", "end",
                            values=(r["NAME"], r["SMILES"],
                                    r["Active%"], r["Inactive%"],
                                    r["Activity"], r["AD"]),
                            tags=tags)
        self.run_btn.config(state="normal")
        self.prog["value"] = self.prog["maximum"]
        self.prog_lbl.config(text="Done")

    def _batch_error(self, msg):
        self.run_btn.config(state="normal")
        self.prog_lbl.config(text="Error")
        messagebox.showerror("Batch Error", msg)

    def _export_excel(self):
        if not self._results_by_rec:
            messagebox.showinfo("No Results", "Run a batch prediction first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx"), ("All", "*.*")],
            initialfile="nrtoxpred_batch_results.xlsx")
        if not path:
            return
        try:
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                for rec, df in self._results_by_rec.items():
                    df.to_excel(writer, sheet_name=rec, index=False)
            messagebox.showinfo("Saved", f"Results saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    def _export_current_csv(self):
        if not self._results_by_rec:
            messagebox.showinfo("No Results", "Run a batch prediction first.")
            return
        tab_idx = self.rec_nb.index(self.rec_nb.select())
        rec     = BINARY_RECEPTORS[tab_idx]
        df      = self._results_by_rec.get(rec)
        if df is None:
            messagebox.showinfo("No Data", f"No results for {rec}.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("All", "*.*")],
            initialfile=f"nrtoxpred_{rec}_results.csv")
        if not path:
            return
        df.to_csv(path, index=False)
        messagebox.showinfo("Saved", f"{rec} results saved to:\n{path}")


# ─────────────────────────────────────────────────────────────────────────────
# About tab
# ─────────────────────────────────────────────────────────────────────────────

class AboutTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._build()

    def _build(self):
        frame = ttk.Frame(self, style="Surface.TFrame")
        frame.place(relx=0.5, rely=0.5, anchor="center", width=660)

        tk.Label(frame, text="NR-ToxPred", font=("Helvetica", 22, "bold"),
                 bg=COLORS["surface"], fg=COLORS["accent"]).pack(pady=(20, 4))
        tk.Label(frame, text="Nuclear Receptor Toxicity Predictor",
                 font=("Helvetica", 13), bg=COLORS["surface"],
                 fg=COLORS["subtext"]).pack()

        ttk.Separator(frame, orient="horizontal").pack(fill="x", padx=30, pady=14)

        body = (
            "Predicts agonist / antagonist / binder activity of small molecules\n"
            "against 9 nuclear receptors using pre-trained SVM / SuperLearner models.\n\n"
            "Receptors:   AR · PR · GR · RXR · FXR · ERα · ERβ · PPARδ · PPARγ\n\n"
            "Fingerprints: Morgan ECFP6 (1024 bits)  ·  MACCS Keys (167 bits)\n\n"
            "Applicability Domain (AD)\n"
            "  Fingerprint-similarity based (Tanimoto).  A compound is labelled\n"
            "  Reliable when ≥ Nsimilar training compounds share similarity ≥ Scutoff.\n"
            "  X_train data: X_train/<receptor>.xlsx  (sheet: X_train, col: SMILES)\n\n"
            "CSV format for batch prediction:\n"
            "  Required columns:  SMILES  and  NAME  (case-insensitive).\n\n"
            "Contact:  eazhagiy@berkeley.edu"
        )
        tk.Label(frame, text=body, font=FONT_BODY,
                 bg=COLORS["surface"], fg=COLORS["text"],
                 justify="left", wraplength=600).pack(padx=30, pady=4)

        ttk.Separator(frame, orient="horizontal").pack(fill="x", padx=30, pady=14)
        tk.Label(frame, text="Working directory: " + SCRIPT_DIR,
                 font=FONT_SMALL, bg=COLORS["surface"],
                 fg=COLORS["subtext"]).pack(pady=(0, 20))


# ─────────────────────────────────────────────────────────────────────────────
# Model download dialog
# ─────────────────────────────────────────────────────────────────────────────

class DownloadDialog(tk.Toplevel):
    """Shown when models are missing — offers to download from Hugging Face."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Models Not Found")
        self.resizable(False, False)
        self.grab_set()
        self._cancelled = False
        self._build()
        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def _build(self):
        pad = {"padx": 20, "pady": 8}

        tk.Label(self, text="Models not found locally",
                 font=FONT_HEAD).pack(**pad)

        msg = (
            "The prediction models were not found on this computer.\n"
            "Choose which models to download from Hugging Face:\n\n"
            "  • SVM only  (~250 MB, fast download, recommended)\n"
            "  • SVM + SuperLearner  (~12 GB, slower but more accurate)\n\n"
            f"Models will be saved to:\n  {_DEFAULT_MODELS_BASE}\n\n"
            "Or close this dialog if you will copy the files manually."
        )
        tk.Label(self, text=msg, justify="left",
                 wraplength=440).pack(**pad)

        self.prog = ttk.Progressbar(self, length=440, mode="determinate")
        self.prog.pack(padx=20, pady=4)

        self.status = tk.Label(self, text="", font=FONT_SMALL,
                               fg=COLORS["subtext"], wraplength=440)
        self.status.pack(**pad)

        btn_row = tk.Frame(self)
        btn_row.pack(pady=(0, 16))
        self.dl_svm_btn = ttk.Button(btn_row, text="Download SVM only  (~250 MB)",
                                     command=self._start_svm)
        self.dl_svm_btn.pack(side="left", padx=6)
        self.dl_all_btn = ttk.Button(btn_row, text="Download All  (~12 GB)",
                                     command=self._start_all)
        self.dl_all_btn.pack(side="left", padx=6)
        ttk.Button(btn_row, text="Skip",
                   command=self._cancel,
                   style="Secondary.TButton").pack(side="left", padx=6)

    def _start_svm(self):
        self._start_download(svm_only=True)

    def _start_all(self):
        self._start_download(svm_only=False)

    def _start_download(self, svm_only=True):
        if not HF_REPO:
            messagebox.showerror(
                "HF_REPO not set",
                "Open pytox_gui.py and set the HF_REPO variable to your\n"
                "Hugging Face repository ID, e.g.:\n\n"
                "  HF_REPO = 'YourName/nrtoxpred-models'",
                parent=self)
            return
        self.dl_svm_btn.config(state="disabled")
        self.dl_all_btn.config(state="disabled")
        threading.Thread(target=self._download_thread,
                         args=(svm_only,), daemon=True).start()

    def _download_thread(self, svm_only):
        try:
            def cb(fname, cur, total):
                short = os.path.basename(fname)
                _ui_queue.put(lambda m=short, c=cur, t=total: self._update(m, c, t))
            download_models_from_hf(progress_cb=cb, svm_only=svm_only)
            _ui_queue.put(self._done)
        except Exception as e:
            msg = str(e)
            _ui_queue.put(lambda m=msg: self._error(m))

    def _update(self, msg, cur, total):
        if total > 0 and cur > 0:
            self.prog.config(mode="determinate", maximum=total, value=cur)
        else:
            self.prog.config(mode="indeterminate")
            self.prog.start(12)
        self.status.config(text=msg)

    def _done(self):
        self.prog.stop()
        self.prog.config(mode="determinate", value=self.prog["maximum"])
        self.status.config(text="Download complete!")
        self.after(1200, self.destroy)

    def _error(self, msg):
        self.dl_svm_btn.config(state="normal")
        self.dl_all_btn.config(state="normal")
        self.status.config(text=f"Error: {msg}", fg=COLORS["inactive"])
        messagebox.showerror("Download Failed", msg, parent=self)

    def _cancel(self):
        self._cancelled = True
        self.destroy()


# ─────────────────────────────────────────────────────────────────────────────
# Command-line interface
# ─────────────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python pytox_gui.py",
        description="NR-ToxPred: Nuclear Receptor Toxicity Predictor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  # single compound\n"
            "  python pytox_gui.py --no-gui --smiles \"CC(=O)Oc1ccccc1C(=O)O\" --name Aspirin\n\n"
            "  # save to file\n"
            "  python pytox_gui.py --no-gui --smiles \"CC(=O)...\" --output results.csv\n\n"
            "  # batch from CSV\n"
            "  python pytox_gui.py --no-gui --csv compounds.csv --smiles-col SMILES --output results.xlsx\n\n"
            "  # specific receptors only\n"
            "  python pytox_gui.py --no-gui --smiles \"...\" --receptors AR ERA ERB\n"
        ),
    )
    p.add_argument("--no-gui", action="store_true",
                   help="run in command-line mode (no window)")
    p.add_argument("--smiles", metavar="SMILES",
                   help="SMILES string for single-compound prediction")
    p.add_argument("--name", default="Compound",
                   help="compound name label (default: Compound)")
    p.add_argument("--csv", metavar="FILE",
                   help="CSV or Excel file for batch prediction")
    p.add_argument("--smiles-col", default="SMILES", metavar="COL",
                   help="column name containing SMILES in the CSV (default: SMILES)")
    p.add_argument("--fp", choices=["morgan", "maccs"], default="morgan",
                   help="fingerprint type (default: morgan)")
    p.add_argument("--algo", choices=["svm", "superlearner"], default="svm",
                   help="algorithm (default: svm)")
    p.add_argument("--receptors", nargs="+", metavar="R", default=None,
                   help="receptors to predict; default is all nine. "
                        "choices: AR ERA ERB FXR GR PPARD PPARG PR RXR")
    p.add_argument("--scutoff", type=float, default=0.25,
                   help="AD Tanimoto similarity cutoff 0–1 (default: 0.25)")
    p.add_argument("--nsimilar", type=int, default=1,
                   help="AD minimum similar neighbours (default: 1)")
    p.add_argument("--output", metavar="FILE",
                   help="output file (.csv or .xlsx); prints table to stdout if omitted")
    return p


def _cli_single(args, receptors: list):
    """CLI: predict one compound and print / save results."""
    print(f"Predicting: {args.name}  [{args.fp} / {args.algo}]")
    try:
        desc, results = predict_single(
            args.smiles, args.name, args.fp, args.algo,
            receptors, args.nsimilar, args.scutoff)
    except Exception as e:
        sys.exit(f"Prediction failed: {e}")

    # ── descriptors ───────────────────────────────────────────────────────────
    print(f"\nCompound : {args.name}")
    print(f"SMILES   : {args.smiles}\n")
    print("Molecular Descriptors:")
    for k, v in desc.items():
        print(f"  {k:<14}: {v}")

    # ── results table ─────────────────────────────────────────────────────────
    print("\nPrediction Results:")
    hdr = f"  {'Receptor':<10} {'Activity':<12} {'Active%':>8} {'Inactive%':>10}  {'AD'}"
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for r in results:
        print(f"  {r['Receptor']:<10} {r['Activity']:<12} "
              f"{str(r['Active%']):>8} {str(r['Inactive%']):>10}  {r['AD']}")

    # ── optional file output ───────────────────────────────────────────────────
    if args.output:
        rows = [{**{"Name": args.name, "SMILES": args.smiles}, **r} for r in results]
        df = pd.DataFrame(rows)
        _cli_save(df, args.output)
        print(f"\nSaved to: {args.output}")


def _cli_batch(args, receptors: list):
    """CLI: run batch prediction from a CSV/Excel file."""
    # ── load input ─────────────────────────────────────────────────────────────
    try:
        if args.csv.lower().endswith((".xlsx", ".xls")):
            df_in = pd.read_excel(args.csv)
        else:
            df_in = pd.read_csv(args.csv)
    except Exception as e:
        sys.exit(f"Could not read '{args.csv}': {e}")

    if args.smiles_col not in df_in.columns:
        sys.exit(
            f"Column '{args.smiles_col}' not found in file.\n"
            f"Available columns: {list(df_in.columns)}\n"
            f"Use --smiles-col to specify the correct column name.")

    df_in = df_in.rename(columns={args.smiles_col: "SMILES"})
    print(f"Batch predicting {len(df_in)} compounds  [{args.fp} / {args.algo}]")

    def _progress(idx, total, rec_name):
        bar = "#" * int(20 * idx / max(total, 1))
        print(f"\r  [{bar:<20}] {idx}/{total}  {rec_name:<12}", end="", flush=True)

    try:
        results_by_rec = predict_batch(
            df_in, args.fp, args.algo, receptors,
            args.nsimilar, args.scutoff, _progress)
    except Exception as e:
        print()
        sys.exit(f"Batch prediction failed: {e}")
    print()  # newline after progress bar

    # ── save / print ──────────────────────────────────────────────────────────
    if args.output:
        if args.output.lower().endswith(".xlsx"):
            with pd.ExcelWriter(args.output, engine="openpyxl") as writer:
                for rec, rdf in results_by_rec.items():
                    rdf.to_excel(writer, sheet_name=rec, index=False)
        else:
            combined = pd.concat(
                [rdf.assign(Receptor=rec) for rec, rdf in results_by_rec.items()],
                ignore_index=True)
            combined = combined[["Receptor"] + [c for c in combined.columns
                                                if c != "Receptor"]]
            combined.to_csv(args.output, index=False)
        print(f"Saved to: {args.output}")
    else:
        for rec, rdf in results_by_rec.items():
            print(f"\n── {rec} ──")
            print(rdf.to_string(index=False))


def _cli_save(df: "pd.DataFrame", path: str):
    if path.lower().endswith(".xlsx"):
        df.to_excel(path, index=False, engine="openpyxl")
    else:
        df.to_csv(path, index=False)


def _cli_main(args):
    """Dispatch CLI prediction after validating args and environment."""
    if not IMPORTS_OK:
        sys.exit(
            f"Missing dependencies: {IMPORT_ERROR}\n"
            "Activate the conda environment first:\n"
            "  conda activate nrtoxpred")

    if not _models_present():
        sys.exit(
            f"Model files not found in: {_DEFAULT_MODELS_BASE}\n"
            "Run the GUI to download them:\n"
            "  python pytox_gui.py")

    if args.smiles and args.csv:
        sys.exit("Specify either --smiles or --csv, not both.")
    if not args.smiles and not args.csv:
        sys.exit("Specify --smiles SMILES or --csv FILE.\n"
                 "Run with --help to see all options.")

    # Normalise + validate receptor list
    receptors = [r.upper() for r in (args.receptors or BINARY_RECEPTORS)]
    invalid = [r for r in receptors if r not in BINARY_RECEPTORS]
    if invalid:
        sys.exit(f"Unknown receptors: {invalid}\n"
                 f"Valid choices: {' '.join(BINARY_RECEPTORS)}")

    # Check model exists for chosen algorithm
    probe = _model_path(args.fp, receptors[0], args.algo)
    if not os.path.exists(probe):
        sys.exit(
            f"No {args.algo.upper()} models found for '{args.fp}' fingerprint.\n" +
            ("SuperLearner models (~12 GB) were not downloaded.\n"
             "Switch --algo svm, or run the GUI and choose 'Download All'."
             if args.algo == "superlearner" else
             "Run the GUI to download models: python pytox_gui.py"))

    if args.smiles:
        _cli_single(args, receptors)
    else:
        _cli_batch(args, receptors)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = _build_parser()
    args   = parser.parse_args()

    if args.no_gui:
        _cli_main(args)
        return

    # ── GUI mode ──────────────────────────────────────────────────────────────
    if not _HAS_TK:
        sys.exit("tkinter is not available on this system.\n"
                 "Use --no-gui for command-line mode.")

    if not IMPORTS_OK:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Missing Dependencies",
            f"Failed to import required libraries:\n\n{IMPORT_ERROR}\n\n"
            "Activate the conda environment and retry:\n"
            "  conda activate <env_name>\n  python pytox_gui.py")
        sys.exit(1)

    root = NRToxPredApp()

    # Show download dialog if models are missing
    if not _models_present():
        dlg = DownloadDialog(root)
        root.wait_window(dlg)

    root.mainloop()


if __name__ == "__main__":
    main()
