# models.py
from flask_login import UserMixin
import os
import json

USERS_FILE = "data/users.json"
class User:
    def __init__(self, id, username):
        self.id = id
        self.username = username

    def get_id(self):
        return self.id

    @property
    def is_authenticated(self): return True
    @property
    def is_active(self): return True
    @property
    def is_anonymous(self): return False


def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)