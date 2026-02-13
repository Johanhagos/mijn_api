@echo off
REM APIBlockchain - Simplified Upload (No PowerShell dependency)
setlocal enabledelayedexpansion

cls
echo.
echo ╔════════════════════════════════════════╗
echo ║  APIBlockchain Webshop Upload          ║
echo ╚════════════════════════════════════════╝
echo.

REM Check admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Need Administrator rights
    echo Right-click and select "Run as Administrator"
    pause
    exit /b 1
)

REM Set credentials
set SFTP_PASSWORD=Nathnael1997&
set SFTP_HOST=ssh.cruerobt5.service.one
set SFTP_USER=cruerobt5_ssh
set SFTP_PORT=22
set REMOTE_PATH=/home/cruerobt5/public_html
set LOCAL_PATH=c:\Users\gebruiker\Desktop\mijn_api\webshop_for_upload

echo Checking WinSCP...
set WINSCP_PATH=C:\Program Files (x86)\WinSCP\WinSCP.com

if not exist "%WINSCP_PATH%" (
    echo.
    echo WinSCP not found. Please download and install:
    echo https://winscp.net/download
    echo.
    echo After installation, run this script again.
    pause
    exit /b 1
)

echo WinSCP found!
echo.
echo Creating upload script...

set SCRIPT_FILE=%TEMP%\winscp_upload_%RANDOM%.txt
(
    echo open sftp://%SFTP_USER%:%SFTP_PASSWORD%@%SFTP_HOST%:%SFTP_PORT%
    echo cd %REMOTE_PATH%
    echo lcd "%LOCAL_PATH%"
    echo put -r *
    echo close
    echo exit
) > "%SCRIPT_FILE%"

echo.
echo Starting upload to one.com...
echo.

REM Run upload
"%WINSCP_PATH%" /script="%SCRIPT_FILE%" /log="%TEMP%\winscp_log.txt"

set RESULT=%errorlevel%

REM Cleanup
del /q "%SCRIPT_FILE%" >nul 2>&1

echo.
if %RESULT% equ 0 (
    cls
    echo.
    echo ╔════════════════════════════════════════╗
    echo ║  SUCCESS - Webshop Uploaded!           ║
    echo ╚════════════════════════════════════════╝
    echo.
    echo Your website is now live:
    echo   https://apiblockchain.io
    echo.
    echo Open in browser and wait for page to load.
    echo If you see 404, clear cache (Ctrl+Shift+Del).
    echo.
) else (
    cls
    echo.
    echo ╔════════════════════════════════════════╗
    echo ║  Upload Failed                         ║
    echo ╚════════════════════════════════════════╝
    echo.
    echo Check upload log:
    echo   %TEMP%\winscp_log.txt
    echo.
)

pause
exit /b %RESULT%
