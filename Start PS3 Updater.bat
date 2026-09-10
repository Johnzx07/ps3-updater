@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title PS3 Updater

rem ---------------------------------------------------------------------------
rem Step 0: prefer the packaged EXE when it exists (built by PyInstaller).
rem Rebuild with:  pyinstaller --onefile --windowed --name PS3Updater ps3_updater.py
rem If dist\PS3Updater.exe is missing, fall through to running from source.
rem ---------------------------------------------------------------------------
if exist "%~dp0dist\PS3Updater.exe" (
    start "" "%~dp0dist\PS3Updater.exe"
    exit /b 0
)

rem ---------------------------------------------------------------------------
rem Step 1: locate a working Python interpreter.
rem We only check that the interpreter RUNS here; required modules are checked
rem separately below so we can tell "no Python" apart from "Python but missing
rem packages". Detection order is preserved: py -3.12, then py -3, then python.
rem ---------------------------------------------------------------------------
set "PYCMD="
call :findpy "py -3.12" && goto found
call :findpy "py -3" && goto found
call :findpy "python" && goto found

echo [PS3 Updater] No suitable Python found on this machine.
echo Install Python 3 from https://www.python.org/downloads/ and tick
echo "Add python.exe to PATH" during setup, then double-click again.
pause
exit /b 1

:found
rem ---------------------------------------------------------------------------
rem Step 2-4: verify the required modules with the interpreter we found.
rem   tkinter  - standard library GUI toolkit (ships with Windows Python)
rem   requests - third-party, pip package 'requests'
rem   yaml     - provided by the third-party pip package 'PyYAML'
rem We collect whatever is missing and report it; we never auto-install.
rem ---------------------------------------------------------------------------
set "MISSING="
call :hasmod tkinter || set "MISSING=%MISSING%tkinter "
call :hasmod requests || set "MISSING=%MISSING%requests "
call :hasmod yaml || set "MISSING=%MISSING%PyYAML "

if defined MISSING goto missing

echo Starting PS3 Updater with: %PYCMD%
%PYCMD% "%~dp0ps3_updater.py"
if errorlevel 1 (
    echo.
    echo [PS3 Updater] The app exited with an error, code %errorlevel%. See messages above.
    pause
)
exit /b 0

:missing
echo.
echo [PS3 Updater] Python was found (%PYCMD%) but required module(s) are missing:
echo     %MISSING%
echo.
echo To install the pip packages requests and/or PyYAML, run this once in a terminal:
echo     %PYCMD% -m pip install requests PyYAML
echo or, if you use the py launcher:
echo     py -3 -m pip install requests PyYAML
echo If tkinter is listed above it ships with the standard Windows Python installer;
echo reinstall Python from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
echo.
echo Then double-click this file again.
pause
exit /b 1

:findpy
set "PYCMD=%~1"
%~1 --version >nul 2>&1
if not errorlevel 1 exit /b 0
exit /b 1

:hasmod
%PYCMD% -c "import %~1" >nul 2>&1
if not errorlevel 1 exit /b 0
exit /b 1
