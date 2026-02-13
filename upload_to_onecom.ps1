# SFTP Upload to One.com
$SFTP_HOST = "ssh.cruerobt5.service.one"
$SFTP_USER = "cruerobt5_ssh"
$SFTP_PASSWORD = "Nathnael1997&"
$SFTP_PORT = 22
$REMOTE_PATH = "/home/cruerobt5/public_html"
$LOCAL_PATH = "c:\Users\gebruiker\Desktop\mijn_api\webshop_for_upload"

$WINSCP_PATH = "C:\Program Files (x86)\WinSCP\WinSCP.com"

# Check if WinSCP exists
if (-not (Test-Path $WINSCP_PATH)) {
    Write-Host "WinSCP not found at default location. Checking alternative path..."
    $WINSCP_PATH = "C:\Program Files\WinSCP\WinSCP.com"
    if (-not (Test-Path $WINSCP_PATH)) {
        Write-Host "ERROR: WinSCP not installed. Please install from https://winscp.net/download"
        exit 1
    }
}

Write-Host "Creating WinSCP script..."
$SCRIPT_FILE = "$env:TEMP\winscp_upload.txt"
@"
open sftp://${SFTP_USER}:${SFTP_PASSWORD}@${SFTP_HOST}:${SFTP_PORT}
cd $REMOTE_PATH
lcd "$LOCAL_PATH"
put index.html
close
exit
"@ | Out-File -FilePath $SCRIPT_FILE -Encoding ASCII

Write-Host "Starting upload to one.com..."
& $WINSCP_PATH /script="$SCRIPT_FILE" /log="$env:TEMP\winscp_upload.log"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================"
    Write-Host "SUCCESS! index.html uploaded to one.com"
    Write-Host "========================================"
    Write-Host ""
    Write-Host "Check your website: https://apiblockchain.io"
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "ERROR during upload. Check the log:"
    Write-Host "$env:TEMP\winscp_upload.log"
    Get-Content "$env:TEMP\winscp_upload.log" -Tail 20
}

# Cleanup
Remove-Item $SCRIPT_FILE -ErrorAction SilentlyContinue
