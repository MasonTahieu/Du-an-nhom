@echo off
setlocal
cd /d "%~dp0"
echo Nap BCTC nam cho danh muc HOSE, HNX, UPCOM theo nguon ho tro.
echo Neu chua co danh muc, chay 00-Nap-Danh-Muc-Thi-Truong.cmd truoc.
call "%~dp0_python.cmd" -m vnresearch.manual financials --all-market --annual-only %*
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" echo Chua hoan tat. Xem thong bao loi phia tren; du lieu da luu duoc giu lai.
pause
exit /b %RESULT%
