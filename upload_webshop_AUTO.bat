@echo off
REM APIBlockchain Webshop - Automated WinSCP Upload to one.com
REM This script downloads WinSCP, installs it, and uploads your webshop
REM
REM Your SFTP Details:
REM Host: ssh.cruerobt5.service.one
REM Username: cruerobt5_ssh
REM Port: 22
REM
REM Instructions:
REM 1. Edit this file and enter your SFTP password on line 20
REM 2. Run this script as Administrator
REM 3. Wait for completion

setlocal enabledelayedexpansion

REM ===== CONFIGURATION =====
REM CHANGE THIS TO YOUR SFTP PASSWORD:
set SFTP_PASSWORD=your_sftp_password_here

REM DO NOT CHANGE BELOW:
set SFTP_HOST=ssh.cruerobt5.service.one
set SFTP_USER=cruerobt5_ssh
set SFTP_PORT=22
set REMOTE_PATH=/home/cruerobt5/public_html
set LOCAL_PATH=c:\Users\gebruiker\Desktop\mijn_api\webshop_for_upload

REM ===== SCRIPT START =====
echo.
echo ========================================
echo APIBlockchain Webshop Upload to one.com
echo ========================================
echo.

REM Check if running as admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This script must run as Administrator
    echo.
    echo Right-click this file and select "Run as Administrator"
    pause
    exit /b 1
)

REM Check if SFTP password is set
if "%SFTP_PASSWORD%"=="your_sftp_password_here" (
    echo ERROR: SFTP password not set!
    echo.
    echo Please edit this file and replace:
    echo   your_sftp_password_here
    echo with your actual SFTP password
    echo.
    echo Then run again.
    pause
    exit /b 1
)

REM Check if local path exists
if not exist "%LOCAL_PATH%" (
    echo ERROR: Local path not found: %LOCAL_PATH%
    pause
    exit /b 1
)

echo SFTP Host: %SFTP_HOST%
echo SFTP User: %SFTP_USER%
echo Remote Path: %REMOTE_PATH%
echo.

REM Check if WinSCP is installed
set WINSCP_PATH=C:\Program Files (x86)\WinSCP\WinSCP.com
if not exist "%WINSCP_PATH%" (
    echo WinSCP not found. Attempting to download and install...
    echo.
    
    REM Create temp directory
    set TEMP_DIR=%TEMP%\winscp_install
    if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"
    
    REM Download WinSCP installer
    echo Downloading WinSCP...
    powershell -Command ^
        "$ProgressPreference = 'SilentlyContinue'; ^
        Invoke-WebRequest -Uri 'https://winscp.net/download/WinSCP-6.3-Setup.exe' ^
        -OutFile '%TEMP_DIR%\WinSCP-Setup.exe'"
    
    if errorlevel 1 (
        echo ERROR: Failed to download WinSCP
        echo.
        echo Please download manually from: https://winscp.net/download
        echo Then run this script again
        pause
        exit /b 1
    )
    
    REM Install WinSCP silently
    echo Installing WinSCP...
    "%TEMP_DIR%\WinSCP-Setup.exe" /S
    
    timeout /t 10 /nobreak
    
    REM Check if installation succeeded
    if not exist "%WINSCP_PATH%" (
        echo ERROR: WinSCP installation failed
        pause
        exit /b 1
    )
    
    echo WinSCP installed successfully!
    echo.
)

echo WinSCP found at: %WINSCP_PATH%
echo.
echo Starting upload...
echo.

REM Create WinSCP script
set SCRIPT_FILE=%TEMP%\winscp_upload.txt
(
    echo open sftp://%SFTP_USER%:%SFTP_PASSWORD%@%SFTP_HOST%:%SFTP_PORT%
    echo cd %REMOTE_PATH%
    echo lcd "%LOCAL_PATH%"
    echo put -r *
    echo close
    echo exit
) > "%SCRIPT_FILE%"

REM Run WinSCP with script
"%WINSCP_PATH%" /script="%SCRIPT_FILE%" /log="%TEMP%\winscp_upload.log"

set UPLOAD_EXIT_CODE=%errorlevel%

REM Show results
echo.
echo ========================================
if %UPLOAD_EXIT_CODE% equ 0 (
    echo SUCCESS: Files uploaded!
    echo ========================================
    echo.
    echo Your webshop is now uploading to one.com
    echo.
    echo Next steps:
    echo 1. Wait 2-5 minutes for files to fully sync
    echo 2. Visit: https://apiblockchain.io
    echo 3. If 404, clear browser cache (Ctrl+Shift+Del^)
    echo 4. Check browser console (F12^) for errors
    echo.
    echo Upload log saved to: %TEMP%\winscp_upload.log
) else (
    echo ERROR: Upload failed (Exit code: %UPLOAD_EXIT_CODE%^)
    echo ========================================
    echo.
    echo Check upload log: %TEMP%\winscp_upload.log
    echo.
    echo Common issues:
    echo - Wrong SFTP password
    echo - SFTP not enabled in one.com
    echo - Network connectivity issue
    echo.
    echo Try the manual method:
    echo 1. Log into one.com dashboard
    echo 2. File Manager
    echo 3. Upload: apiblockchain_webshop_ready_to_upload.zip
    echo 4. Extract to public_html/
)

echo.
pause
exit /b %UPLOAD_EXIT_CODE%
