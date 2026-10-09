@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Setup.ps1" %*
pause
