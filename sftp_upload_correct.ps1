# SFTP Upload to One.com with correct password
$SFTP_HOST = "ssh.cruerobt5.service.one"
$SFTP_USER = "cruerobt5_ssh"
$SFTP_PASSWORD = "Johanahagos1992&"
$SFTP_PORT = 22
$LOCAL_FILE = "c:\Users\gebruiker\Desktop\mijn_api\webshop_for_upload\index.html"
$REMOTE_PATH = "/home/cruerobt5/public_html"

Write-Host "Uploading index.html to One.com via SFTP..."

# Create SFTP script
$SCRIPT_FILE = "$env:TEMP\sftp_upload.txt"
@"
open sftp://${SFTP_USER}:${SFTP_PASSWORD}@${SFTP_HOST}:${SFTP_PORT}
cd $REMOTE_PATH
put "$LOCAL_FILE"
close
exit
"@ | Out-File -FilePath $SCRIPT_FILE -Encoding ASCII

# Try to find and use WinSCP
$winscpPaths = @(
    "C:\Program Files (x86)\WinSCP\WinSCP.com",
    "C:\Program Files\WinSCP\WinSCP.com",
    "$env:LOCALAPPDATA\Programs\WinSCP\WinSCP.com"
)

$WINSCP_PATH = $null
foreach ($path in $winscpPaths) {
    if (Test-Path $path) {
        $WINSCP_PATH = $path
        break
    }
}

if ($WINSCP_PATH) {
    Write-Host "Using WinSCP at: $WINSCP_PATH"
    & $WINSCP_PATH /script="$SCRIPT_FILE" /log="$env:TEMP\winscp_upload.log"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "========================================"
        Write-Host "SUCCESS! File uploaded to One.com"
        Write-Host "========================================"
        Write-Host ""
        Write-Host "Visit: https://apiblockchain.io"
        Write-Host "Press Ctrl+Shift+Del to clear cache if needed"
    } else {
        Write-Host ""
        Write-Host "Upload failed. Check log:"
        if (Test-Path "$env:TEMP\winscp_upload.log") {
            Get-Content "$env:TEMP\winscp_upload.log" -Tail 20
        }
    }
} else {
    Write-Host ""
    Write-Host "WinSCP not found. Please use One.com File Manager:"
    Write-Host "1. Go to https://www.one.com/admin/"
    Write-Host "2. Click 'File Manager'"
    Write-Host "3. Navigate to public_html"
    Write-Host "4. Upload: $LOCAL_FILE"
}

Remove-Item $SCRIPT_FILE -ErrorAction SilentlyContinue
