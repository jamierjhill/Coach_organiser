import os
import json

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

# === Core User Info ===
USER_DIR = "data/users"

def user_path(username):
    return os.path.join(USER_DIR, f"{username}.json")

def load_user(username):
    path = user_path(username)
    print(f"🔍 Attempting to load user file: {path}")  # Debug logging
    if os.path.exists(path):
        try:
            with open(path) as f:
                data = json.load(f)
                print("✅ Loaded user data:", data)
                return data
        except json.JSONDecodeError as e:
            print(f"❌ JSON error in user file: {e}")
        except Exception as e:
            print(f"❌ Unexpected error loading user: {e}")
    else:
        print("⚠️ User file not found.")
    return None

def save_user(user_data):
    ensure_dir(USER_DIR)
    path = user_path(user_data["username"])
    with open(path, "w") as f:
        json.dump(user_data, f, indent=2)

def rename_user_file(old_username, new_username):
    old_path = user_path(old_username)
    new_path = user_path(new_username)
    if os.path.exists(old_path):
        os.rename(old_path, new_path)

def delete_user_file(username):
    path = user_path(username)
    if os.path.exists(path):
        os.remove(path)

# === Feature-Specific Data (notes, events, etc.) ===
def feature_path(folder, username, prefix=""):
    return os.path.join(folder, f"{prefix}{username}.json")

def load_json_feature(folder, username, prefix=""):
    path = feature_path(folder, username, prefix)
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Error reading {path}: {e}")
    return []

def save_json_feature(folder, username, data, prefix=""):
    ensure_dir(folder)
    path = feature_path(folder, username, prefix)
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"⚠️ Error writing {path}: {e}")

def rename_feature_file(folder, old_username, new_username, prefix=""):
    old_path = feature_path(folder, old_username, prefix)
    new_path = feature_path(folder, new_username, prefix)
    if os.path.exists(old_path):
        os.rename(old_path, new_path)

def delete_feature_file(folder, username, prefix=""):
    path = feature_path(folder, username, prefix)
    if os.path.exists(path):
        os.remove(path)
