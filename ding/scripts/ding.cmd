@echo off
setlocal
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ding.ps1" %*
exit /b %ERRORLEVEL%
