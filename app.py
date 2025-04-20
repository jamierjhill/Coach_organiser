# app.py
from dotenv import load_dotenv
load_dotenv()

import os
from flask import Flask
from flask_login import LoginManager
from flask_mail import Mail
from blueprints import all_blueprints
from models import load_users, User

mail = Mail()

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("FLASK_SECRET_KEY")

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
    os.makedirs("data", exist_ok=True)

    # Flask-Login setup
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user_by_id(user_id):
        users = load_users()
        if user_id in users:
            return User(id=user_id, username=user_id)
        return None

    # Register blueprints
    for bp in all_blueprints:
        app.register_blueprint(bp)

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
