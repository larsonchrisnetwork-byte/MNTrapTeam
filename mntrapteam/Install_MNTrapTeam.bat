@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo Installing MNTrapTeam
echo ==========================================

set "PYTHON_CMD="
for %%V in (3.14 3.13 3.12 3.11) do (
    if not defined PYTHON_CMD (
        py -%%V --version >nul 2>nul
        if not errorlevel 1 set "PYTHON_CMD=py -%%V"
    )
)
if not defined PYTHON_CMD (
    python --version >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python"
)
if not defined PYTHON_CMD (
    echo No usable Python 3 installation was found.
    pause
    exit /b 1
)

echo Using Python:
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

".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :fail

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :fail

".venv\Scripts\python.exe" -m compileall -q mntrapteam
if errorlevel 1 goto :fail

".venv\Scripts\python.exe" -m pytest -q -c pytest.ini tests
if errorlevel 1 goto :fail

echo.
echo Installation completed successfully.
echo Run Run_MNTrapTeam.bat to start MNTrapTeam.
pause
exit /b 0

:fail
echo.
echo Installation failed. Review the error above.
pause
exit /b 1
