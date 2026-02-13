$password = "Johanahagos1992&"
$username = "cruerobt5_ssh"
$hostname = "ssh.cruerobt5.service.one"
$localFile = "c:/Users/gebruiker/Desktop/mijn_api/webshop_for_upload/index.html"
$remotePath = "/home/cruerobt5/public_html/index.html"

# Create expect-like script for SFTP
$commands = @"
cd public_html
put $localFile
ls -la index.html
bye
"@

$commands | Out-File -FilePath "c:\Users\gebruiker\Desktop\mijn_api\sftp_batch.txt" -Encoding ASCII

Write-Host "Connecting to $hostname..." -ForegroundColor Cyan
Write-Host "Username: $username" -ForegroundColor Yellow
Write-Host "You will need to enter the password: $password" -ForegroundColor Green
Write-Host ""

# Use plink if available (comes with PuTTY)
if (Test-Path "C:\Program Files\PuTTY\psftp.exe") {
    Write-Host "Using PSFTP..." -ForegroundColor Cyan
    echo $password | & "C:\Program Files\PuTTY\psftp.exe" -P 22 -b "c:\Users\gebruiker\Desktop\mijn_api\sftp_batch.txt" "$username@$hostname"
} else {
    Write-Host "PSFTP not found. Please enter password manually when prompted:" -ForegroundColor Yellow
    sftp -P 22 -b "c:\Users\gebruiker\Desktop\mijn_api\sftp_batch.txt" "$username@$hostname"
}
