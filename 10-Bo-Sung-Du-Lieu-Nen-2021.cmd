@echo off
setlocal
cd /d "%~dp0"
echo Bo sung nam nen tu cache da co; khong goi Internet.
call "%~dp0_python.cmd" -m vnresearch.annual_baseline %*
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" echo Chua hoan tat. Xem thong bao loi phia tren; du lieu da luu duoc giu lai.
pause
exit /b %RESULT%
