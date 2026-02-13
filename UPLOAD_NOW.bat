@echo off
REM APIBlockchain - Ultimate One-Click Upload
REM No config needed - just run and enter password once
REM Everything else is automatic

setlocal enabledelayedexpansion
cls

echo.
echo ╔════════════════════════════════════════╗
echo ║  APIBlockchain Webshop Upload Tool     ║
echo ║  One-Click to Launch Your Website      ║
echo ╚════════════════════════════════════════╝
echo.

REM Check admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ⚠ This needs Administrator rights
    echo.
    echo Right-click this file and select "Run as Administrator"
    echo.
    pause
    exit /b 1
)

REM Get password securely
set /p SFTP_PASSWORD="Enter your SFTP password and press Enter: "

if "%SFTP_PASSWORD%"=="" (
    echo.
    echo ✗ Password required
    pause
    exit /b 1
)

echo.
echo ✓ Password received
echo.
echo Checking files...

REM Validate files exist
set LOCAL_PATH=c:\Users\gebruiker\Desktop\mijn_api\webshop_for_upload
if not exist "%LOCAL_PATH%" (
    echo ✗ ERROR: Webshop files not found
    echo Expected: %LOCAL_PATH%
    pause
    exit /b 1
)

echo ✓ Webshop files found
echo.
echo Checking WinSCP...

REM Check WinSCP
set WINSCP_PATH=C:\Program Files (x86)\WinSCP\WinSCP.com
if not exist "%WINSCP_PATH%" (
    echo ✓ Need to install WinSCP (one-time)
    echo.
    echo Downloading (may take 1-2 minutes)...
    
    set TEMP_DIR=%TEMP%\winscp_install
    if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"
    
    powershell -NoProfile -Command ^
        "$ProgressPreference = 'SilentlyContinue'; ^
        Write-Host 'Downloading WinSCP...'; ^
        Invoke-WebRequest -Uri 'https://winscp.net/download/WinSCP-6.3-Setup.exe' ^
        -OutFile '%TEMP_DIR%\WinSCP-Setup.exe'; ^
        Write-Host 'Download complete'"
    
    if errorlevel 1 (
        echo.
        echo ✗ Download failed - check internet connection
        pause
        exit /b 1
    )
    
    echo Installing WinSCP (silent install)...
    "%TEMP_DIR%\WinSCP-Setup.exe" /S /D=C:\Program Files (x86)\WinSCP
    
    REM Wait for install
    timeout /t 8 /nobreak >nul
    
    if not exist "%WINSCP_PATH%" (
        echo ✗ WinSCP installation failed
        pause
        exit /b 1
    )
    
    echo ✓ WinSCP installed
) else (
    echo ✓ WinSCP already installed
)

echo.
echo ════════════════════════════════════════
echo Starting Upload to one.com...
echo ════════════════════════════════════════
echo.

REM Create upload script
set SCRIPT_FILE=%TEMP%\winscp_upload_%RANDOM%.txt
(
    echo open sftp://cruerobt5_ssh:%SFTP_PASSWORD%@ssh.cruerobt5.service.one:22
    echo cd /home/cruerobt5/public_html
    echo lcd "%LOCAL_PATH%"
    echo put -r *
    echo close
    echo exit
) > "%SCRIPT_FILE%"

REM Run upload
"%WINSCP_PATH%" /script="%SCRIPT_FILE%" /log="%TEMP%\winscp_log_%RANDOM%.txt"

set RESULT=%errorlevel%

REM Cleanup script file
del /q "%SCRIPT_FILE%" >nul 2>&1

REM Show result
echo.
if %RESULT% equ 0 (
    cls
    echo.
    echo ╔════════════════════════════════════════╗
    echo ║  ✓ SUCCESS - Webshop Uploaded!         ║
    echo ╚════════════════════════════════════════╝
    echo.
    echo Your website is now live:
    echo   https://apiblockchain.io
    echo.
    echo Next steps:
    echo   1. Open https://apiblockchain.io in browser
    echo   2. If you see 404, clear cache (Ctrl+Shift+Del^)
    echo   3. Wait 5 minutes if domain not loading
    echo.
    echo ✓ Forms will connect to your API
    echo ✓ Dashboard at: https://dashboard.apiblockchain.io
    echo ✓ API docs at: https://api.apiblockchain.io/docs
    echo.
) else (
    cls
    echo.
    echo ╔════════════════════════════════════════╗
    echo ║  ✗ Upload Failed (Code: %RESULT%^)      ║
    echo ╚════════════════════════════════════════╝
    echo.
    echo Common issues:
    echo   1. Wrong SFTP password
    echo   2. SFTP not enabled in one.com
    echo   3. Network connection problem
    echo.
    echo Try manually:
    echo   1. Log into one.com dashboard
    echo   2. File Manager
    echo   3. Upload: apiblockchain_webshop_ready_to_upload.zip
    echo   4. Extract to public_html/
    echo.
)

echo.
pause
exit /b %RESULT%
