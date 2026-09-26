@echo off
cd /d "%~dp0"

if not exist ".venv" (
    echo Sanal ortam olusturuluyor, ilk acilis biraz surebilir...
    py -3 -m venv .venv
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

".venv\Scripts\python.exe" main.py
