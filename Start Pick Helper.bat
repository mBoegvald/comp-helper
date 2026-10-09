@echo off
rem Double-click to start the Pick Helper. It opens in your browser; close this window to stop it.
setlocal
cd /d "%~dp0"
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (where python >nul 2>nul && set "PY=python")
if not defined PY goto nopython
%PY% -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>nul || goto nopython
%PY% -c "import openpyxl" >nul 2>nul || (
  echo Installing openpyxl, only needed the first time...
  %PY% -m pip install --user openpyxl || goto fail
)
%PY% webapp.py %*
if errorlevel 1 goto fail
exit /b 0

:nopython
echo.
echo Python 3.10 or newer is needed. Install it from https://www.python.org/downloads/
echo and tick "Add python.exe to PATH" during setup. Then double-click this file again.
echo.
pause
exit /b 1

:fail
echo.
echo Something went wrong, see the message above.
pause
exit /b 1
