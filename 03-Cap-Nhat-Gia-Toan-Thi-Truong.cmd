@echo off
setlocal
cd /d "%~dp0"
echo Cap nhat gia toan thi truong cho cac phien da dong.
echo Lich su da luu duoc giu lai. Chay lai de bo sung phan con thieu.
call "%~dp0_python.cmd" -m vnresearch.manual history --all-market %*
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" echo Chua hoan tat. Xem thong bao loi phia tren; du lieu da luu duoc giu lai.
pause
exit /b %RESULT%
