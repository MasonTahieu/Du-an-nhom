@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "VNSTOCK_DISABLE_AGENT_SETUP=1"
set "VNSTOCK_DISABLE_GLOBAL_AGENT=1"
set "VNSTOCK_AGENT_TARGETS=none"
if not exist "%~dp0.venv\Scripts\python.exe" (
 echo Chay Cai-Dat.cmd truoc.
 exit /b 1
)
call "%~dp0.venv\Scripts\activate.bat"
"%~dp0.venv\Scripts\python.exe" %*
exit /b %errorlevel%
