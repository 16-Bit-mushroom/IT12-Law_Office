@echo off
:: Sets the directory to wherever this file is saved (handles spaces in "IT12 Law_Office")
cd /d "%~dp0"

:: Activate the virtual environment (Updated for .venv)
call .venv\Scripts\activate

:: Run the server
python serve.py

pause