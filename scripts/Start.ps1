$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
$taskVenv = Join-Path $HOME '.venv'
$taskPython = Join-Path $taskVenv 'Scripts\python.exe'
# Child Python process writes Vietnamese messages to redirected log files.
# PowerShell Start-Process does not inherit the environment set by _python.cmd.
# Without UTF-8, Windows may encode redirected stdout/stderr as cp1252 (charmap).
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8:backslashreplace'
$env:VNSTOCK_DISABLE_AGENT_SETUP = '1'
$env:VNSTOCK_DISABLE_GLOBAL_AGENT = '1'
$env:VNSTOCK_AGENT_TARGETS = 'none'
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Chay Cai-Dat.cmd truoc.' }
$taskLogs = Join-Path $taskRoot 'logs'
New-Item -ItemType Directory -Path $taskLogs -Force | Out-Null
try {
    $taskReply = Invoke-RestMethod 'http://127.0.0.1:8001/api/status' -TimeoutSec 2
    if ($taskReply.mode -eq 'sample') {
        Start-Process 'http://127.0.0.1:8001'
        exit
    }
} catch {}
$taskProcess = Start-Process -FilePath $taskPython -ArgumentList @('-m','vnresearch','serve','--port','8001') -WorkingDirectory $taskRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $taskLogs 'server.log') -RedirectStandardError (Join-Path $taskLogs 'server-error.log')
Set-Content -LiteralPath (Join-Path $taskLogs 'server.pid') -Value $taskProcess.Id
for ($taskAttempt=0; $taskAttempt -lt 30; $taskAttempt++) {
    Start-Sleep -Milliseconds 500
    try {
        Invoke-RestMethod 'http://127.0.0.1:8001/api/status' -TimeoutSec 1 | Out-Null
        Start-Process 'http://127.0.0.1:8001'
        Write-Host 'Ung dung dang chay tai http://127.0.0.1:8001'
        exit
    } catch {}
}
throw 'Khong mo duoc ung dung. Xem logs/server-error.log.'
