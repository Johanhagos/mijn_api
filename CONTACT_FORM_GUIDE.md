# Contact Form Implementation - Complete Guide

## Overview
A modern, professional contact form has been created to handle customer inquiries with both frontend and backend components.

## 📂 Files Created/Modified

### Frontend Files
- **`webshop/contact_new.html`** - New clean, modern contact page
  - Professional design with gradient header
  - Responsive layout (desktop & mobile)
  - Form validation on client-side
  - Office information section with maps link
  - Social media integration
  - Success/error message handling

### Backend Files
- **`main.py`** - Updated with contact handling
  - New `ContactMessage` Pydantic model (line ~490)
  - New `CONTACTS_FILE` constant (line ~272)
  - New helper functions: `_ensure_contacts_file()`, `load_contacts()`, `save_contact()`
  - New endpoint: `POST /api/contact` (line ~4955)
  - New endpoint: `GET /api/contact/messages` (admin only, line ~5020)

- **`test_contact_form.py`** - Complete test suite
  - Tests valid submissions
  - Tests validation (email, message length, required fields)
  - Tests edge cases and optional fields

## 🔧 API Endpoints

### POST /api/contact
Submits a new contact message.

**Request Body:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "+31652824245",           // Optional
  "company": "Acme Corp",            // Optional
  "subject": "Integration Request",
  "message": "Your message here...",
  "to": "info@apiblockchain.io"     // Optional, defaults to info@apiblockchain.io
}
```

**Response (Success - 200):**
```json
{
  "success": true,
  "message": "Your message has been received! We'll get back to you within 24 hours.",
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
}
```

**Response (Validation Error - 400):**
```json
{
  "success": false,
  "error": "Message must be at least 10 characters"
}
```

### GET /api/contact/messages
Retrieves all contact messages (admin only).

**Authentication:** Requires admin JWT token as query parameter
```
GET /api/contact/messages?token=<admin_jwt_token>
```

**Response:**
```json
{
  "success": true,
  "count": 5,
  "messages": [
    {
      "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "name": "John Doe",
      "email": "john@example.com",
      "phone": "+31652824245",
      "company": "Acme Corp",
      "subject": "Integration Request",
      "message": "Your message here...",
      "to": "info@apiblockchain.io",
      "ip": "192.168.1.1",
      "created_at": "2025-02-14T10:30:45.123456+00:00"
    }
  ]
}
```

## ✅ Validation Rules

| Field | Required | Min Length | Validation |
|-------|----------|-----------|------------|
| name | Yes | 2 chars | Text only |
| email | Yes | - | Valid email format |
| phone | No | - | Phone format |
| company | No | - | Text only |
| subject | Yes | 3 chars | Text only |
| message | Yes | 10 chars | Text only |

## 📊 Data Storage

Contact messages are stored in `data/contacts.json`:
```json
[
  {
    "id": "uuid-here",
    "name": "Sender Name",
    "email": "sender@email.com",
    "phone": "",
    "company": "",
    "subject": "Message Subject",
    "message": "Full message content",
    "to": "info@apiblockchain.io",
    "ip": "192.168.1.1",
    "created_at": "2025-02-14T10:30:45.123456+00:00"
  }
]
```

## 🧪 Testing

Run the test suite:
```bash
python test_contact_form.py
```

The test suite includes:
1. ✅ Valid contact form submission
2. ✅ Invalid email rejection
3. ✅ Short message rejection
4. ✅ Missing required fields rejection
5. ✅ Optional fields handling

## 🚀 Deployment

### Frontend Deployment
1. Replace old `webshop/contact.html` with `webshop/contact_new.html`
2. Or rename: `mv webshop/contact_new.html webshop/contact.html`
3. Update navigation links if needed
4. Ensure API endpoint URL is correct in JavaScript (currently `/api/contact`)

### Backend Deployment
1. The contact functionality is already integrated into `main.py`
2. No additional dependencies required (uses built-in FastAPI, Pydantic)
3. Ensure `data/` directory is writable
4. Set up proper CORS headers if frontend is on different domain

## 📝 Address Information

**Office Address:**
- API Blockchain
- G.A. Brederodestraat 100
- 1132 ST Volendam
- Netherlands

**Contact Details:**
- Phone: +31 (0) 6 5282 4245
- Email: info@apiblockchain.io
- Hours: Monday-Friday, 9:00 AM - 5:00 PM CET

**Map Location:** 52.4615° N, 5.0670° E

## 🔒 Security Features

1. **Input Validation**: All fields validated server-side
2. **IP Logging**: Submitter IP address recorded
3. **Event Logging**: All submissions logged via `log_event()`
4. **CORS Protected**: Follow FastAPI CORS configuration
5. **Rate Limiting**: Can add slowapi rate limits if needed
6. **Email Validation**: RFC-compliant email format check

## 🔗 Frontend Integration

The HTML form posts to `/api/contact` endpoint. The JavaScript includes:

```javascript
const response = await fetch('/api/contact', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify(data)
});
```

## 📱 Mobile Responsive

- Header adapts to mobile screens
- Form switches to single column on tablets/phones
- Touch-friendly buttons and inputs
- Responsive navigation menu
- Maps link works on all devices

## 🎨 Design Features

- Clean, professional layout
- Gradient blue header (0066cc primary color)
- Two-column layout on desktop, single on mobile
- Smooth transitions and hover effects
- Success/error message alerts
- Social media links (Facebook, Twitter, LinkedIn)
- Google Maps integration link

## 🔄 Email Integration

Currently messages are saved to `contacts.json`. To enable email notifications:

1. **Option A: Use sendmail.php**
   - Configure sendmail.php in webshop directory
   - Create a webhook to send emails from contact list

2. **Option B: Use SMTP**
   - Add smtp configuration to `main.py`
   - Configure `SMTP_SERVER`, `SMTP_PORT`, `EMAIL_FROM`

3. **Option C: Use External Service**
   - Integrate with SendGrid, Mailgun, or AWS SES
   - Call API from `/api/contact` endpoint

## 📋 Checklist for Production

- [ ] Replace `contact.html` with `contact_new.html`
- [ ] Test form submission on live server
- [ ] Verify `data/contacts.json` is created
- [ ] Check messages appear in contacts file
- [ ] Configure email notification service
- [ ] Set up admin dashboard to view messages
- [ ] Add rate limiting to contact endpoint
- [ ] Monitor CORS issues on production domain
- [ ] Test on mobile devices
- [ ] Update navigation links if using new URLs

## 🆘 Troubleshooting

**Issue: Form submission returns 500 error**
- Check `data/` directory permissions
- Review `uvicorn.err` log file
- Verify endpoint is `/api/contact` not `/contact`

**Issue: CORS errors in browser console**
- Verify CORS middleware in `main.py`
- Check frontend domain matches CORS allowed origins
- Use full URL for fetch if testing across domains

**Issue: Messages not being saved**
- Check `data/` directory exists and is writable
- Verify no read-only filesystem (`READ_ONLY_FS` flag)
- Check `contacts.json` file permissions

**Issue: Mobile form looks broken**
- Check viewport meta tag is present
- Verify CSS media queries are working
- Test in different mobile browsers

## 📞 Support

For questions about the contact form implementation:
1. Review this documentation
2. Check test cases in `test_contact_form.py`
3. Review API endpoint code in `main.py` (lines 4955-5070)
4. Check browser console for JavaScript errors
5. Review server logs in `uvicorn.err`
