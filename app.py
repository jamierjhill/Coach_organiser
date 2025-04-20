# app.py
from dotenv import load_dotenv
load_dotenv()


from flask import Flask
from flask_login import LoginManager
from dotenv import load_dotenv
import os

from blueprints import all_blueprints  # imports from blueprints/__init__.py
from models import load_users, User

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("FLASK_SECRET_KEY")

    # Ensure required directories exist
    os.makedirs("sessions", exist_ok=True)
    os.makedirs("notes", exist_ok=True)
    os.makedirs("data/events", exist_ok=True)
    os.makedirs("data", exist_ok=True)

    # Set up Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user_by_id(user_id):
        users = load_users()
        if user_id in users:
            return User(id=user_id, username=user_id)
        return None

    # Register all blueprints
    for bp in all_blueprints:
        app.register_blueprint(bp)

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
