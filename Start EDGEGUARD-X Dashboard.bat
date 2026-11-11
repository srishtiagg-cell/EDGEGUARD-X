@echo off
setlocal

set "APP_DIR=%~dp0.venv"
set "PYTHON=%APP_DIR%\Scripts\python.exe"
set "LAUNCHER=%~dp0launch_dashboard.py"

if not exist "%PYTHON%" (
    echo Could not find the project Python environment:
    echo %PYTHON%
    pause
    exit /b 1
)

"%PYTHON%" "%LAUNCHER%"
