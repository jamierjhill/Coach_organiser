# app.py
from dotenv import load_dotenv
load_dotenv()

import os
from datetime import timedelta
from flask import Flask, send_from_directory
from flask_login import LoginManager
from flask_mail import Mail
from blueprints import all_blueprints
from models import User, load_user_by_id

mail = Mail()

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("FLASK_SECRET_KEY")
    
    # Add this for ngrok HTTPS support
    app.config['PREFERRED_URL_SCHEME'] = 'https'
    
    # Add session configuration
    app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)  # Session lasts 24 hours
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

    # Mail config
    app.config.update(
        MAIL_SERVER=os.getenv("MAIL_SERVER"),
        MAIL_PORT=int(os.getenv("MAIL_PORT")),
        MAIL_USE_TLS=os.getenv("MAIL_USE_TLS") == "True",
        MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
        MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
        MAIL_DEFAULT_SENDER=os.getenv("MAIL_USERNAME")
    )
    mail.init_app(app)

    # Ensure required directories exist
    os.makedirs("sessions", exist_ok=True)
    os.makedirs("notes", exist_ok=True)
    os.makedirs("data/events", exist_ok=True)
    os.makedirs("data/users", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    os.makedirs("static", exist_ok=True)

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