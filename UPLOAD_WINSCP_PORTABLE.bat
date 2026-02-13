@echo off
REM APIBlockchain - SFTP Upload using WinSCP Session
setlocal enabledelayedexpansion

cls
echo.
echo ╔════════════════════════════════════════╗
echo ║  APIBlockchain Webshop Upload          ║
echo ║  (WinSCP Session Method)               ║
echo ╚════════════════════════════════════════╝
echo.

REM Check admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    powershell -NoProfile -Command "Start-Process cmd -ArgumentList '/c %0' -Verb RunAs"
    exit /b 0
)

set SFTP_HOST=ssh.cruerobt5.service.one
set SFTP_USER=cruerobt5_ssh
set SFTP_PASSWORD=Nathnael1997
set SFTP_PORT=22
set REMOTE_PATH=/home/cruerobt5/public_html
set LOCAL_PATH=c:\Users\gebruiker\Desktop\mijn_api\webshop_for_upload

echo Checking files...
if not exist "%LOCAL_PATH%" (
    echo ERROR: Files not found
    pause
    exit /b 1
)

echo Files found!
echo.
echo Downloading WinSCP...

REM Download WinSCP portable version
set WINSCP_ZIP=%TEMP%\WinSCP.zip
set WINSCP_EXE=%TEMP%\WinSCP.com

powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://winscp.net/download/WinSCP-6.1-portable.zip' -OutFile '%WINSCP_ZIP%' -UseBasicParsing; Expand-Archive -Path '%WINSCP_ZIP%' -DestinationPath '%TEMP%' -Force" 2>nul

if not exist "%WINSCP_EXE%" (
    echo.
    echo WinSCP download failed. Trying alternative...
    powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://winscp.net/download/WinSCP-5.21.7-portable.zip' -OutFile '%WINSCP_ZIP%' -UseBasicParsing; Expand-Archive -Path '%WINSCP_ZIP%' -DestinationPath '%TEMP%' -Force" 2>nul
)

if not exist "%WINSCP_EXE%" (
    echo ERROR: Could not download WinSCP
    pause
    exit /b 1
)

echo WinSCP ready!
echo.

REM Create WinSCP script
set SCRIPT_FILE=%TEMP%\winscp_script_%RANDOM%.txt
(
    echo open sftp://%SFTP_USER%:%SFTP_PASSWORD%@%SFTP_HOST%:%SFTP_PORT%/
    echo synchronize remote "%LOCAL_PATH%" %REMOTE_PATH%
    echo close
    echo exit
) > "%SCRIPT_FILE%"

echo Uploading webshop files...
echo.

REM Execute upload
"%WINSCP_EXE%" /console /script="%SCRIPT_FILE%" /log="%TEMP%\winscp_%RANDOM%.log"

set RESULT=%errorlevel%

REM Cleanup
del /q "%SCRIPT_FILE%" 2>nul
del /q "%WINSCP_ZIP%" 2>nul

echo.
if %RESULT% equ 0 (
    cls
    echo.
    echo ╔════════════════════════════════════════╗
    echo ║  SUCCESS - Upload Complete!            ║
    echo ╚════════════════════════════════════════╝
    echo.
    echo Visit: https://apiblockchain.io
    echo.
    echo Wait 30 seconds for DNS cache
    echo Clear browser cache if 404 appears
    echo.
) else (
    cls
    echo.
    echo Upload result code: %RESULT%
    echo.
)

pause
exit /b %RESULT%
