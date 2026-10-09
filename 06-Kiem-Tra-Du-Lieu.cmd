@echo off
cd /d "%~dp0"
echo Chi doc du lieu da luu, khong goi API.
call "%~dp0_python.cmd" -m vnresearch.manual check
pause
