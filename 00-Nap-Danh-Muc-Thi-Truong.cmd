@echo off
setlocal
cd /d "%~dp0"
echo Cap nhat danh muc co phieu HOSE, HNX, UPCOM.
call "%~dp0_python.cmd" -m vnresearch.manual universe %*
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" echo Chua hoan tat. Xem thong bao loi phia tren; du lieu da luu duoc giu lai.
pause
exit /b %RESULT%
