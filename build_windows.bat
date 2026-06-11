@echo off
REM ===========================================================================
REM  Build PDFCombiner.exe on Windows.
REM
REM  Just double-click this file. It will:
REM    - find your Python (the ONLY thing that must already be installed),
REM    - create an isolated .venv (nothing is installed system-wide),
REM    - install PyQt6 / pypdf / PyInstaller into that .venv,
REM    - build a single-file PDFCombiner.exe,
REM    - copy it onto your Desktop.
REM
REM  The window stays open at the end so you can read the result.
REM ===========================================================================
setlocal EnableExtensions

REM Always run from the folder this script lives in (so double-click works).
cd /d "%~dp0"

echo(
echo === PDF Combiner build ===
echo(

REM ---------------------------------------------------------------------------
REM [1/5] Locate a working Python. Try the launcher first, then python/python3.
REM ---------------------------------------------------------------------------
echo [1/5] Looking for Python...
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY ( python --version >nul 2>&1 && set "PY=python" )
if not defined PY ( python3 --version >nul 2>&1 && set "PY=python3" )

if not defined PY (
    echo(
    echo ERROR: Python was not found on this PC.
    echo(
    echo Python is required to BUILD the .exe ^(it is not needed to RUN it^).
    echo Install it once from https://www.python.org/downloads/windows/
    echo and tick "Add python.exe to PATH" during setup, then run this again.
    goto :fail
)
echo       Using: %PY%

REM ---------------------------------------------------------------------------
REM [2/5] Create the isolated virtual environment (only if missing).
REM ---------------------------------------------------------------------------
echo [2/5] Preparing isolated build environment ^(.venv^)...
if not exist ".venv\Scripts\python.exe" (
    %PY% -m venv .venv || goto :fail
)
set "VPY=.venv\Scripts\python.exe"

REM ---------------------------------------------------------------------------
REM [3/5] Install build dependencies INTO the venv (nothing system-wide).
REM ---------------------------------------------------------------------------
echo [3/5] Installing dependencies ^(this can take a minute the first time^)...
"%VPY%" -m pip install --upgrade pip >nul || goto :fail
"%VPY%" -m pip install -r requirements.txt || goto :fail

REM ---------------------------------------------------------------------------
REM [4/5] Build a single-file exe straight onto the Desktop.
REM ---------------------------------------------------------------------------
echo [4/5] Building PDFCombiner.exe ...
set "DESKTOP=%USERPROFILE%\Desktop"
"%VPY%" -m PyInstaller --clean --noconfirm ^
    --distpath "%DESKTOP%" ^
    --workpath "build" ^
    PDFCombiner.spec || goto :fail

REM ---------------------------------------------------------------------------
REM [5/5] Confirm the result.
REM ---------------------------------------------------------------------------
if not exist "%DESKTOP%\PDFCombiner.exe" (
    echo(
    echo ERROR: The build finished but PDFCombiner.exe was not found on the Desktop.
    goto :fail
)

echo(
echo ============================================================
echo  SUCCESS!  PDFCombiner.exe is on your Desktop:
echo  %DESKTOP%\PDFCombiner.exe
echo  You can copy that single file to any Windows PC and run it
echo  - no Python needed there.
echo ============================================================
echo(
pause
exit /b 0

:fail
echo(
echo ------------------------------------------------------------
echo  BUILD FAILED. Read the messages above for the cause.
echo ------------------------------------------------------------
echo(
pause
exit /b 1
