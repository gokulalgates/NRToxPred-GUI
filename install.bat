@echo off
title NR-ToxPred Installer
color 0A

echo.
echo  =============================================
echo    NR-ToxPred  ^|  One-Time Installation
echo  =============================================
echo.

:: ── Check conda ──────────────────────────────────────────────────────────────
where conda >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Conda (Miniconda) is not installed.
    echo.
    echo  Please download and install Miniconda first:
    echo    https://docs.conda.io/en/latest/miniconda.html
    echo.
    echo  After installing Miniconda, close this window,
    echo  open a NEW terminal, and run install.bat again.
    echo.
    pause
    exit /b 1
)

echo  [OK] Conda found.
echo.

:: ── Create or update environment ─────────────────────────────────────────────
echo  [1/2] Setting up Python environment...
echo        (This can take 5-15 minutes on the first run)
echo.

conda env create -f environment_setup.yml 2>nul
if %errorlevel% neq 0 (
    echo  Environment already exists — updating instead...
    conda env update -f environment_setup.yml --prune
)

if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Environment setup failed.
    echo  Please check the error above or contact support.
    pause
    exit /b 1
)

echo.
echo  [2/2] Installation complete!
echo.
echo  =============================================
echo    Run NR-ToxPred by double-clicking run.bat
echo  =============================================
echo.
pause
