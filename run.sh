#!/bin/bash
# NR-ToxPred — Launcher (Linux / macOS)

# Change to the folder where this script lives
cd "$(dirname "$0")"

echo ""
echo " ============================================="
echo "   NR-ToxPred  |  Starting..."
echo " ============================================="
echo ""

# ── Find conda ────────────────────────────────────────────────────────────────
CONDA_EXE=""

if command -v conda &>/dev/null; then
    CONDA_EXE="conda"
elif [ -f ".conda_path.txt" ]; then
    CONDA_EXE=$(cat .conda_path.txt)
else
    for P in \
        "$HOME/miniconda3/bin/conda" \
        "$HOME/Miniconda3/bin/conda" \
        "$HOME/anaconda3/bin/conda" \
        "/opt/miniconda3/bin/conda"
    do
        if [ -x "$P" ]; then CONDA_EXE="$P"; break; fi
    done
fi

if [ -z "$CONDA_EXE" ] || [ ! -x "$CONDA_EXE" ] && ! command -v "$CONDA_EXE" &>/dev/null; then
    echo " [ERROR] Conda not found."
    echo " Please run install.sh first."
    echo ""
    exit 1
fi

# ── Check the nrtoxpred environment exists ────────────────────────────────────
if ! "$CONDA_EXE" env list | grep -q "nrtoxpred"; then
    echo " [ERROR] NR-ToxPred environment not found."
    echo " Please run install.sh first."
    echo ""
    exit 1
fi

# ── Launch the application ────────────────────────────────────────────────────
echo " Launching NR-ToxPred GUI..."
echo " (A download window may appear on first launch to fetch the models)"
echo ""

"$CONDA_EXE" run -n nrtoxpred python pytox_gui.py

if [ $? -ne 0 ]; then
    echo ""
    echo " [ERROR] The application failed to start."
    echo " Try running install.sh again to repair the installation."
    echo ""
fi
