# APIBlockchain Webshop - SFTP Upload Script for one.com
# Uses your SFTP credentials to upload webshop files securely
#
# Your one.com SFTP Details:
# Host: ssh.cruerobt5.service.one
# Username: cruerobt5_ssh
# Port: 22
#
# Usage: .\upload_webshop_sftp.ps1 -SftpPassword "your_sftp_password"

param(
    [Parameter(Mandatory=$true)]
    [string]$SftpPassword,
    [string]$SftpHost = "ssh.cruerobt5.service.one",
    [string]$SftpUser = "cruerobt5_ssh",
    [int]$SftpPort = 22,
    [string]$RemotePath = "/home/cruerobt5/public_html",
    [string]$LocalPath = "c:\Users\gebruiker\Desktop\mijn_api\webshop_for_upload"
)

# Colors
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Error { Write-Host $args -ForegroundColor Red }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warn { Write-Host $args -ForegroundColor Yellow }

Write-Info "=== APIBlockchain Webshop SFTP Upload ==="
Write-Info ""

# Check if files exist
if (-not (Test-Path $LocalPath)) {
    Write-Error "ERROR: Path not found: $LocalPath"
    exit 1
}

Write-Info "Local path: $LocalPath"
Write-Info "SFTP host: $SftpHost"
Write-Info "SFTP user: $SftpUser"
Write-Info "Remote path: $RemotePath"
Write-Info "Port: $SftpPort"
Write-Info ""

# Try to use WinSCP if available (most reliable)
$winscpPath = "C:\Program Files (x86)\WinSCP\WinSCP.com"
if (Test-Path $winscpPath) {
    Write-Info "Found WinSCP, using it for upload..."
    Write-Info ""
    
    # Create WinSCP script
    $script = @"
open sftp://$SftpUser`:$SftpPassword@$SftpHost`:$SftpPort
cd $RemotePath
put -r `"$LocalPath\*`"
close
exit
"@
    
    $scriptFile = [System.IO.Path]::GetTempFileName()
    Set-Content -Path $scriptFile -Value $script
    
    try {
        & $winscpPath /script="$scriptFile" /log=`"$env:TEMP\winscplog.txt`"
        Write-Success "✓ Upload completed"
        
        # Show log
        if (Test-Path "$env:TEMP\winscplog.txt") {
            Write-Info ""
            Write-Info "Upload log:"
            Get-Content "$env:TEMP\winscplog.txt" | Select-Object -Last 20
        }
    } catch {
        Write-Error "Error during upload: $_"
        exit 1
    } finally {
        Remove-Item $scriptFile -Force -ErrorAction SilentlyContinue
    }
} else {
    Write-Warn "WinSCP not found. Trying alternative SFTP method..."
    Write-Info ""
    
    # Fallback: Use Posh-SSH if available
    if (-not (Get-Module -ListAvailable -Name Posh-SSH)) {
        Write-Error "Neither WinSCP nor Posh-SSH found."
        Write-Error ""
        Write-Error "To use SFTP upload, please install WinSCP:"
        Write-Error "1. Download from: https://winscp.net/download"
        Write-Error "2. Install WinSCP"
        Write-Error "3. Run this script again"
        Write-Error ""
        Write-Error "Alternatively, use the ZIP file with One.com File Manager:"
        Write-Error "1. Log into one.com dashboard"
        Write-Error "2. File Manager"
        Write-Error "3. Upload: apiblockchain_webshop_ready_to_upload.zip"
        Write-Error "4. Extract to public_html/"
        exit 1
    }
    
    Import-Module Posh-SSH -ErrorAction Stop
    
    Write-Info "Connecting to SFTP..."
    
    $credential = New-Object System.Management.Automation.PSCredential(
        $SftpUser,
        (ConvertTo-SecureString -String $SftpPassword -AsPlainText -Force)
    )
    
    try {
        $sftpSession = New-SFTPSession -ComputerName $SftpHost -Credential $credential -Port $SftpPort -AcceptKey
        Write-Success "✓ Connected to SFTP"
        
        Write-Info ""
        Write-Info "Uploading files..."
        
        $files = Get-ChildItem -Path $LocalPath -Recurse -File
        Write-Info "Total files: $($files.Count)"
        Write-Info ""
        
        $uploadedCount = 0
        foreach ($file in $files) {
            $relativePath = $file.FullName.Substring($LocalPath.Length).TrimStart('\')
            $remoteFile = "$RemotePath/$relativePath".Replace('\', '/')
            
            Write-Host "Uploading: $relativePath... " -NoNewline
            
            try {
                Set-SFTPFile -SFTPSession $sftpSession -LocalFile $file.FullName -RemotePath $remoteFile -Force
                Write-Success "✓"
                $uploadedCount++
            } catch {
                Write-Error "✗ Failed"
            }
        }
        
        Write-Info ""
        Write-Success "Upload complete: $uploadedCount/$($files.Count) files"
        
        Remove-SFTPSession -SFTPSession $sftpSession | Out-Null
    } catch {
        Write-Error "SFTP Error: $_"
        exit 1
    }
}

Write-Info ""
Write-Info "=== Upload Finished ==="
Write-Info ""
Write-Info "Next steps:"
Write-Info "1. Visit https://apiblockchain.io in your browser"
Write-Info "2. If 404, clear cache (Ctrl+Shift+Del)"
Write-Info "3. Wait 2-5 minutes for CDN cache to clear"
Write-Info ""
Write-Success "Webshop should now be live!"
