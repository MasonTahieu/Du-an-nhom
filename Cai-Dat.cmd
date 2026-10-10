@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Setup.ps1" %*
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" echo Chua hoan tat. Xem thong bao loi phia tren; du lieu da luu duoc giu lai.
pause
exit /b %RESULT%
