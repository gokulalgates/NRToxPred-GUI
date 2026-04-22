#!/bin/bash
# NR-ToxPred — One-Time Installer (Linux / macOS)
set -e

# Change to the folder where this script lives
cd "$(dirname "$0")"

echo ""
echo " ============================================="
echo "   NR-ToxPred  |  One-Time Installation"
echo " ============================================="
echo ""

MINICONDA_DIR="$HOME/miniconda3"

# ── Find conda (PATH or default install location) ────────────────────────────
find_conda() {
    if command -v conda &>/dev/null; then
        echo "conda"
        return
    fi
    for P in \
        "$HOME/miniconda3/bin/conda" \
        "$HOME/Miniconda3/bin/conda" \
        "$HOME/anaconda3/bin/conda" \
        "/opt/miniconda3/bin/conda" \
        "/opt/anaconda3/bin/conda"
    do
        if [ -x "$P" ]; then
            echo "$P"
            return
        fi
    done
    echo ""
}

CONDA_EXE=$(find_conda)

if [ -n "$CONDA_EXE" ]; then
    echo " [OK] Conda already installed: $CONDA_EXE"
else
    # ── Download and silently install Miniconda ───────────────────────────────
    echo " Miniconda not found. Downloading it now..."
    echo " (Miniconda is a free, lightweight Python package manager)"
    echo ""

    OS=$(uname -s)
    ARCH=$(uname -m)

    if [ "$OS" = "Darwin" ]; then
        if [ "$ARCH" = "arm64" ]; then
            MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh"
        else
            MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh"
        fi
    else
        MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
    fi

    MINICONDA_INSTALLER="/tmp/miniconda_installer.sh"

    echo " [1/3] Downloading Miniconda (~90 MB)..."
    if command -v curl &>/dev/null; then
        curl -L "$MINICONDA_URL" -o "$MINICONDA_INSTALLER" --progress-bar
    elif command -v wget &>/dev/null; then
        wget -q --show-progress "$MINICONDA_URL" -O "$MINICONDA_INSTALLER"
    else
        echo " [ERROR] Neither curl nor wget found. Cannot download Miniconda."
        echo " Please install curl and try again."
        exit 1
    fi

    echo " [2/3] Installing Miniconda (silent install)..."
    bash "$MINICONDA_INSTALLER" -b -p "$MINICONDA_DIR"
    rm -f "$MINICONDA_INSTALLER"

    CONDA_EXE="$MINICONDA_DIR/bin/conda"
    echo " [OK] Miniconda installed."
    echo ""
fi

# ── Source conda so it is usable in this shell session ───────────────────────
CONDA_BASE=$(dirname "$(dirname "$CONDA_EXE")")
source "$CONDA_BASE/etc/profile.d/conda.sh" 2>/dev/null || true

# Save path for run.sh
echo "$CONDA_EXE" > .conda_path.txt
chmod +x run.sh

# ── Create or update the nrtoxpred environment ───────────────────────────────
echo " [3/3] Setting up the NR-ToxPred Python environment..."
echo "       (This can take 5-15 minutes — please be patient)"
echo ""

if "$CONDA_EXE" env create -f environment_setup.yml 2>/dev/null; then
    echo " Environment created."
else
    echo " Environment already exists, updating instead..."
    "$CONDA_EXE" env update -f environment_setup.yml --prune
fi

echo ""
echo " ============================================="
echo "   Installation complete!"
echo "   Launch NR-ToxPred by running:  bash run.sh"
echo " ============================================="
echo ""
