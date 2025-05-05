# make_admin.py
# Run this script to make a user an admin
# Usage: python make_admin.py username

import os
import sys
import json

def make_admin(username):
    """
    Make a user an admin by adding the is_admin flag to their user file
    """
    users_dir = "data/users"
    user_file = f"{users_dir}/{username}.json"
    
    if not os.path.exists(user_file):
        print(f"❌ User {username} not found!")
        return False
        
    try:
        with open(user_file, 'r') as f:
            user_data = json.load(f)
            
        if user_data.get('is_admin', False):
            print(f"⚠️ User {username} is already an admin!")
            return True
            
        user_data['is_admin'] = True
        
        with open(user_file, 'w') as f:
            json.dump(user_data, f, indent=2)
            
        print(f"✅ User {username} is now an admin!")
        return True
    
    except Exception as e:
        print(f"❌ Error making {username} an admin: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python make_admin.py username")
        sys.exit(1)
        
    username = sys.argv[1]
    make_admin(username)