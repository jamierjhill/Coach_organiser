#!/usr/bin/env python3
"""
Email Setup Helper for Tennis Match Organizer
Run this script to configure email settings interactively
"""
import os
import getpass
from email_service import EmailService

def create_env_file():
    """Create .env file with email configuration"""
    print("🎾 Tennis Match Organizer - Email Setup")
    print("=" * 50)
    
    # Check if .env already exists
    if os.path.exists('.env'):
        overwrite = input("⚠️  .env file already exists. Overwrite? (y/N): ").lower()
        if overwrite != 'y':
            print("Setup cancelled.")
            return
    
    print("\n📧 Email Configuration")
    print("This will set up email sending for the contact form.")
    print("You'll need SMTP credentials (Gmail recommended for easy setup).\n")
    
    # Get email provider choice
    print("Choose email provider:")
    print("1. Gmail (recommended)")
    print("2. Outlook/Hotmail") 
    print("3. Yahoo Mail")
    print("4. Custom SMTP")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    # Set defaults based on provider
    if choice == '1':
        smtp_server = 'smtp.gmail.com'
        smtp_port = '587'
        print("\n📝 Gmail Setup:")
        print("1. Enable 2-Step Verification in your Google Account")
        print("2. Generate an App Password for 'Mail'")
        print("3. Use the 16-character app password below")
    elif choice == '2':
        smtp_server = 'smtp-mail.outlook.com'
        smtp_port = '587'
        print("\n📝 Outlook Setup:")
        print("Use your regular Outlook password")
    elif choice == '3':
        smtp_server = 'smtp.mail.yahoo.com'
        smtp_port = '587'
        print("\n📝 Yahoo Setup:")
        print("Generate an app password in Yahoo Account Security")
    else:
        smtp_server = input("SMTP Server: ").strip()
        smtp_port = input("SMTP Port (usually 587): ").strip() or '587'
    
    # Get credentials
    print("\n🔐 Email Credentials:")
    smtp_username = input("Email address: ").strip()
    smtp_password = getpass.getpass("Password (or app password): ")
    
    # Get sender/receiver emails
    print("\n📨 Email Addresses:")
    from_email = input(f"From email [{smtp_username}]: ").strip() or smtp_username
    to_email = input("Your email (where contact messages go) [jamierjhill@gmail.com]: ").strip() or "jamierjhill@gmail.com"
    
    # Optional admin key
    admin_key = input("Admin key for testing (optional): ").strip() or "dev_admin_key"
    
    # Create .env content
    env_content = f"""# Email Configuration for Tennis Match Organizer
SMTP_SERVER={smtp_server}
SMTP_PORT={smtp_port}
SMTP_USERNAME={smtp_username}
SMTP_PASSWORD={smtp_password}
FROM_EMAIL={from_email}
TO_EMAIL={to_email}
ADMIN_KEY={admin_key}

# Flask Configuration
FLASK_SECRET_KEY=dev_key_UNSAFE_FOR_PRODUCTION
FLASK_ENV=development
"""
    
    # Write .env file
    try:
        with open('.env', 'w') as f:
            f.write(env_content)
        print("\n✅ .env file created successfully!")
    except Exception as e:
        print(f"\n❌ Error creating .env file: {e}")
        return
    
    # Test configuration
    print("\n🧪 Testing email configuration...")
    test_email_config()

def test_email_config():
    """Test the current email configuration"""
    try:
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        # Test configuration
        email_service = EmailService()
        
        if not email_service.is_configured:
            print("❌ Email service not configured - check environment variables")
            return
        
        print(f"📧 SMTP Server: {email_service.smtp_server}:{email_service.smtp_port}")
        print(f"📧 From: {email_service.from_email}")
        print(f"📧 To: {email_service.to_email}")
        
        success, message = email_service.test_configuration()
        
        if success:
            print("✅ Email configuration test passed!")
            
            # Ask if user wants to send test email
            send_test = input("\n📤 Send test email? (y/N): ").lower()
            if send_test == 'y':
                send_test_email(email_service)
        else:
            print(f"❌ Email configuration test failed: {message}")
            print("\n🔧 Troubleshooting tips:")
            print("- For Gmail: Use app password, not regular password")
            print("- Enable 2-Factor Authentication first")
            print("- Check firewall/antivirus settings")
            print("- Verify SMTP server and port")
            
    except ImportError:
        print("❌ python-dotenv not installed. Run: pip install python-dotenv")
    except Exception as e:
        print(f"❌ Test error: {e}")

def send_test_email(email_service):
    """Send a test email"""
    test_data = {
        'contact_name': 'Email Setup Test',
        'contact_email': email_service.to_email,
        'contact_subject': 'other',
        'contact_message': 'This is a test email sent during setup to verify email functionality is working correctly.'
    }
    
    try:
        success, message = email_service.send_contact_email(test_data)
        
        if success:
            print("✅ Test email sent successfully!")
            print(f"📧 Check your inbox at {email_service.to_email}")
        else:
            print(f"❌ Test email failed: {message}")
    except Exception as e:
        print(f"❌ Test email error: {e}")

def main():
    """Main setup function"""
    if len(os.sys.argv) > 1 and os.sys.argv[1] == 'test':
        # Just test existing configuration
        test_email_config()
    else:
        # Full setup
        create_env_file()
    
    print("\n" + "=" * 50)
    print("🎾 Setup Complete!")
    print("\nNext steps:")
    print("1. Start the app: python app.py")
    print("2. Visit: http://localhost:5000/contact")
    print("3. Test the contact form")
    print("\nFor troubleshooting, see EMAIL_SETUP.md")

if __name__ == "__main__":
    main()