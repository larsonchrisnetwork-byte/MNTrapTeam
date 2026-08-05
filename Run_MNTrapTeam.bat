@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo MNTrapTeam is not installed yet.
  echo Run Install_MNTrapTeam.bat first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" main.py
if errorlevel 1 (
  echo.
  echo MNTrapTeam closed because of an error.
  pause
)
