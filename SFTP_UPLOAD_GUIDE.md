# SFTP Upload - Your one.com Credentials

## Your SFTP Details (From one.com)

```
Host:       ssh.cruerobt5.service.one
Username:   cruerobt5_ssh
Port:       22
```

## Step 1: Set Your SFTP Password

1. Log into one.com dashboard
2. Go to **Hosting** → **Manage** 
3. Click **SFTP-beheer** (SFTP Management)
4. Toggle **SFTP-toegang activeren** to **Aan** (On)
5. Click **Verzenden** (Submit)
6. Check your email for SFTP password setup instructions
7. Set your SFTP password

## Step 2: Run the Upload Script

### Option A: Using WinSCP (Easiest)
WinSCP is the easiest method - it's a graphical SFTP tool.

1. Download WinSCP: https://winscp.net/download
2. Install it
3. Run PowerShell script:
   ```powershell
   cd c:\Users\gebruiker\Desktop\mijn_api
   .\upload_webshop_sftp.ps1 -SftpPassword "your_sftp_password"
   ```
   Replace `your_sftp_password` with your actual SFTP password

4. Watch it upload all files automatically ✓

### Option B: Manual Upload with WinSCP
1. Install WinSCP
2. Open WinSCP
3. Create new site:
   - Protocol: SFTP
   - Host: `ssh.cruerobt5.service.one`
   - Port: `22`
   - Username: `cruerobt5_ssh`
   - Password: your SFTP password
4. Connect
5. Left side: Browse to `c:\Users\gebruiker\Desktop\mijn_api\webshop_for_upload`
6. Right side: Navigate to `/home/cruerobt5/public_html`
7. Drag and drop all files from left to right
8. Wait for upload to complete

### Option C: Manual Upload via One.com File Manager (No Tools Needed)
1. Log into one.com dashboard
2. Go to **Hosting** → **Manage**
3. Click **File Manager**
4. Navigate to `/home/cruerobt5/public_html/` (or just `public_html/`)
5. Delete all existing files
6. Click **Upload**
7. Select: `apiblockchain_webshop_ready_to_upload.zip`
8. Extract the ZIP in place
9. Move files from `webshop_for_upload/` folder to root

## Troubleshooting

### "SFTP connection failed"
- Verify SFTP is enabled in one.com dashboard
- Check username: `cruerobt5_ssh` (not your main username)
- Verify password is correct
- Try with WinSCP's GUI to test connection

### "Permission denied"
- Make sure you're uploading to `/home/cruerobt5/public_html/`
- Not `/home/cruerobt5/` directly
- Check file permissions after upload

### Upload hangs or times out
- Try uploading smaller batches
- Use WinSCP instead of PowerShell script
- Check your internet connection

---

## Which Method to Use?

| Method | Ease | Speed | Requires |
|--------|------|-------|----------|
| WinSCP GUI | ⭐⭐⭐ | ⭐⭐ | WinSCP install |
| PowerShell Script | ⭐⭐ | ⭐⭐⭐ | WinSCP install |
| One.com File Manager | ⭐⭐⭐ | ⭐ | Browser only |

**Recommendation**: Use WinSCP GUI - it's most reliable and visual.

---

## After Upload

1. Visit `https://apiblockchain.io`
2. Should see your webshop homepage
3. If 404, clear browser cache and wait 5 minutes
4. Forms should work and connect to API

**Done!** 🎉
