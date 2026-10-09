@echo off
cd /d "%~dp0"
echo Nap BCTC nam va quy cho cac ma trong config/watchlist.json.
call "%~dp0_python.cmd" -m vnresearch.manual financials %*
pause
