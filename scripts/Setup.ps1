param([switch]$Market, [switch]$Dev, [switch]$Offline)
# Default installation remains complete; -Market is kept for old callers.
$ErrorActionPreference = 'Stop'
if ($Market -and $Offline) { throw 'Khong dung -Market va -Offline cung luc.' }
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:VNSTOCK_DISABLE_AGENT_SETUP = '1'
$env:VNSTOCK_DISABLE_GLOBAL_AGENT = '1'
$env:VNSTOCK_AGENT_TARGETS = 'none'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
$taskVenv = Join-Path $taskRoot '.venv'
$taskPython = Join-Path $taskVenv 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    $taskBootstrap = Get-Command python -ErrorAction SilentlyContinue
    $taskBootstrapArgs = @()
    if (-not $taskBootstrap) {
        $taskBootstrap = Get-Command py -ErrorAction SilentlyContinue
        $taskBootstrapArgs = @('-3')
    }
    if (-not $taskBootstrap) { throw 'Can cai Python 3.11 tu python.org, them Python vao PATH roi chay lai.' }
    & $taskBootstrap.Source @taskBootstrapArgs -c "import sys; assert sys.version_info >= (3,11), 'Python >=3.11 required'"
    if ($LASTEXITCODE -ne 0) { throw 'Python qua cu. Can Python >=3.11 (khuyen nghi 3.11).' }
    & $taskBootstrap.Source @taskBootstrapArgs -m venv $taskVenv
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $taskPython)) { throw 'Khong tao duoc .venv trong du an. Kiem tra quyen ghi va Python.' }
}
& $taskPython -c "import sys; assert sys.version_info >= (3,11), 'Python >=3.11 required'"
if ($LASTEXITCODE -ne 0) { throw '.venv hien co khong dung Python >=3.11. Tao lai moi truong bang Python 3.11.' }
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
& (Join-Path $taskVenv 'Scripts\Activate.ps1')
& $taskPython -m pip install --index-url https://pypi.org/simple -r requirements.lock.txt
if ($LASTEXITCODE -ne 0) { throw 'Cai thu vien that bai. Kiem tra mang va phien ban Python.' }
& $taskPython -m vnresearch verify
if ($LASTEXITCODE -ne 0) { throw 'Du lieu demo khong khop. Tai lai data/sample tu Git.' }
if (-not $Offline) {
    & $taskPython -m pip install --index-url https://pypi.org/simple -r requirements-market.txt
    if ($LASTEXITCODE -ne 0) { throw 'Phan ung dung va du lieu mau da san sang; bo nap du lieu chua cai xong. Kiem tra ket noi PyPI/vnstocks.com roi chay lai Cai-Dat.cmd. Co the xem du lieu da co, nhung chua tai du lieu thi truong moi.' }
}
if ($Dev) {
    & $taskPython -m pip install --index-url https://pypi.org/simple -c requirements.lock.txt -r requirements-dev.txt
    if ($LASTEXITCODE -ne 0) { throw 'Cai thu vien kiem thu that bai.' }
}
& $taskPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Thu vien dang xung dot. Xem thong bao pip check va chay lai Cai-Dat.cmd.' }
if ($Offline) {
    Write-Host 'Da cai/kiem tra phan ung dung. Bo nap online duoc bo qua trong lan nay; chay Cai-Dat.cmd khong kem -Offline de cai/kiem tra day du.' -ForegroundColor Yellow
}
Write-Host 'San sang. Chay Mo-Ung-Dung.cmd de mo giao dien.' -ForegroundColor Green
