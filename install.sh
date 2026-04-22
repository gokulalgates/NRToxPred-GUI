#!/bin/bash
# NR-ToxPred — One-Time Installer (Linux / macOS)

echo ""
echo " ============================================="
echo "   NR-ToxPred  |  One-Time Installation"
echo " ============================================="
echo ""

# ── Check conda ───────────────────────────────────────────────────────────────
if ! command -v conda &>/dev/null; then
    echo " [ERROR] Conda (Miniconda) is not installed."
    echo ""
    echo " Please download and install Miniconda first:"
    echo "   https://docs.conda.io/en/latest/miniconda.html"
    echo ""
    echo " After installing, open a NEW terminal and run:"
    echo "   bash install.sh"
    echo ""
    exit 1
fi

echo " [OK] Conda found: $(conda --version)"
echo ""

# ── Create or update environment ──────────────────────────────────────────────
echo " [1/2] Setting up Python environment..."
echo "       (This can take 5-15 minutes on the first run)"
echo ""

if conda env create -f environment_setup.yml 2>/dev/null; then
    echo " Environment created successfully."
else
    echo " Environment already exists — updating instead..."
    conda env update -f environment_setup.yml --prune
fi

if [ $? -ne 0 ]; then
    echo ""
    echo " [ERROR] Environment setup failed."
    echo " Please check the error above or contact support."
    exit 1
fi

# ── Make run.sh executable ────────────────────────────────────────────────────
chmod +x run.sh

echo ""
echo " [2/2] Installation complete!"
echo ""
echo " ============================================="
echo "   Launch NR-ToxPred by running:  bash run.sh"
echo " ============================================="
echo ""
