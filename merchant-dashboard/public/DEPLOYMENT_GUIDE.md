# APIBlockchain Webshop - Deployment Guide

## Quick Start
This is a One.com-hosted webshop that connects to the APIBlockchain API.

### What You Have
- **Frontend**: Static HTML/CSS/JS site hosted on one.com
- **Backend**: FastAPI service at `https://api.apiblockchain.io` (Running on Railway)
- **API Configuration**: `api-config.js` with endpoint definitions

### How to Deploy

#### Method 1: One.com File Manager (Easiest)
1. Log in to one.com dashboard
2. Go to **File Manager**
3. Navigate to your webroot (usually `public_html/`)
4. **Delete all existing files** in the webroot
5. **Upload all files from this folder** to the webroot
6. The site should load at `https://apiblockchain.io`

#### Method 2: FTP Upload
1. Connect via FTP using one.com credentials
2. Navigate to `public_html/` folder
3. Delete all existing files
4. Upload all files from this folder
5. Verify at `https://apiblockchain.io`

### API Integration
The webshop uses `api-config.js` to communicate with the backend:
- **Base URL**: `https://api.apiblockchain.io`
- **Checkout**: `POST /checkout` → creates a session
- **Sessions**: `GET /sessions/{id}` → retrieves session details
- **Forms**: `sendmail.php` handles contact/booking forms

### Key Files
- `index.html` - Homepage
- `services.html` - Services page
- `booking.html` - Booking form
- `quotation.html` - Quotation request
- `contact.html` - Contact form
- `sendmail.php` - Form handler (one.com built-in)
- `api-config.js` - API configuration (NEW)
- `.htaccess` - URL routing and SSL enforcement
- `/onewebstatic/` - CSS, JS, and assets (CRITICAL - must upload)
- `/blogmedia/` - Blog images

### What's Different?
✅ Added `api-config.js` for centralized API configuration
✅ CORS is enabled on backend for `https://apiblockchain.io`
✅ All form submissions route through One.com's sendmail.php
✅ API calls use proper error handling

### Testing
After deployment:
1. Visit `https://apiblockchain.io` - should load homepage
2. Click "Contact us" → form should work
3. Click "Book a consultation" → booking form should work
4. Check browser console (F12) for any errors

### Troubleshooting

**404 errors on images/CSS**
- Make sure `/onewebstatic/` folder is uploaded

**Forms not working**
- sendmail.php requires POST to work (check one.com settings)
- Contact one.com support if PHP execution is disabled

**API calls failing**
- Check browser console for errors
- Ensure `api-config.js` is loaded
- Verify `https://api.apiblockchain.io` is accessible

### Support
- API docs: `https://api.apiblockchain.io/docs`
- Dashboard: `https://dashboard.apiblockchain.io`
- Contact: info@apiblockchain.io or +31652824245
