@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo MNTrapTeam is not installed yet.
    echo Run Install_MNTrapTeam.bat first.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m mntrapteam
if errorlevel 1 pause
endlocal
