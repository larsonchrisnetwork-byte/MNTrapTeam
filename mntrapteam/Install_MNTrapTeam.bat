@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ==========================================
echo       MNTrapTeam Windows Installation
echo ==========================================
echo.

set "PYTHON_CMD="
where py >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=py -3"
if not defined PYTHON_CMD (
  where python >nul 2>nul
  if not errorlevel 1 set "PYTHON_CMD=python"
)
if not defined PYTHON_CMD (
  echo ERROR: Python 3 was not found.
  echo Install a current 64-bit Python 3 release and try again.
  pause
  exit /b 1
)

%PYTHON_CMD% -c "import sys; print('Using Python',sys.version.split()[0]); raise SystemExit(0 if sys.version_info >= (3,11) else 1)"
if errorlevel 1 (
  echo ERROR: MNTrapTeam requires Python 3.11 or newer.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating private Python environment...
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 goto :fail
)
set "PYTHON=.venv\Scripts\python.exe"

echo Updating pip...
"%PYTHON%" -m pip install --upgrade pip
if errorlevel 1 goto :fail

echo Installing dependencies...
"%PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 goto :fail

echo Validating source files...
"%PYTHON%" -m compileall -q mntrapteam main.py
if errorlevel 1 goto :fail

echo Running automated tests...
"%PYTHON%" -m pytest -q -c pytest.ini tests
if errorlevel 1 goto :fail

echo.
echo Installation and all tests completed successfully.
echo Start MNTrapTeam with Run_MNTrapTeam.bat.
pause
exit /b 0

:fail
echo.
echo Installation failed. Review the error above.
pause
exit /b 1
