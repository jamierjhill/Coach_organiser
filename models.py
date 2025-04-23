# models.py
import os
import json
from flask_login import UserMixin

USERS_DIR = "data/users"

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

    def get_id(self):
        return self.id

# Optional: still needed in settings.py to update login credentials
USERS_FILE = "data/users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

# Flask-Login loader function (used in app.py)
def load_user_by_id(user_id):
    path = os.path.join(USERS_DIR, f"{user_id}.json")
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
        return User(id=data["username"], username=data["username"])
    return None
