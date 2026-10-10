@echo off
setlocal
cd /d "%~dp0"
echo Nap vi mo, ty gia va tin theo nguon cau hinh.
call "%~dp0_python.cmd" -m vnresearch.manual context %*
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" echo Chua hoan tat. Xem thong bao loi phia tren; du lieu da luu duoc giu lai.
pause
exit /b %RESULT%
