# migrate_passwords.py
# 
# This script migrates existing user accounts to use password hashing.
# Run this script once to update all existing user accounts.

import os
import json
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from password_utils import hash_password

def migrate_user_passwords():
    """
    Migrate all existing user passwords to the new hashed format.
    """
    users_dir = "data/users"
    if not os.path.exists(users_dir):
        print(f"❌ Users directory not found: {users_dir}")
        return
    
    print("🔐 Starting password migration...")
    migrated_count = 0
    error_count = 0
    
    # Process each user file
    for filename in os.listdir(users_dir):
        if not filename.endswith('.json'):
            continue
            
        filepath = os.path.join(users_dir, filename)
        try:
            # Load user data
            with open(filepath, 'r') as f:
                user_data = json.load(f)
            
            # Skip if already migrated
            if "password_hash" in user_data:
                print(f"✅ User {user_data['username']} already migrated")
                continue
                
            # Get plaintext password and hash it
            plaintext_password = user_data.get("password")
            if not plaintext_password:
                print(f"⚠️ No password found for {user_data['username']}")
                error_count += 1
                continue
                
            # Generate hash and salt
            hashed_password, salt = hash_password(plaintext_password)
            
            # Update user data
            user_data["password_hash"] = hashed_password
            user_data["password_salt"] = salt
            
            # Save updated user data
            with open(filepath, 'w') as f:
                json.dump(user_data, f, indent=2)
                
            print(f"✅ Migrated {user_data['username']}")
            migrated_count += 1
            
        except Exception as e:
            print(f"❌ Error migrating {filename}: {str(e)}")
            error_count += 1
    
    print(f"\n🔐 Migration complete!")
    print(f"✅ {migrated_count} users migrated successfully")
    if error_count > 0:
        print(f"⚠️ {error_count} errors encountered")
    
if __name__ == "__main__":
    migrate_user_passwords()