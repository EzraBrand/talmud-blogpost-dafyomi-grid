$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$builder = Join-Path $root "build_blogpost_dafyomi_db.py"
$grid = Join-Path $root "blogpost_dafyomi_grid.html"

if (-not (Test-Path $builder)) {
    throw "Missing builder script: $builder"
}

python $builder
Start-Process $grid
Write-Host "Opened grid: $grid"
