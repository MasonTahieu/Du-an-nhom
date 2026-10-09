@echo off
cd /d "%~dp0"
echo Quet lich su ba san, co luu tien do de chay tiep.
call "%~dp0_python.cmd" -m vnresearch.manual history --all-market --initial %*
pause
