import os
import json

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

# === Core User Info ===
USER_DIR = "data/users"

def user_path(username):
    """
    Generate a safe file path for a user's data file.
    Sanitizes the username to prevent path traversal attacks.
    
    Args:
        username: The username to generate a path for
        
    Returns:
        str: The full path to the user's data file
    """
    # Sanitize username to prevent path traversal
    safe_username = "".join(c for c in username if c.isalnum() or c in ['-', '_'])
    return os.path.join(USER_DIR, f"{safe_username}.json")

def load_user(username):
    """
    Load a user's data from disk.
    
    Args:
        username: The username to load
        
    Returns:
        dict: The user's data, or None if not found
    """
    path = user_path(username)
    print(f"🔍 Loading user: {username}")  # Only log username
    if os.path.exists(path):
        try:
            with open(path) as f:
                data = json.load(f)
                print(f"✅ User {username} loaded successfully")
                return data
        except json.JSONDecodeError as e:
            print(f"❌ JSON error in user file: {e}")
        except Exception as e:
            print(f"❌ Unexpected error loading user: {e}")
    else:
        print("⚠️ User file not found.")
    return None

def save_user(user_data):
    """
    Save a user's data to disk with proper error handling.
    
    Args:
        user_data: The user data to save
        
    Returns:
        bool: True if saved successfully, False otherwise
    """
    if not user_data or "username" not in user_data:
        print("❌ Invalid user data - missing username")
        return False
        
    try:
        ensure_dir(USER_DIR)
        path = user_path(user_data["username"])
        
        # Create a backup of the existing file if it exists
        if os.path.exists(path):
            backup_path = f"{path}.bak"
            try:
                shutil.copy2(path, backup_path)
            except Exception as e:
                print(f"⚠️ Failed to create backup: {e}")
        
        # Write to a temporary file first, then rename for atomic operation
        temp_path = f"{path}.tmp"
        with open(temp_path, "w") as f:
            json.dump(user_data, f, indent=2)
            
        # Ensure file is flushed to disk
        os.fsync(f.fileno())
        
        # Atomic rename for safer file replacement
        os.replace(temp_path, path)
        return True
    except Exception as e:
        print(f"❌ Error saving user {user_data.get('username', 'unknown')}: {e}")
        return False

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
