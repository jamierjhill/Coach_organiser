# Email Configuration Guide

## Overview
The Tennis Match Organizer contact form can send real emails when properly configured. This guide shows you how to set up email functionality.

## Quick Setup (Gmail)

### 1. Enable App Passwords in Gmail
1. Go to [Google Account Settings](https://myaccount.google.com/)
2. Select "Security" → "2-Step Verification" (enable if not already)
3. Select "App passwords"
4. Generate an app password for "Mail"
5. Save the 16-character password

### 2. Set Environment Variables

Create a `.env` file in your project directory:

```bash
# Gmail SMTP Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your.email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
FROM_EMAIL=your.email@gmail.com
TO_EMAIL=jamierjhill@gmail.com

# Optional admin key for testing
ADMIN_KEY=your-secret-admin-key
```

### 3. Alternative Email Providers

**Outlook/Hotmail:**
```bash
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USERNAME=your.email@outlook.com
SMTP_PASSWORD=your-password
```

**Yahoo Mail:**
```bash
SMTP_SERVER=smtp.mail.yahoo.com
SMTP_PORT=587
SMTP_USERNAME=your.email@yahoo.com
SMTP_PASSWORD=your-app-password
```

**Custom SMTP:**
```bash
SMTP_SERVER=mail.yourdomain.com
SMTP_PORT=587
SMTP_USERNAME=contact@yourdomain.com
SMTP_PASSWORD=your-password
```

## Testing Email Configuration

### 1. Test SMTP Connection
Visit: `http://localhost:5000/admin/email-test?admin_key=your-secret-admin-key`

This will show:
- Whether email is configured
- SMTP connection test result
- Current email settings

### 2. Send Test Email
```bash
curl -X POST http://localhost:5000/admin/test-email \
  -d "admin_key=your-secret-admin-key"
```

### 3. Test Contact Form
1. Go to `/contact`
2. Fill out the form
3. Submit and check if you receive the email

## Email Features

### What Happens When Someone Submits the Contact Form:

1. **Main Email to You:**
   - Sent to `TO_EMAIL` (jamierjhill@gmail.com)
   - Contains sender's details and message
   - Subject categorized by type (Bug Report, Feature Request, etc.)

2. **Auto-Reply to Sender:**
   - Confirms message received
   - Provides estimated response time
   - Includes helpful information

3. **Logging:**
   - All email attempts logged to `email.log`
   - Success/failure tracking
   - Security event logging

## Email Template Customization

The emails use these templates:

### Main Email Format:
```
[Tennis Match Organizer] 🐛 Bug Report from John Doe

📧 CONTACT DETAILS
Name: John Doe
Email: john@example.com
Subject: Bug Report
Timestamp: 2025-08-15 10:30:00

💬 MESSAGE
I found a bug when organizing matches...
```

### Auto-Reply Format:
```
Hi John,

Thank you for reaching out about Tennis Match Organizer!

We've received your message and will get back to you within 24-48 hours.

[Additional helpful information]
```

## Troubleshooting

### Email Not Sending

1. **Check Configuration:**
   ```bash
   # Verify environment variables are set
   echo $SMTP_USERNAME
   echo $SMTP_SERVER
   ```

2. **Check Logs:**
   ```bash
   tail -f email.log
   tail -f security.log
   ```

3. **Common Issues:**
   - Gmail: Need app password, not regular password
   - 2FA: Must be enabled for app passwords
   - Firewall: Port 587 must be open
   - Antivirus: May block SMTP connections

### Error Messages

**"Email service not configured"**
- Missing environment variables
- Check `.env` file exists and is loaded

**"Authentication failed"**
- Wrong username/password
- Need app password for Gmail
- 2FA not enabled

**"SMTP error"**
- Wrong server/port settings
- Network connectivity issues
- Firewall blocking connection

## Production Deployment

### Environment Variables in Production:
```bash
export SMTP_SERVER=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USERNAME=your.email@gmail.com
export SMTP_PASSWORD=your-app-password
export FROM_EMAIL=noreply@yourdomain.com
export TO_EMAIL=jamierjhill@gmail.com
export ADMIN_KEY=secure-random-key
```

### Security Best Practices:
- Use app passwords, never regular passwords
- Keep credentials in environment variables, not code
- Use secure admin keys in production
- Monitor email logs for abuse
- Set up rate limiting (already implemented)

### Alternative Solutions:
- **SendGrid**: Professional email service
- **Mailgun**: Transactional email API  
- **Amazon SES**: AWS email service
- **Postmark**: Reliable email delivery

## Monitoring

### Email Logs:
```bash
# Watch email activity
tail -f email.log

# Check for errors
grep "ERROR" email.log

# Monitor contact form submissions
grep "Contact email sent" security.log
```

### Email Delivery:
- Check spam folders
- Monitor bounce rates
- Track delivery confirmations
- Set up email alerts for failures

## Support

If you encounter issues:
1. Check the logs first
2. Verify environment variables
3. Test SMTP connection
4. Check firewall/antivirus settings
5. Try different email provider

The email functionality is designed to be robust - if email fails, the contact form still works and logs the message for manual follow-up.