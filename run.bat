@echo off
title NR-ToxPred
color 0A

:: Change to the folder where this script lives
cd /d "%~dp0"

echo.
echo  =============================================
echo    NR-ToxPred  ^|  Starting...
echo  =============================================
echo.

:: ── Locate conda (saved path first, then common locations, then PATH) ─────────
set "CONDA_EXE="

if exist ".conda_path.txt" (
    set /p CONDA_EXE=<.conda_path.txt
    if not exist "%CONDA_EXE%" set "CONDA_EXE="
)

if not defined CONDA_EXE (
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
            goto :found_conda
        )
    )
    where conda >nul 2>&1
    if %errorlevel% equ 0 (
        for /f "tokens=*" %%i in ('where conda') do (
            set "CONDA_EXE=%%i"
            goto :found_conda
        )
    )
    echo  [ERROR] Conda not found. Please run install.bat first.
    pause
    exit /b 1
)

:found_conda
:: ── Derive the conda base directory ──────────────────────────────────────────
for %%i in ("%CONDA_EXE%") do set "CONDA_SCRIPTS=%%~dpi"
for %%i in ("%CONDA_SCRIPTS%\.") do set "CONDA_BASE=%%~dpi"
:: Remove trailing backslash
if "%CONDA_BASE:~-1%"=="\" set "CONDA_BASE=%CONDA_BASE:~0,-1%"

set "ENV_DIR=%CONDA_BASE%\envs\nrtoxpred"
set "PYTHON_EXE=%ENV_DIR%\python.exe"

if not exist "%PYTHON_EXE%" (
    echo  [ERROR] Python not found in the nrtoxpred environment.
    echo  Expected: %PYTHON_EXE%
    echo.
    echo  Please run install.bat again to repair the installation.
    pause
    exit /b 1
)

:: ── Set PATH so conda DLLs (rdkit, numpy, etc.) are found ────────────────────
:: Running python.exe directly without conda activate skips the DLL search paths.
:: We add them manually here so C extensions load correctly.
set "PATH=%ENV_DIR%;%ENV_DIR%\Library\bin;%ENV_DIR%\Library\mingw-w64\bin;%ENV_DIR%\Library\usr\bin;%ENV_DIR%\Scripts;%PATH%"

:: ── Launch the application ────────────────────────────────────────────────────
echo  Launching NR-ToxPred GUI...
echo  (A download window may appear on first launch to fetch the models)
echo.

:: Capture both stdout and stderr so crash details are never blank
"%PYTHON_EXE%" -u pytox_gui.py > error.log 2>&1
set APP_EXIT=%errorlevel%

if %APP_EXIT% neq 0 (
    echo.
    echo  [ERROR] The application crashed (exit code %APP_EXIT%).
    echo  -----------------------------------------------
    if exist error.log (
        for %%A in (error.log) do if %%~zA gtr 0 (
            type error.log
        ) else (
            echo  (no output in error.log - checking crash.log for C-level details)
            echo.
            if exist crash.log (
                for %%B in (crash.log) do if %%~zB gtr 0 (
                    echo  === crash.log contents ===
                    type crash.log
                ) else (
                    echo  crash.log is also empty - crash happened before Python started
                )
            ) else (
                echo  crash.log not found - crash happened before Python started
            )
            echo.
            echo  === Diagnostics ===
            "%PYTHON_EXE%" --version
            "%PYTHON_EXE%" -c "import numpy; print('numpy', numpy.__version__)" 2>&1
            "%PYTHON_EXE%" -c "from rdkit import Chem; print('rdkit OK')" 2>&1
            "%PYTHON_EXE%" -c "import tkinter; print('tkinter OK')" 2>&1
            "%PYTHON_EXE%" -c "import sklearn; print('sklearn', sklearn.__version__)" 2>&1
            "%PYTHON_EXE%" -c "from molvs import standardize_smiles; print('molvs OK')" 2>&1
        )
    )
    echo  -----------------------------------------------
    echo.
    echo  Please take a screenshot of this window and report the issue.
    pause
)

del /f /q error.log 2>nul
