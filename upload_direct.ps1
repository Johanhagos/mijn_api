# Direct SFTP upload using PowerShell and PSFTP
$ErrorActionPreference = "Stop"

$SFTP_HOST = "ssh.cruerobt5.service.one"
$SFTP_USER = "cruerobt5_ssh"  
$SFTP_PASSWORD = "Nathnael1997&"
$SFTP_PORT = 22
$REMOTE_PATH = "/home/cruerobt5/public_html/index.html"
$LOCAL_FILE = "c:\Users\gebruiker\Desktop\mijn_api\webshop_for_upload\index.html"

Write-Host "Uploading index.html to One.com via SFTP..."

# Create batch file for PSFTP
$batchFile = "$env:TEMP\sftp_commands.txt"
@"
cd /home/cruerobt5/public_html
put "$LOCAL_FILE" index.html
quit
"@ | Out-File -FilePath $batchFile -Encoding ASCII

# Try using psftp if available (from PuTTY)
$psftpPath = "C:\Program Files\PuTTY\psftp.exe"
if (Test-Path $psftpPath) {
    Write-Host "Using PSFTP..."
    echo y | & $psftpPath -pw "$SFTP_PASSWORD" -P $SFTP_PORT -b "$batchFile" "${SFTP_USER}@${SFTP_HOST}"
} else {
    # Fallback: Use WinSCP portable
    Write-Host "Downloading WinSCP portable..."
    $winscpZip = "$env:TEMP\winscp.zip"
    $winscpDir = "$env:TEMP\winscp"
    
    Invoke-WebRequest -Uri "https://winscp.net/download/WinSCP-6.3-Portable.zip" -OutFile $winscpZip -UseBasicParsing
    
    if (Test-Path $winscpDir) { Remove-Item $winscpDir -Recurse -Force }
    Expand-Archive -Path $winscpZip -DestinationPath $winscpDir
    
    $winscpCom = Get-ChildItem -Path $winscpDir -Filter "WinSCP.com" -Recurse | Select-Object -First 1
    
    if ($winscpCom) {
        Write-Host "Using WinSCP portable..."
        $scriptFile = "$env:TEMP\winscp_script.txt"
        @"
open sftp://${SFTP_USER}:${SFTP_PASSWORD}@${SFTP_HOST}:${SFTP_PORT}
cd /home/cruerobt5/public_html
put "$LOCAL_FILE"
close
exit
"@ | Out-File -FilePath $scriptFile -Encoding ASCII
        
        & $winscpCom.FullName /script="$scriptFile"
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "`n========================================"
            Write-Host "SUCCESS! File uploaded to one.com"
            Write-Host "========================================`n"
            Write-Host "Visit: https://apiblockchain.io"
            Write-Host "Clear cache if needed (Ctrl+Shift+Del)`n"
        }
    }
}
