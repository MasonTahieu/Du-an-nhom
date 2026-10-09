param([switch]$Market, [switch]$Dev)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
$taskPython = Get-Command python -ErrorAction SilentlyContinue
if (-not $taskPython) { throw 'Can cai Python 3.11 tu python.org, them Python vao PATH roi chay lai.' }
python -c "import sys; assert sys.version_info >= (3,11), 'Python >=3.11 required'"
if ($LASTEXITCODE -ne 0) { throw 'Python qua cu. Can Python >=3.11 (khuyen nghi 3.11).' }
$taskVenv = Join-Path $HOME '.venv'
if (-not (Test-Path -LiteralPath (Join-Path $taskVenv 'Scripts\python.exe'))) {
    python -m venv $taskVenv
}
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
& (Join-Path $taskVenv 'Scripts\Activate.ps1')
python -m pip install -r requirements.lock.txt
if ($LASTEXITCODE -ne 0) { throw 'Cai thu vien that bai. Kiem tra mang va phien ban Python.' }
if ($Market) {
    python -m pip install -r requirements-market.txt
    if ($LASTEXITCODE -ne 0) { throw 'Cai vnstock that bai. Demo offline van dung duoc.' }
}
if ($Dev) {
    python -m pip install -r requirements-dev.txt
    if ($LASTEXITCODE -ne 0) { throw 'Cai thu vien kiem thu that bai.' }
}
python -m vnresearch verify
if ($LASTEXITCODE -ne 0) { throw 'Du lieu demo khong khop. Tai lai data/sample tu Git.' }
Write-Host 'San sang. Chay Mo-Ung-Dung.cmd de mo giao dien.' -ForegroundColor Green
