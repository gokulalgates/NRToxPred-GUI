@echo off
title NR-ToxPred Installer
color 0A

:: Change to the folder where this script lives
cd /d "%~dp0"

echo.
echo  =============================================
echo    NR-ToxPred  ^|  One-Time Installation
echo  =============================================
echo.

:: ── Find conda (check PATH and common install locations) ─────────────────────
set "CONDA_EXE="

where conda >nul 2>&1
if %errorlevel% equ 0 (
    set "CONDA_EXE=conda"
    echo  [OK] Conda already installed.
    goto :setup_env
)

for %%P in (
    "%UserProfile%\miniconda3\Scripts\conda.exe"
    "%UserProfile%\Miniconda3\Scripts\conda.exe"
    "%UserProfile%\anaconda3\Scripts\conda.exe"
    "%LocalAppData%\miniconda3\Scripts\conda.exe"
    "C:\ProgramData\miniconda3\Scripts\conda.exe"
    "C:\ProgramData\Miniconda3\Scripts\conda.exe"
) do (
    if exist %%P (
        set "CONDA_EXE=%%~P"
        echo  [OK] Conda found at %%~P
        goto :setup_env
    )
)

:: ── Miniconda not found — download and install it silently ───────────────────
echo  Miniconda not found. Downloading it now...
echo  (Miniconda is a free, lightweight Python package manager)
echo.

set "MINICONDA_URL=https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe"
set "MINICONDA_INSTALLER=%TEMP%\miniconda_installer.exe"
set "MINICONDA_DIR=%UserProfile%\miniconda3"

echo  [1/3] Downloading Miniconda (~90 MB) ...
powershell -NoProfile -Command ^
  "Invoke-WebRequest -Uri '%MINICONDA_URL%' -OutFile '%MINICONDA_INSTALLER%' -UseBasicParsing"
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Download failed. Check your internet connection and try again.
    pause
    exit /b 1
)

echo  [2/3] Installing Miniconda (this takes about 1 minute) ...
start /wait "" "%MINICONDA_INSTALLER%" /S /D=%MINICONDA_DIR%
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Miniconda installation failed.
    pause
    exit /b 1
)

set "CONDA_EXE=%MINICONDA_DIR%\Scripts\conda.exe"
echo  [OK] Miniconda installed successfully.
echo.

:setup_env
:: ── Remove old environment if it exists (ensures version pins are respected) ──
"%CONDA_EXE%" env list | find "nrtoxpred" >nul 2>&1
if %errorlevel% equ 0 (
    echo  Removing old environment to apply updates...
    "%CONDA_EXE%" env remove -n nrtoxpred -y
)

:: ── Create the nrtoxpred conda environment ────────────────────────────────────
echo  [3/3] Setting up the NR-ToxPred Python environment...
echo        (This can take 5-15 minutes — please be patient)
echo.

"%CONDA_EXE%" env create -f environment_setup.yml
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Environment setup failed.
    echo  Please take a screenshot of this window and contact support.
    pause
    exit /b 1
)

:: ── Save conda path for run.bat ───────────────────────────────────────────────
echo %CONDA_EXE%> .conda_path.txt

echo.
echo  =============================================
echo    Installation complete!
echo    Double-click run.bat to launch NR-ToxPred.
echo  =============================================
echo.
pause
