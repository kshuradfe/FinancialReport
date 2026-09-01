@echo off
rem ---------------------------------------------------------------
rem  FinScope launcher.
rem  Keep this file pure ASCII with CRLF line endings: cmd.exe re-reads
rem  batch files byte by byte using the active code page, so non-ASCII
rem  text here corrupts parsing of every line that follows.
rem  All user-facing messages live in run_finscope.py instead.
rem ---------------------------------------------------------------
setlocal
cd /d "%~dp0"
title FinScope

if exist ".venv\Scripts\python.exe" (
  set "PY=.venv\Scripts\python.exe"
  goto run
)

py -3 --version >nul 2>nul
if not errorlevel 1 (
  set "PY=py -3"
  goto run
)

python --version >nul 2>nul
if not errorlevel 1 (
  set "PY=python"
  goto run
)

goto nopython

:run
%PY% run_finscope.py %*
set "CODE=%ERRORLEVEL%"
if not "%CODE%"=="0" goto failed
exit /b 0

:failed
echo.
echo   Startup failed with exit code %CODE%.
echo   The details are in the messages above.
echo.
pause
exit /b %CODE%

:nopython
echo.
echo   Python was not found.
echo   Install Python 3.10 or newer from https://www.python.org
echo   and tick "Add python.exe to PATH" during setup, then run this again.
echo.
pause
exit /b 1
