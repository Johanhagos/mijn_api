# APIBlockchain Webshop - Upload Instructions

## File Ready to Upload
📦 **File**: `apiblockchain_webshop_ready_to_upload.zip` (14.7 MB)

## Steps to Deploy to one.com

### Step 1: Log in to One.com
Visit: https://one.com → Login with your credentials

### Step 2: Access File Manager
1. Go to **Dashboard** 
2. Click **Hosting** (or similar)
3. Click **Manage** next to your domain `apiblockchain.io`
4. Click **File Manager**

### Step 3: Upload Files
1. Navigate to **public_html/** (the webroot)
2. **DELETE all existing files** (backup first if needed)
3. Click **Upload** button
4. Select `apiblockchain_webshop_ready_to_upload.zip`
5. **Extract/Unzip** the uploaded file in the file manager
6. Move all files from the `webshop_for_upload` folder to root of `public_html/`

### Step 4: Verify
1. Wait 2-3 minutes for changes to propagate
2. Visit `https://apiblockchain.io` in browser
3. You should see the homepage with:
   - Navigation menu (Home, Services, etc.)
   - Contact/booking buttons
   - Footer with contact info

### What's Inside the ZIP
```
webshop_for_upload/
├── index.html              ← Main homepage
├── services.html           ← Services page
├── booking.html            ← Booking form
├── contact.html            ← Contact form
├── quotation.html          ← Quotation request
├── about.html              ← About page
├── api-config.js           ← API configuration (NEW)
├── sendmail.php            ← Form handler
├── .htaccess               ← Routing rules (IMPORTANT)
├── DEPLOYMENT_GUIDE.md     ← Full documentation
├── onewebstatic/           ← CSS, JS, fonts, styles
├── blogmedia/              ← Blog images
├── onebookingsmedia/       ← Booking images
└── onewebmedia/            ← General images
```

## API Endpoints (Already Configured)
The webshop will automatically connect to:
- **Base API**: `https://api.apiblockchain.io`
- **Checkout**: For creating payment sessions
- **Invoices**: For invoice management
- **Forms**: Handled by sendmail.php

## If Something Goes Wrong

❌ **White page / 404 error**
- Make sure ALL files are uploaded
- Check that `.htaccess` is in root of `public_html/`
- Delete browser cache (Ctrl+Shift+Del)

❌ **Images/CSS not loading**
- Ensure `/onewebstatic/` folder is uploaded completely
- Check file permissions (should be 644)

❌ **Forms not working**
- Ensure `sendmail.php` is in root
- Contact one.com support if PHP is disabled

## Next Steps
1. Upload the ZIP file
2. Extract all files to `public_html/`
3. Test the website
4. Forms should now work and connect to your API

**Need help?**
- Check browser console (F12) for errors
- Review DEPLOYMENT_GUIDE.md
- Contact: info@apiblockchain.io
