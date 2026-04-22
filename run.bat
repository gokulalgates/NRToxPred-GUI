@echo off
title NR-ToxPred
color 0A

echo.
echo  =============================================
echo    NR-ToxPred  ^|  Starting...
echo  =============================================
echo.

:: ── Check conda ──────────────────────────────────────────────────────────────
where conda >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Conda not found.
    echo  Please run install.bat first.
    echo.
    pause
    exit /b 1
)

:: ── Check environment exists ─────────────────────────────────────────────────
conda env list | find "nrtoxpred" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] The nrtoxpred environment is not installed.
    echo  Please run install.bat first.
    echo.
    pause
    exit /b 1
)

:: ── Launch app ───────────────────────────────────────────────────────────────
echo  Launching NR-ToxPred GUI...
echo  (A setup window may appear on first launch to download models)
echo.

conda run -n nrtoxpred python pytox_gui.py

if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] The application crashed or failed to start.
    echo  Make sure install.bat completed successfully.
    echo.
    pause
)
