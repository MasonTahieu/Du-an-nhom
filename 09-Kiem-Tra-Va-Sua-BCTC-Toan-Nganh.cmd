@echo off
setlocal
cd /d "%~dp0"
echo Sua anh xa BCTC quy da luu va thong ke du lieu toan nganh; khong goi Internet.
call "%~dp0_python.cmd" -m vnresearch.universal_repair
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" echo Chua hoan tat. Xem thong bao loi phia tren; du lieu da luu duoc giu lai.
pause
exit /b %RESULT%
