# Contact Form - Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Step 1: Replace Contact Page
Move the modern contact page into your webshop:
```bash
cd webshop
cp contact_new.html contact.html
```

Or manually:
- Old file: `webshop/contact.html`
- New file: `webshop/contact_new.html` (replaces the old one)

### Step 2: Start Your API Server
```bash
# From project root
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### Step 3: Test the Contact Form
Open contact page in browser:
- Local: `http://localhost:8000/contact`
- Public: `https://your-domain.com/contact`

### Step 4: Fill Out and Submit
Try submitting a test message. You should see:
- ✅ Success message: "Your message has been received!"
- 📄 File created: `data/contacts.json`
- 📝 Message saved with timestamp and sender IP

## 📋 What You Get

✅ **Modern Contact Form**
- Clean, professional design
- Full-width on desktop, mobile-optimized
- Blue gradient header matching your brand

✅ **Address Information**
- Office location with Google Maps link
- Phone number (clickable tel: link)
- Email (clickable mailto: link)
- Business hours display

✅ **Form Fields**
- Name (required)
- Email (required)
- Phone (optional)
- Company (optional)
- Subject (required)
- Message (required)

✅ **Validation**
- Client-side validation with user feedback
- Server-side validation for security
- Clear error messages
- Success confirmation

✅ **Data Storage**
- Messages saved to `data/contacts.json`
- Includes sender IP address
- Automatic timestamp
- Unique message ID

## 🧪 Test It

Run the automated test suite:
```bash
python test_contact_form.py
```

**Expected Output:**
```
========== CONTACT FORM API TEST SUITE ==========
Testing endpoint: http://localhost:8000/api/contact

[TEST 1] Valid Contact Form Submission
Status Code: 200
Response: {
  "success": true,
  "message": "Your message has been received! We'll get back to you within 24 hours.",
  "id": "..."
}
✅ Test PASSED: Contact message submitted successfully

[TEST 2] Invalid Email Address
Status Code: 400
✅ Test PASSED: Invalid email rejected as expected

... (more tests)

==================== TEST SUMMARY ====================
✅ PASSED: Valid Submission
✅ PASSED: Invalid Email
✅ PASSED: Short Message
✅ PASSED: Missing Fields
✅ PASSED: Optional Fields

Total: 5/5 tests passed
🎉 All tests passed!
```

## 📊 Check Your Messages

### View in JSON File
```bash
cat data/contacts.json
```

### View via Admin API
```bash
# Get admin token first
ADMIN_TOKEN="your-admin-jwt-token"

curl "http://localhost:8000/api/contact/messages?token=$ADMIN_TOKEN"
```

**Sample Response:**
```json
{
  "success": true,
  "count": 3,
  "messages": [
    {
      "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "name": "John Doe",
      "email": "john@example.com",
      "phone": "+31652824245",
      "company": "Acme Corporation",
      "subject": "Integration Request",
      "message": "We would like to integrate your blockchain payment gateway...",
      "to": "info@apiblockchain.io",
      "ip": "192.168.1.100",
      "created_at": "2025-02-14T15:30:45.123456+00:00"
    },
    ...more messages...
  ]
}
```

## 🔗 Page Navigation

The contact page includes links to:
- Home (`/`)
- Services (`/services`)
- Quotation (`/quotation`)
- Booking (`/booking`)
- About (`/about`)
- Blog (`/blog/`)
- Contact (current - `/contact`)

Update these links in `contact.html` if your URLs are different.

## 📧 Address Details Built-in

```
API Blockchain
G.A. Brederodestraat 100
1132 ST Volendam
Netherlands

Phone: +31 (0) 6 5282 4245
Email: info@apiblockchain.io
Hours: Monday-Friday, 9:00 AM - 5:00 PM CET
```

All clickable and functional:
- Phone number opens dialer on mobile
- Email opens default email client
- Address shows Google Maps

## 🎯 Next Steps (Optional)

### 1. Set Up Email Notifications
Currently messages are saved to JSON. To send emails:

```python
# In main.py, add email sending to /api/contact endpoint
import smtplib
from email.mime.text import MIMEText

# Send email when message received
msg = MIMEText(contact_dict['message'])
msg['Subject'] = f"New Contact: {contact_dict['subject']}"
msg['From'] = 'noreply@apiblockchain.io'
msg['To'] = contact_dict['to']
# ... send via SMTP
```

### 2. Create Admin Dashboard
Build a dashboard to view contact messages:
```python
@app.get("/admin/contact-messages")
async def view_contact_messages(current_user = Depends(require_admin)):
    messages = load_contacts()
    return {
        "total": len(messages),
        "messages": messages,
        "unread": len([m for m in messages if not m.get('read')])
    }
```

### 3. Add Message Search/Filter
List and search contact messages by date, sender, subject.

### 4. Mark Messages as "Read"
Track which messages have been reviewed by admin.

### 5. Export Messages
Generate CSV or PDF reports of all contact submissions.

## 📱 Mobile Testing

Make sure to test on:
- [ ] iPhone (Safari)
- [ ] Android (Chrome)
- [ ] Tablet (iPad/etc)
- [ ] Desktop (multiple browsers)

The page uses responsive design and should work on all devices.

## 🔐 Security Notes

✅ **Already Implemented:**
- Input validation (name length, email format, message length)
- XSS protection (FastAPI sanitizes JSON)
- CORS headers configured
- IP address logging
- Event audit trail

⚠️ **Consider Adding:**
- Rate limiting (prevent spam)
- CAPTCHA (anti-bot)
- Email verification (optional)
- Message encryption (for sensitive data)

## 🚀 Deploy to Production

### 1. On Your Server
```bash
git pull  # Get latest changes
pip install -r requirements.txt  # Install/update deps
# Restart your FastAPI server
```

### 2. Update Domain
If your API is on a different domain, update in `contact.html`:
```javascript
const response = await fetch('https://your-api.com/api/contact', {
    // ... rest of code
});
```

### 3. Set Up CORS
Ensure your `main.py` CORS settings allow your frontend domain:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com", "https://www.your-domain.com"],
    # ...
)
```

## 📞 Support & Debugging

**Form not submitting?**
1. Open browser DevTools (F12)
2. Go to Console tab
3. Look for error messages
4. Check Network tab - see what response comes from `/api/contact`

**Messages not being saved?**
1. Check `data/` directory exists: `ls data/`
2. Check permissions: `chmod 755 data/`
3. Check if read-only: Look for `READ_ONLY_FS` in server logs

**CORS errors?**
```
Access to XMLHttpRequest blocked by CORS policy
```
Solution: Update `allow_origins` in FastAPI CORS middleware

**Validation errors?**
Form shows red error messages. Check:
- Email has @ symbol
- Name is 2+ characters
- Subject is 3+ characters
- Message is 10+ characters

## ✨ Features Summary

| Feature | Status | Details |
|---------|--------|---------|
| Contact Form | ✅ Done | 6 fields (3 required, 3 optional) |
| Validation | ✅ Done | Client & server-side |
| Address Info | ✅ Done | Full contact details |
| Data Storage | ✅ Done | JSON file with timestamps |
| Admin API | ✅ Done | View all messages |
| Mobile Design | ✅ Done | Fully responsive |
| Maps Link | ✅ Done | Google Maps integration |
| Social Links | ✅ Done | Facebook, Twitter, LinkedIn |
| Email Notify | ⏳ Optional | Can be added |
| Dashboard | ⏳ Optional | Can be added |

---

**Need help?** See `CONTACT_FORM_GUIDE.md` for detailed documentation.
