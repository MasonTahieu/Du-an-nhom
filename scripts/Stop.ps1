$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskPidPath = Join-Path $taskRoot 'logs\server.pid'
if (-not (Test-Path -LiteralPath $taskPidPath)) { Write-Host 'Khong co ung dung duoc script nay ghi nhan.'; exit }
$taskRecordedPid = [int](Get-Content -LiteralPath $taskPidPath)
$taskRecorded = Get-CimInstance Win32_Process -Filter ("ProcessId="+$taskRecordedPid) -ErrorAction SilentlyContinue
if (-not $taskRecorded) { Write-Host 'Ung dung da dung.'; exit }
if ($taskRecorded.CommandLine -notmatch '-m\s+vnresearch\s+serve') { throw 'PID khong con thuoc ung dung; khong dung tien trinh nay.' }
$taskChildren = Get-CimInstance Win32_Process -Filter ("ParentProcessId="+$taskRecordedPid) -ErrorAction SilentlyContinue
foreach ($taskChild in $taskChildren) {
    if ($taskChild.CommandLine -match '-m\s+vnresearch\s+serve') { Stop-Process -Id $taskChild.ProcessId -ErrorAction SilentlyContinue }
}
Stop-Process -Id $taskRecordedPid -ErrorAction SilentlyContinue
Write-Host 'Da dung ung dung.'
