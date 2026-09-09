@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title PS3 Updater

rem Find a Python that has the libraries we need (tkinter + requests).
call :try "py -3.12" && goto run
call :try "py -3" && goto run
call :try "python" && goto run

echo [PS3 Updater] No suitable Python found on this machine.
echo Install Python 3 from https://www.python.org/downloads/ and tick
echo Add python.exe to PATH during setup, then double-click again.
pause
exit /b 1

:run
echo Starting PS3 Updater with: %PYCMD%
%PYCMD% "%~dp0ps3_updater.py"
if errorlevel 1 (
    echo.
    echo [PS3 Updater] The app exited with an error, code %errorlevel%. See messages above.
    pause
)
exit /b 0

:try
set "PYCMD=%~1"
%~1 -c "import tkinter, requests" >nul 2>&1
if not errorlevel 1 exit /b 0
exit /b 1
