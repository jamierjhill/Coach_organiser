#!/usr/bin/env python3
"""
Send a test email to verify everything works
"""
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def send_test_email():
    """Send a test email"""
    try:
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        from email_service import send_contact_message
        
        print("Sending test email...")
        
        # Create test contact data
        test_data = {
            'contact_name': 'Email Configuration Test',
            'contact_email': 'jamierjhill@gmail.com',
            'contact_subject': 'other',
            'contact_message': '''This is a test email from the Tennis Match Organizer contact form.

If you receive this email, the email configuration is working correctly!

Test details:
- SMTP server: Gmail
- Contact form: Functional
- Auto-reply: Should also be sent

The contact form is now ready to receive real messages.'''
        }
        
        # Send email (with auto-reply)
        success, message = send_contact_message(test_data, send_auto_reply=True)
        
        if success:
            print("SUCCESS: Test email sent successfully!")
            print()
            print("Check your inbox at jamierjhill@gmail.com for:")
            print("1. Main test email (from the contact form)")
            print("2. Auto-reply email (confirmation to sender)")
            print()
            print("The contact form is now fully functional!")
        else:
            print(f"ERROR: Test email failed - {message}")
            print("Check the email.log file for more details")
        
        return success
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    send_test_email()