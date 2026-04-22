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

:: ── Find conda (PATH, saved path, or common locations) ───────────────────────
set "CONDA_EXE="

where conda >nul 2>&1
if %errorlevel% equ 0 (
    set "CONDA_EXE=conda"
    goto :check_env
)

if exist ".conda_path.txt" (
    set /p CONDA_EXE=<.conda_path.txt
    if exist "%CONDA_EXE%" goto :check_env
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
        goto :check_env
    )
)

echo  [ERROR] Conda not found.
echo  Please run install.bat first.
echo.
pause
exit /b 1

:check_env
:: ── Check the nrtoxpred environment exists ────────────────────────────────────
"%CONDA_EXE%" env list | find "nrtoxpred" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] NR-ToxPred environment not found.
    echo  Please run install.bat first.
    echo.
    pause
    exit /b 1
)

:: ── Launch the application ────────────────────────────────────────────────────
echo  Launching NR-ToxPred GUI...
echo  (A download window may appear on first launch to fetch the models)
echo.

"%CONDA_EXE%" run -n nrtoxpred python pytox_gui.py

if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] The application failed to start.
    echo  Try running install.bat again to repair the installation.
    echo.
    pause
)
