@echo off
setlocal
cd /d "%~dp0"
echo Cap nhat gia cac ma da co lich su gia tren may va VNINDEX.
echo Tu 15:30 gio Viet Nam moi lay du lieu ngay hien tai. Can co Internet.
echo Lich su da luu duoc giu lai. Neu chua co phien moi, chay lai de kiem tra.
call "%~dp0_python.cmd" -m vnresearch.manual history --stored %*
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" echo Chua hoan tat. Xem thong bao loi phia tren; du lieu da luu duoc giu lai.
pause
exit /b %RESULT%
