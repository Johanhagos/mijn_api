@echo off
REM Quick setup - just enter your SFTP password once
REM
REM This script will:
REM 1. Ask for your SFTP password
REM 2. Download WinSCP if needed
REM 3. Upload everything automatically

setlocal enabledelayedexpansion

echo.
echo ========================================
echo APIBlockchain - One.com Upload Setup
echo ========================================
echo.
echo Your SFTP Details:
echo   Host: ssh.cruerobt5.service.one
echo   Username: cruerobt5_ssh
echo.

REM Prompt for password
set /p SFTP_PASSWORD="Enter your SFTP password: "

if "%SFTP_PASSWORD%"=="" (
    echo ERROR: Password cannot be empty
    pause
    exit /b 1
)

REM Create the main upload script with password
(
    echo @echo off
    echo set SFTP_PASSWORD=%SFTP_PASSWORD%
    echo set SFTP_HOST=ssh.cruerobt5.service.one
    echo set SFTP_USER=cruerobt5_ssh
    echo set SFTP_PORT=22
    echo set REMOTE_PATH=/home/cruerobt5/public_html
    echo set LOCAL_PATH=c:\Users\gebruiker\Desktop\mijn_api\webshop_for_upload
    echo.
    echo net session ^>nul 2^>^&1
    echo if %%errorLevel%% neq 0 (
    echo     echo ERROR: Run as Administrator
    echo     pause
    echo     exit /b 1
    echo ^)
    echo.
    echo if not exist "%%LOCAL_PATH%%" (
    echo     echo ERROR: Path not found: %%LOCAL_PATH%%
    echo     pause
    echo     exit /b 1
    echo ^)
    echo.
    echo set WINSCP_PATH=C:\Program Files (x86)\WinSCP\WinSCP.com
    echo if not exist "%%WINSCP_PATH%%" (
    echo     echo Downloading WinSCP...
    echo     set TEMP_DIR=%%TEMP%%\winscp_install
    echo     if not exist "%%TEMP_DIR%%" mkdir "%%TEMP_DIR%%"
    echo     powershell -Command "$ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri 'https://winscp.net/download/WinSCP-6.3-Setup.exe' -OutFile '%%TEMP_DIR%%\WinSCP-Setup.exe'"
    echo     if errorlevel 1 (
    echo         echo Failed to download WinSCP
    echo         echo Download manually: https://winscp.net/download
    echo         pause
    echo         exit /b 1
    echo     ^)
    echo     echo Installing WinSCP...
    echo     "%%TEMP_DIR%%\WinSCP-Setup.exe" /S
    echo     timeout /t 10 /nobreak
    echo ^)
    echo.
    echo echo Starting upload to one.com...
    echo echo.
    echo.
    echo set SCRIPT_FILE=%%TEMP%%\winscp_upload.txt
    echo (
    echo     echo open sftp://%%SFTP_USER%%:%%SFTP_PASSWORD%%@%%SFTP_HOST%%:%%SFTP_PORT%%
    echo     echo cd %%REMOTE_PATH%%
    echo     echo lcd "%%LOCAL_PATH%%"
    echo     echo put -r *
    echo     echo close
    echo     echo exit
    echo ^) ^> "%%SCRIPT_FILE%%"
    echo.
    echo "%%WINSCP_PATH%%" /script="%%SCRIPT_FILE%%" /log="%%TEMP%%\winscp_upload.log"
    echo.
    echo if %%errorlevel%% equ 0 (
    echo     echo.
    echo     echo ========================================
    echo     echo SUCCESS! Webshop uploaded to one.com
    echo     echo ========================================
    echo     echo.
    echo     echo Check your website: https://apiblockchain.io
    echo     echo.
    echo     echo If you see 404:
    echo     echo - Clear browser cache (Ctrl+Shift+Del^)
    echo     echo - Wait 5 minutes for CDN cache to clear
    echo     echo.
    echo ^) else (
    echo     echo.
    echo     echo ERROR during upload. Check the log:
    echo     echo %%TEMP%%\winscp_upload.log
    echo ^)
    echo.
    echo pause
) > "%TEMP%\webshop_upload_with_password.bat"

REM Run with admin privileges
powershell -Command "Start-Process '%TEMP%\webshop_upload_with_password.bat' -Verb runAs"

echo.
echo Setup script launched. Follow the prompts to complete upload.
echo.
pause
