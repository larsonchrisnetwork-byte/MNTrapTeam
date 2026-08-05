@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher was not found. Install Python 3.11 or newer and enable Add Python to PATH.
  pause
  exit /b 1
)
py -3 -m venv .venv
if errorlevel 1 goto :fail
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -e .
if errorlevel 1 goto :fail
python -m pytest -q
if errorlevel 1 goto :fail
echo.
echo Installation and tests completed successfully.
pause
exit /b 0
:fail
echo.
echo Installation failed. Review the error above.
pause
exit /b 1
