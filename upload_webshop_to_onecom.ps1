# APIBlockchain Webshop - FTP Upload Script
# This script uploads all webshop files to one.com via FTP
# 
# Usage: 
#   1. Edit the FTP_USER, FTP_PASS, FTP_HOST variables below with your one.com credentials
#   2. Run: .\upload_webshop_to_onecom.ps1
#   3. Wait for completion

param(
    [string]$FtpUser = "your_ftp_username",
    [string]$FtpPass = "your_ftp_password",
    [string]$FtpHost = "your_ftp_host",
    [string]$FtpPath = "/public_html/",
    [string]$LocalPath = "c:\Users\gebruiker\Desktop\mijn_api\webshop_for_upload"
)

# Colors for output
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Error { Write-Host $args -ForegroundColor Red }
function Write-Info { Write-Host $args -ForegroundColor Cyan }

Write-Info "=== APIBlockchain Webshop FTP Upload ==="
Write-Info ""

# Check if files exist
if (-not (Test-Path $LocalPath)) {
    Write-Error "ERROR: Path not found: $LocalPath"
    exit 1
}

Write-Info "Local path: $LocalPath"
Write-Info "FTP host: $FtpHost"
Write-Info "FTP path: $FtpPath"
Write-Info ""

# Create FTP credentials
$FtpUri = "ftp://$FtpHost$FtpPath"
$FtpCredential = New-Object System.Net.NetworkCredential($FtpUser, $FtpPass)

Write-Info "Connecting to $FtpHost..."

try {
    # Test connection
    $ftpRequest = [System.Net.FtpWebRequest]::Create($FtpUri)
    $ftpRequest.Credentials = $FtpCredential
    $ftpRequest.Method = [System.Net.WebRequestMethods+Ftp]::ListDirectory
    $ftpResponse = $ftpRequest.GetResponse()
    $ftpResponse.Close()
    Write-Success "✓ Connected to FTP server"
} catch {
    Write-Error "✗ Failed to connect to FTP"
    Write-Error "Error: $_"
    Write-Error ""
    Write-Error "Check your credentials:"
    Write-Error "  FTP User: $FtpUser"
    Write-Error "  FTP Host: $FtpHost"
    exit 1
}

# Get all files recursively
$files = Get-ChildItem -Path $LocalPath -Recurse -File

Write-Info "Found $($files.Count) files to upload"
Write-Info ""

$uploadedCount = 0
$failedCount = 0

# Upload each file
foreach ($file in $files) {
    $relativePath = $file.FullName.Substring($LocalPath.Length).TrimStart('\').Replace('\', '/')
    $ftpFilePath = "$FtpPath$relativePath"
    $ftpUri = "ftp://$FtpHost$ftpFilePath"
    
    # Create directory structure if needed
    $fileDir = Split-Path $relativePath -Parent
    if ($fileDir) {
        $ftpDirPath = "$FtpPath$fileDir"
        $ftpDirUri = "ftp://$FtpHost$ftpDirPath"
        
        try {
            $ftpDirRequest = [System.Net.FtpWebRequest]::Create($ftpDirUri)
            $ftpDirRequest.Credentials = $FtpCredential
            $ftpDirRequest.Method = [System.Net.WebRequestMethods+Ftp]::MakeDirectory
            $ftpDirRequest.GetResponse() | Out-Null
        } catch {
            # Directory might already exist, that's OK
        }
    }
    
    try {
        Write-Host "Uploading: $relativePath... " -NoNewline
        
        $ftpRequest = [System.Net.FtpWebRequest]::Create($ftpUri)
        $ftpRequest.Credentials = $FtpCredential
        $ftpRequest.Method = [System.Net.WebRequestMethods+Ftp]::UploadFile
        $ftpRequest.UseBinary = $true
        
        $fileStream = [System.IO.File]::OpenRead($file.FullName)
        $ftpStream = $ftpRequest.GetRequestStream()
        $fileStream.CopyTo($ftpStream)
        $fileStream.Close()
        $ftpStream.Close()
        
        $ftpResponse = $ftpRequest.GetResponse()
        $ftpResponse.Close()
        
        Write-Success "✓"
        $uploadedCount++
    } catch {
        Write-Error "✗ Failed: $_"
        $failedCount++
    }
}

Write-Info ""
Write-Info "=== Upload Complete ==="
Write-Success "Uploaded: $uploadedCount files"
if ($failedCount -gt 0) {
    Write-Error "Failed: $failedCount files"
}

Write-Info ""
Write-Info "Next steps:"
Write-Info "1. Visit https://apiblockchain.io in your browser"
Write-Info "2. If you see a 404, clear your browser cache (Ctrl+Shift+Del)"
Write-Info "3. Wait 5 minutes for DNS propagation if domain not resolving"
Write-Info ""
Write-Success "Done! Webshop should now be live."
