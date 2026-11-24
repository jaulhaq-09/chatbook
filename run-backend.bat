@echo off
echo Starting Chatbook Backend...
cd /d "%~dp0backend"
if exist ".venv\Scripts\uvicorn.exe" (
    ".venv\Scripts\uvicorn.exe" app.main:app --reload
) else (
    uvicorn app.main:app --reload
)
pause
