@echo off
setlocal
cd /d "%~dp0"
set "DEPLOY_MODE="
set "PORT=0"
set "HOST=127.0.0.1"
echo BDRIS React local test starting...
echo The correct page opens automatically after the server starts.
where npm >nul 2>nul
if %errorlevel%==0 (
  call npm start
  goto :done
)
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 server.py
  goto :done
)
where python >nul 2>nul
if %errorlevel%==0 (
  python server.py
  goto :done
)
echo Python 3 is required. Install Python 3 and try again.
:done
echo.
echo Server stopped. Read any error above.
pause
