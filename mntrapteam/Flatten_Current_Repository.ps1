$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
$nested = Join-Path $root "mntrapteam"
$nestedPackage = Join-Path $nested "mntrapteam"

if (-not (Test-Path $nestedPackage)) {
    Write-Host "No duplicated nested project was detected. Nothing to flatten."
    exit 0
}

Write-Host "Flattening duplicated MNTrapTeam project..."
$backup = Join-Path $root ("nested-project-backup-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
New-Item -ItemType Directory -Path $backup | Out-Null

$projectFiles = @(
    ".gitignore", "CHANGELOG.md", "LICENSE", "README.md", "VERSION",
    "Install_MNTrapTeam.bat", "Run_MNTrapTeam.bat", "main.py",
    "pytest.ini", "requirements.txt"
)
foreach ($name in $projectFiles) {
    $source = Join-Path $nested $name
    if (Test-Path $source) {
        if (Test-Path (Join-Path $root $name)) { Copy-Item (Join-Path $root $name) $backup -Force }
        Copy-Item $source (Join-Path $root $name) -Force
    }
}

$projectDirs = @("config", "docs", "samples")
foreach ($name in $projectDirs) {
    $source = Join-Path $nested $name
    $destination = Join-Path $root $name
    if (Test-Path $source) {
        if (Test-Path $destination) { Remove-Item $destination -Recurse -Force }
        Copy-Item $source $destination -Recurse -Force
    }
}

$destinationPackage = Join-Path $root "mntrapteam.new"
if (Test-Path $destinationPackage) { Remove-Item $destinationPackage -Recurse -Force }
Copy-Item $nestedPackage $destinationPackage -Recurse -Force
Remove-Item $nested -Recurse -Force
Rename-Item $destinationPackage "mntrapteam"

Get-ChildItem -Path $root -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $root -Recurse -File -Include *.pyc,*.pyo | Remove-Item -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $root ".pytest_cache") -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $root "pyproject.toml") -Force -ErrorAction SilentlyContinue

Write-Host "Repository flattened successfully. Backup of overwritten root files: $backup"
Write-Host "Run: Remove-Item .venv -Recurse -Force -ErrorAction SilentlyContinue"
Write-Host "Then: .\Install_MNTrapTeam.bat"
