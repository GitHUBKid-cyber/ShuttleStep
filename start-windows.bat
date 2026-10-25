@echo off
REM Double-click this file on Windows to start ShuttleStep.
cd /d "%~dp0"

python -c "import sys; sys.exit(sys.version_info < (3, 12))" >nul 2>nul
if errorlevel 1 (
  echo ShuttleStep needs Python 3.12 or newer. Install it from https://www.python.org/downloads/
  echo During install, tick "Add python.exe to PATH". Then double-click this file again.
  pause
  exit /b 1
)

if not exist venv (
  echo First-time setup: installing what ShuttleStep needs ^(this takes a few minutes^)...
  python -m venv venv || goto failed
  venv\Scripts\python -m pip install --upgrade pip
)

REM Install (or update) the add-ons whenever requirements.txt has changed since last time.
fc /b requirements.txt venv\installed-requirements.txt >nul 2>nul
if errorlevel 1 (
  venv\Scripts\pip install -r requirements.txt || goto failed
  copy /y requirements.txt venv\installed-requirements.txt >nul
)

venv\Scripts\python app.py
pause
exit /b 0

:failed
echo Setup failed. Send Claude a screenshot of this window.
pause
exit /b 1
