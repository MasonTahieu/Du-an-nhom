@echo off
cd /d "%~dp0"
echo Cap nhat gia cac phien da dong. Nen chay sau 16:00.
call "%~dp0_python.cmd" -m vnresearch.manual history %*
pause
