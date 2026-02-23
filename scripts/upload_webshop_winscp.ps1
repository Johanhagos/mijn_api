# WinSCP Upload Script for APIBlockchain Webshop
# This script uploads all webshop files to One.com via SFTP

# ===== CONFIGURATION =====
# Update these with your One.com credentials
$ftpHost = "ftp.apiblockchain.io"           # or your One.com FTP server
$ftpUsername = "your_username_here"          # Your One.com username
$ftpPassword = "your_password_here"          # Your One.com password
$ftpPort = 22                                 # SFTP port (22) or FTP (21)
$localWebshopPath = "C:\Users\gebruiker\Desktop\mijn_api\webshop"
$remoteWebshopPath = "/public_html"          # or "/" depending on One.com setup

# ===== WINSCP SCRIPT =====
$winscpScript = @"
option batch abort
option confirm off
open sftp://$($ftpUsername):$($ftpPassword)@$($ftpHost):$($ftpPort)
synchronize remote "$($localWebshopPath)" "$($remoteWebshopPath)"
close
exit
"@

# Save script to temp file
$scriptPath = "$env:TEMP\winscp_upload.txt"
$winscpScript | Out-File -FilePath $scriptPath -Encoding ASCII

# Run WinSCP with script
Write-Host "Starting WinSCP upload to One.com..."
Write-Host "Host: $ftpHost"
Write-Host "Local: $localWebshopPath"
Write-Host "Remote: $remoteWebshopPath"
Write-Host ""

# Execute WinSCP
& "C:\Program Files (x86)\WinSCP\WinSCP.com" /script=$scriptPath

# Check result
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Upload completed successfully!" -ForegroundColor Green
} else {
    Write-Host "❌ Upload failed with exit code: $LASTEXITCODE" -ForegroundColor Red
    Write-Host "Check your credentials and try again."
}

# Cleanup
Remove-Item $scriptPath -Force
