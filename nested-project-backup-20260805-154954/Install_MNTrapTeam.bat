@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo Installing MNTrapTeam
echo ==========================================

set "PYTHON_CMD="

py -3.14 --version >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=py -3.14"

if not defined PYTHON_CMD (
    py -3.13 --version >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=py -3.13"
)

if not defined PYTHON_CMD (
    py -3.12 --version >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=py -3.12"
)

if not defined PYTHON_CMD (
    py -3 --version >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=py -3"
)

if not defined PYTHON_CMD (
    python --version >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo No usable Python installation was found.
    echo Install Python 3.12 or newer and try again.
    pause
    exit /b 1
)

echo Using:
%PYTHON_CMD% --version

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    %PYTHON_CMD% -m venv .venv
)

if not exist ".venv\Scripts\python.exe" (
    echo Failed to create the virtual environment.
    pause
    exit /b 1
)

echo Updating pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip

if errorlevel 1 (
    echo Pip upgrade failed.
    pause
    exit /b 1
)

echo Installing dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt

if errorlevel 1 (
    echo Dependency installation failed.
    pause
    exit /b 1
)

echo Checking Python source files...
".venv\Scripts\python.exe" -m compileall -q mntrapteam

if errorlevel 1 (
    echo Python source validation failed.
    pause
    exit /b 1
)

if exist "tests" (
    echo Running automated tests...
    ".venv\Scripts\python.exe" -m pytest -q

    if errorlevel 1 (
        echo Tests failed.
        pause
        exit /b 1
    )
)

echo.
echo ==========================================
echo MNTrapTeam installation completed.
echo Run Run_MNTrapTeam.bat to start.
echo ==========================================
pause
endlocal