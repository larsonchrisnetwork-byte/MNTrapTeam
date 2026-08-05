$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$gui = Join-Path $PSScriptRoot "mntrapteam\gui.py"
if (Test-Path $gui) {
    $text = [System.IO.File]::ReadAllText($gui)
    $text = $text.Replace("MNTrapTeam 1.3", "MNTrapTeam 1.5")
    $old = "('hoa','HOA'),('singles_targets','Singles')"
    $new = "('hoa','HOA'),('cut_line_hoa','Cut HOA'),('hoa_gap_to_cut','Gap to Cut'),('birds_per_300_gap','Birds / 300'),('singles_targets','Singles')"
    if ($text.Contains($old)) {
        $text = $text.Replace($old, $new)
    }
    [System.IO.File]::WriteAllText(
        $gui,
        $text,
        [System.Text.UTF8Encoding]::new($false)
    )
}

Write-Host "MNTrapTeam 1.5 files applied."
Write-Host "Run: & `".\.venv\Scripts\python.exe`" -m pytest -q tests"
