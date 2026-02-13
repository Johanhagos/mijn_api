# Quick FTP Upload - 3 Steps

## Step 1: Get Your FTP Credentials from One.com

1. Log in to one.com dashboard
2. Go to **Hosting** → **Manage** (next to apiblockchain.io)
3. Look for **FTP Access** section
4. You'll see:
   - **FTP Username** (e.g., `u123456789`)
   - **FTP Password** (the password you set)
   - **FTP Host** (e.g., `ftp.apiblockchain.io` or `ftp1.one.com`)

## Step 2: Edit the Upload Script

1. Open this file in Notepad: `upload_webshop_to_onecom.ps1`
2. Change the first 4 lines to match YOUR credentials:

```powershell
[string]$FtpUser = "your_ftp_username",      # ← Change this
[string]$FtpPass = "your_ftp_password",      # ← Change this
[string]$FtpHost = "your_ftp_host",          # ← Change this
[string]$FtpPath = "/public_html/",          # ← Usually stays the same
```

Example (after editing):
```powershell
[string]$FtpUser = "u123456789",
[string]$FtpPass = "MyPassword123",
[string]$FtpHost = "ftp.apiblockchain.io",
[string]$FtpPath = "/public_html/",
```

3. Save the file

## Step 3: Run the Script

1. Open **PowerShell** as Administrator
2. Navigate to the mijn_api folder:
   ```powershell
   cd c:\Users\gebruiker\Desktop\mijn_api
   ```
3. Run the script:
   ```powershell
   .\upload_webshop_to_onecom.ps1
   ```
4. Watch it upload all files (you'll see ✓ marks for each file)

## What Happens Next?

- ✅ All webshop files uploaded to one.com
- ✅ Your website loads at https://apiblockchain.io
- ✅ Forms connect to API at https://api.apiblockchain.io
- ⏳ Wait 2-5 minutes for DNS/CDN cache to clear

## Troubleshooting

**"Failed to connect to FTP"**
- Check FTP credentials are correct
- Verify FTP host is right (usually `ftp1.one.com` or `ftp.apiblockchain.io`)
- Make sure FTP is enabled in one.com settings

**"404 Not Found" after upload**
- Clear browser cache: Ctrl+Shift+Del
- Delete all cookies for apiblockchain.io
- Wait 5 minutes
- Try in an incognito/private window

**Images not loading**
- Scroll through upload output
- Check if `/onewebstatic/` folder uploaded (it's critical)
- Re-run the script if any files failed

## Alternative: Manual Upload via One.com File Manager

If FTP script doesn't work:
1. Log in to one.com
2. File Manager
3. Upload ZIP file: `apiblockchain_webshop_ready_to_upload.zip`
4. Extract ZIP
5. Move files from webshop_for_upload/ to root

---

**Need help?** Check browser console (F12) for errors, or contact: info@apiblockchain.io
