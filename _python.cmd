@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "VNSTOCK_DISABLE_AGENT_SETUP=1"
set "VNSTOCK_DISABLE_GLOBAL_AGENT=1"
set "VNSTOCK_AGENT_TARGETS=none"
if not exist "%USERPROFILE%\.venv\Scripts\python.exe" (
 echo Chay Cai-Dat.cmd truoc.
 exit /b 1
)
call "%USERPROFILE%\.venv\Scripts\activate.bat"
python %*
exit /b %errorlevel%
