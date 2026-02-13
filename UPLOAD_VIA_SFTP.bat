@echo off
REM APIBlockchain - Direct SFTP Upload via PuTTY Plink
setlocal enabledelayedexpansion

cls
echo.
echo ╔════════════════════════════════════════╗
echo ║  APIBlockchain Webshop Upload          ║
echo ║  via SFTP                              ║
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

REM Credentials
set SFTP_PASSWORD=Nathnael1997
set SFTP_HOST=ssh.cruerobt5.service.one
set SFTP_USER=cruerobt5_ssh
set SFTP_PORT=22
set REMOTE_PATH=/home/cruerobt5/public_html
set LOCAL_PATH=c:\Users\gebruiker\Desktop\mijn_api\webshop_for_upload

echo Checking webshop files...
if not exist "%LOCAL_PATH%" (
    echo ERROR: Webshop files not found at %LOCAL_PATH%
    pause
    exit /b 1
)

echo Files found!
echo.

REM Download Plink
set PLINK_PATH=%TEMP%\plink.exe
if not exist "%PLINK_PATH%" (
    echo Downloading plink (SFTP tool)...
    powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://the.earth.li/~sgtatham/putty/latest/w64/plink.exe' -OutFile '%PLINK_PATH%' -UseBasicParsing"
    if !errorlevel! neq 0 (
        echo Failed to download plink
        pause
        exit /b 1
    )
    echo Downloaded successfully
)

echo.
echo Creating SFTP command script...

REM Create script for SFTP commands
set SCRIPT_FILE=%TEMP%\sftp_commands_%RANDOM%.txt
(
    echo cd %REMOTE_PATH%
    echo rm *.*
    echo mput *.*
    echo quit
) > "%SCRIPT_FILE%"

echo.
echo Starting SFTP upload...
echo Host: %SFTP_HOST%
echo User: %SFTP_USER%
echo Port: %SFTP_PORT%
echo.

REM Run SFTP via plink
cd /d "%LOCAL_PATH%"
echo %SFTP_PASSWORD% | "%PLINK_PATH%" -ssh -l %SFTP_USER% -P %SFTP_PORT% -m "%SCRIPT_FILE%" %SFTP_HOST%

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
    echo Open in browser - wait 10 seconds for DNS
    echo If you see 404, clear cache (Ctrl+Shift+Del)
    echo.
) else (
    cls
    echo.
    echo ╔════════════════════════════════════════╗
    echo ║  Upload Failed (Code: %RESULT%)          ║
    echo ╚════════════════════════════════════════╝
    echo.
    echo Check credentials and try again
    echo.
)

pause
exit /b %RESULT%
