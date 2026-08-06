@echo off
setlocal
cd /d "%~dp0"

if not exist .venv (
    echo Creating virtual environment...
    py -3 -m venv .venv
)

call .venv\Scripts\activate.bat
pip install -q -r requirements.txt
python -m app

endlocal
