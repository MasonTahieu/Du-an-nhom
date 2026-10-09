@echo off
cd /d "%~dp0"
echo Cap nhat gia ba san cho cac phien da dong.
call "%~dp0_python.cmd" -m vnresearch.manual history --all-market %*
pause
