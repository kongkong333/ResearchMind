@echo off
setlocal

cd /d "%~dp0"

"%CD%\researchmind\Scripts\python.exe" scripts\stop_webapp.py
pause
exit /b 0
