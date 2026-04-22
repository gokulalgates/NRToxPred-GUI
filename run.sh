#!/bin/bash
# NR-ToxPred — Launcher (Linux / macOS)

echo ""
echo " ============================================="
echo "   NR-ToxPred  |  Starting..."
echo " ============================================="
echo ""

# ── Check conda ───────────────────────────────────────────────────────────────
if ! command -v conda &>/dev/null; then
    echo " [ERROR] Conda not found."
    echo " Please run install.sh first."
    echo ""
    exit 1
fi

# ── Check environment exists ──────────────────────────────────────────────────
if ! conda env list | grep -q "nrtoxpred"; then
    echo " [ERROR] The nrtoxpred environment is not installed."
    echo " Please run install.sh first."
    echo ""
    exit 1
fi

# ── Launch app ────────────────────────────────────────────────────────────────
echo " Launching NR-ToxPred GUI..."
echo " (A setup window may appear on first launch to download models)"
echo ""

conda run -n nrtoxpred python pytox_gui.py

if [ $? -ne 0 ]; then
    echo ""
    echo " [ERROR] The application crashed or failed to start."
    echo " Make sure install.sh completed successfully."
    echo ""
fi
