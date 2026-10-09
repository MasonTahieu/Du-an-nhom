@echo off
cd /d "%~dp0"
echo Nap nguon da cau hinh trong config/sources.json.
call "%~dp0_python.cmd" -m vnresearch.manual context %*
pause
