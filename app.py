# app.py - Tennis Match Organizer (No Authentication)
from dotenv import load_dotenv
load_dotenv()

import os
from datetime import timedelta
from flask import Flask, render_template, session

def create_app():
    app = Flask(__name__)
    
    # Set secret key for session management
    app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev_key_UNSAFE_FOR_PRODUCTION")
    
    # Session configuration
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    
    # Make session permanent by default
    @app.before_request
    def make_session_permanent():
        session.permanent = True
    
    # Basic security headers
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response

    # Register only the match organizer blueprint
    from blueprints.match import match_bp
    app.register_blueprint(match_bp)
        
    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('error.html', 
                              error_code=404, 
                              error_message="Page not found"), 404
                              
    @app.errorhandler(500)
    def server_error(e):
        return render_template('error.html', 
                              error_code=500, 
                              error_message="Internal server error"), 500

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)