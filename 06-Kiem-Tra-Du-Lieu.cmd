@echo off
setlocal
cd /d "%~dp0"
echo Chi kiem tra du lieu da luu, khong goi API va khong sua du lieu.
call "%~dp0_python.cmd" -m vnresearch.manual check
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" echo Chua hoan tat. Xem thong bao loi phia tren; du lieu da luu duoc giu lai.
pause
exit /b %RESULT%
