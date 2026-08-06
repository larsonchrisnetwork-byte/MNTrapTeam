
param([switch]$WhatIf)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$patterns = @(
    "Apply_v1.*.py",
    "Apply_v1.*.ps1",
    "Flatten_Current_Repository.ps1",
    "README_UPGRADE.md"
)

$targets = foreach ($pattern in $patterns) {
    Get-ChildItem -Path . -File -Filter $pattern -ErrorAction SilentlyContinue
}
$targets = $targets | Sort-Object FullName -Unique

if (-not $targets) {
    Write-Host "No obsolete upgrade files were found."
    exit 0
}

Write-Host "Obsolete files:"
$targets | ForEach-Object { Write-Host "  $($_.Name)" }

if ($WhatIf) {
    Write-Host "WhatIf mode: nothing was removed."
    exit 0
}

$targets | Remove-Item -Force
Write-Host "Obsolete upgrade files removed."
