@echo off
setlocal
cd /d "%~dp0"
py -3 -m venv .venv
if errorlevel 1 goto :fail
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 goto :fail
echo.
echo Installation complete. Run Run_MNTrapTeam.bat
pause
exit /b 0
:fail
echo Installation failed. Verify Python 3.11+ is installed and on PATH.
pause
exit /b 1
