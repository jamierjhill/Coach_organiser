# models.py
import os
import json
from flask_login import UserMixin

USERS_DIR = "data/users"

class User(UserMixin):
    def __init__(self, id, username, is_admin=False):
        self.id = id
        self.username = username
        self.is_admin = is_admin

    def get_id(self):
        return self.id
    
    def is_administrator(self):
        return self.is_admin

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
        is_admin = data.get("is_admin", False)
        return User(id=data["username"], username=data["username"], is_admin=is_admin)
    return None

# Helper to create the first admin user
def create_admin(username):
    path = os.path.join(USERS_DIR, f"{username}.json")
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
        
        data["is_admin"] = True
        
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"✅ User {username} was granted admin privileges")
        return True
    else:
        print(f"❌ User {username} not found")
        return False

# For creating your first admin, run in a Python shell:
# from models import create_admin
# create_admin("your_username")