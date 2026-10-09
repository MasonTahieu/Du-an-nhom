@echo off
cd /d "%~dp0"
echo Lay lich su theo config/watchlist.json. Co luu tien do; chay lai de tiep tuc.
call "%~dp0_python.cmd" -m vnresearch.manual history --initial %*
pause
