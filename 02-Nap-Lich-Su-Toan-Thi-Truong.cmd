@echo off
setlocal
cd /d "%~dp0"
echo Nap lich su gia toan thi truong tu ngay bat dau trong cau hinh.
echo Neu chua co danh muc, chay 00-Nap-Danh-Muc-Thi-Truong.cmd truoc.
call "%~dp0_python.cmd" -m vnresearch.manual history --all-market --initial %*
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" echo Chua hoan tat. Xem thong bao loi phia tren; du lieu da luu duoc giu lai.
pause
exit /b %RESULT%
