# email_service.py - Email sending functionality for contact form
import smtplib
import ssl
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging

# Configure email logging
email_logger = logging.getLogger('email')
handler = logging.FileHandler('email.log')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
email_logger.addHandler(handler)
email_logger.setLevel(logging.INFO)

class EmailService:
    def __init__(self):
        # Email configuration from environment variables
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.from_email = os.getenv('FROM_EMAIL', self.smtp_username)
        self.to_email = os.getenv('TO_EMAIL', 'jamierjhill@gmail.com')
        
        # Validate configuration
        self.is_configured = bool(self.smtp_username and self.smtp_password)
        
        if not self.is_configured:
            email_logger.warning("Email service not configured - check environment variables")
    
    def send_contact_email(self, contact_data):
        """
        Send contact form email
        
        Args:
            contact_data (dict): Contact form data containing:
                - contact_name: Sender's name
                - contact_email: Sender's email
                - contact_subject: Message subject category
                - contact_message: Message content
        
        Returns:
            tuple: (success: bool, message: str)
        """
        if not self.is_configured:
            email_logger.error("Cannot send email - service not configured")
            return False, "Email service not configured"
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = self.to_email
            msg['Subject'] = self._get_subject_line(contact_data['contact_subject'], contact_data['contact_name'])
            
            # Create email body
            body = self._create_email_body(contact_data)
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            # Log success
            email_logger.info(f"Contact email sent successfully from {contact_data['contact_email']}")
            return True, "Email sent successfully"
            
        except smtplib.SMTPAuthenticationError:
            email_logger.error("SMTP authentication failed - check credentials")
            return False, "Email authentication failed"
        except smtplib.SMTPException as e:
            email_logger.error(f"SMTP error: {e}")
            return False, "Email server error"
        except Exception as e:
            email_logger.error(f"Unexpected email error: {e}")
            return False, "Email sending failed"
    
    def _get_subject_line(self, subject_category, sender_name):
        """Generate email subject line based on category"""
        subject_map = {
            'bug_report': '🐛 Bug Report',
            'feature_request': '🚀 Feature Request', 
            'support': '❓ Support Request',
            'feedback': '💭 Feedback',
            'other': '📝 General Inquiry'
        }
        
        subject_prefix = subject_map.get(subject_category, '📧 Contact')
        return f"[Tennis Match Organizer] {subject_prefix} from {sender_name}"
    
    def _create_email_body(self, contact_data):
        """Create formatted email body"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Map subject categories to readable names
        subject_map = {
            'bug_report': 'Bug Report',
            'feature_request': 'Feature Request', 
            'support': 'Support Question',
            'feedback': 'General Feedback',
            'other': 'Other'
        }
        
        subject_name = subject_map.get(contact_data['contact_subject'], 'Unknown')
        
        body = f"""
New contact form submission from Tennis Match Organizer

📧 CONTACT DETAILS
Name: {contact_data['contact_name']}
Email: {contact_data['contact_email']}
Subject: {subject_name}
Timestamp: {timestamp}

💬 MESSAGE
{contact_data['contact_message']}

---
This message was sent via the Tennis Match Organizer contact form.
Reply directly to respond to the sender.
        """.strip()
        
        return body
    
    def send_auto_reply(self, contact_data):
        """
        Send automatic reply to the contact form sender
        
        Args:
            contact_data (dict): Contact form data
            
        Returns:
            tuple: (success: bool, message: str)
        """
        if not self.is_configured:
            return False, "Email service not configured"
        
        try:
            # Create auto-reply message
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = contact_data['contact_email']
            msg['Subject'] = "Thank you for contacting Tennis Match Organizer"
            
            # Create auto-reply body
            body = self._create_auto_reply_body(contact_data)
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            email_logger.info(f"Auto-reply sent to {contact_data['contact_email']}")
            return True, "Auto-reply sent"
            
        except Exception as e:
            email_logger.error(f"Auto-reply error: {e}")
            return False, "Auto-reply failed"
    
    def _create_auto_reply_body(self, contact_data):
        """Create auto-reply email body"""
        
        # Estimate response time based on subject
        response_times = {
            'bug_report': '24-48 hours',
            'feature_request': '3-5 business days',
            'support': '1-2 business days',
            'feedback': '2-3 business days',
            'other': '2-3 business days'
        }
        
        estimated_response = response_times.get(contact_data['contact_subject'], '2-3 business days')
        
        body = f"""
Hi {contact_data['contact_name']},

Thank you for reaching out about Tennis Match Organizer! 

We've received your message and will get back to you within {estimated_response}.

Here's a summary of your submission:
• Subject: {contact_data['contact_subject'].replace('_', ' ').title()}
• Message: {contact_data['contact_message'][:100]}{'...' if len(contact_data['contact_message']) > 100 else ''}

In the meantime, you might find these helpful:
• Check our FAQ section on the contact page
• Visit the main app at your convenience
• Feel free to submit additional questions if needed

Best regards,
Jamie Hill
Tennis Match Organizer

---
This is an automated response. Please don't reply to this email.
If you need immediate assistance, you can submit another contact form.
        """.strip()
        
        return body
    
    def test_configuration(self):
        """
        Test email configuration
        
        Returns:
            tuple: (success: bool, message: str)
        """
        if not self.is_configured:
            return False, "Email credentials not configured"
        
        try:
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.smtp_username, self.smtp_password)
            
            return True, "Email configuration valid"
            
        except smtplib.SMTPAuthenticationError:
            return False, "Authentication failed - check username/password"
        except smtplib.SMTPException as e:
            return False, f"SMTP error: {e}"
        except Exception as e:
            return False, f"Configuration error: {e}"

# Global email service instance
email_service = EmailService()

def send_contact_message(contact_data, send_auto_reply=True):
    """
    Convenience function to send contact message with optional auto-reply
    
    Args:
        contact_data (dict): Contact form data
        send_auto_reply (bool): Whether to send auto-reply to sender
        
    Returns:
        tuple: (success: bool, message: str)
    """
    # Send main email to admin
    success, message = email_service.send_contact_email(contact_data)
    
    if success and send_auto_reply:
        # Send auto-reply to sender (don't fail if this fails)
        auto_success, auto_message = email_service.send_auto_reply(contact_data)
        if not auto_success:
            email_logger.warning(f"Auto-reply failed: {auto_message}")
    
    return success, message