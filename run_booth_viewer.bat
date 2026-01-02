@echo off
cd /d %~dp0
echo Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Failed to install dependencies.
    pause
    exit /b
)

echo Starting Booth Viewer...
python app.py
pause