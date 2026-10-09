@echo off
cd /d "%~dp0"
call "%~dp0_python.cmd" -m vnresearch verify --mode submission
if errorlevel 1 goto end
call "%~dp0_python.cmd" -m vnresearch report VCB --mode submission --output "output/pdf/VCB_Bao_cao_2026-10-09.pdf"
:end
pause
