@echo off
cd /d "%~dp0"
echo Lay danh muc co phieu HOSE, HNX, UPCOM.
call "%~dp0_python.cmd" -m vnresearch.manual universe %*
pause
