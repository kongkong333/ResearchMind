@echo off
setlocal

cd /d "%~dp0"

set "PYTHON_EXE=%CD%\researchmind\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
  echo [ResearchMind] Project virtualenv not found:
  echo   %PYTHON_EXE%
  echo Please run initial setup first:
  echo   py -m venv researchmind
  echo   researchmind\Scripts\python.exe -m pip install -e .[dev]
  pause
  exit /b 1
)

"%PYTHON_EXE%" scripts\start_webapp.py
if errorlevel 1 (
  pause
  exit /b 1
)
exit /b 0
