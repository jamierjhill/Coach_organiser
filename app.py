# app.py
from dotenv import load_dotenv
load_dotenv()

import os
from datetime import timedelta
from flask import Flask, send_from_directory, session
from flask_login import LoginManager
from flask_mail import Mail
from blueprints import all_blueprints
from models import User, load_user_by_id

mail = Mail()

def create_app():
    app = Flask(__name__)
    
    # Check for required environment variables
    required_env_vars = {
        "FLASK_SECRET_KEY": "Secret key is required for secure session management",
        "OPENWEATHER_API_KEY": "API key is required for weather functionality",
        "MAIL_SERVER": "Mail server configuration is required for email notifications"
    }
    
    missing_vars = []
    for var, message in required_env_vars.items():
        if not os.getenv(var):
            missing_vars.append(f"{var}: {message}")
    
    if missing_vars:
        print("ERROR: Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("Application may not function correctly without these variables.")
    
    # Set secret key with fallback for development only
    app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev_key_UNSAFE_FOR_PRODUCTION")
    
    # Add this for ngrok HTTPS support
    app.config['PREFERRED_URL_SCHEME'] = 'https'
    
    # Add session configuration
    app.config['SESSION_COOKIE_SECURE'] = True if os.getenv("PRODUCTION", "False").lower() == "true" else False
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)  # Session lasts 24 hours
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    
    # FIXED: Make session permanent by default to extend session lifetime
    @app.before_request
    def make_session_permanent():
        session.permanent = True
    
    # Security headers middleware
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response

    # Mail config with proper error handling
    mail_config = {
        "MAIL_SERVER": os.getenv("MAIL_SERVER"),
        "MAIL_PORT": int(os.getenv("MAIL_PORT", "587")),
        "MAIL_USE_TLS": os.getenv("MAIL_USE_TLS", "True") == "True",
        "MAIL_USERNAME": os.getenv("MAIL_USERNAME"),
        "MAIL_PASSWORD": os.getenv("MAIL_PASSWORD"),
        "MAIL_DEFAULT_SENDER": os.getenv("MAIL_USERNAME")
    }
    
    # Only enable mail if all required mail settings are present
    if all(mail_config.values()):
        app.config.update(mail_config)
        mail.init_app(app)
    else:
        print("WARNING: Email functionality disabled due to missing configuration")

    # Ensure required directories exist
    required_dirs = [
        "sessions", "notes", "data", "data/events", 
        "data/users", "data/bulletins", "data/emails", "static"
    ]
    for directory in required_dirs:
        os.makedirs(directory, exist_ok=True)

    # Flask-Login setup
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return load_user_by_id(user_id)

    # Register blueprints
    for bp in all_blueprints:
        app.register_blueprint(bp)
    
    # Define the static file route for service worker
    @app.route('/static/<path:filename>')
    def serve_static(filename):
        return send_from_directory('static', filename)

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)  # Changed to listen on all interfaces