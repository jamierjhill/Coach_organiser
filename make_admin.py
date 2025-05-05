#!/usr/bin/env python3
# make_admin.py - Enhanced version
import os
import sys
import json
import argparse
from pathlib import Path

def make_admin(username):
    """
    Make a user an admin by adding the is_admin flag to their user file.
    
    Args:
        username: The username to promote to admin
        
    Returns:
        bool: True if successful, False otherwise
    """
    users_dir = "data/users"
    user_file = os.path.join(users_dir, f"{username}.json")
    
    if not os.path.exists(user_file):
        print(f"❌ User {username} not found!")
        return False
        
    try:
        # Read current data
        with open(user_file, 'r') as f:
            user_data = json.load(f)
            
        if user_data.get('is_admin', False):
            print(f"⚠️ User {username} is already an admin!")
            return True
            
        # Make backup
        backup_file = f"{user_file}.bak"
        try:
            with open(user_file, 'r') as src, open(backup_file, 'w') as dst:
                dst.write(src.read())
        except Exception as e:
            print(f"⚠️ Failed to create backup: {e}")
            
        # Update and save
        user_data['is_admin'] = True
        
        with open(user_file, 'w') as f:
            json.dump(user_data, f, indent=2)
            
        print(f"✅ User {username} is now an admin!")
        return True
    
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing user file: {e}")
        return False
    except Exception as e:
        print(f"❌ Error making {username} an admin: {str(e)}")
        return False

def list_users():
    """List all available users in the system."""
    users_dir = "data/users"
    if not os.path.exists(users_dir):
        print(f"❌ Users directory not found: {users_dir}")
        return
        
    print("\nAvailable users:")
    print("---------------")
    
    for filename in sorted(os.listdir(users_dir)):
        if filename.endswith('.json'):
            username = filename[:-5]  # Remove .json extension
            try:
                with open(os.path.join(users_dir, filename)) as f:
                    data = json.load(f)
                    is_admin = data.get('is_admin', False)
                    admin_status = "[ADMIN]" if is_admin else ""
                    print(f"  {username} {admin_status}")
            except:
                print(f"  {username} [ERROR: Could not read file]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage admin privileges for Coaches Hub users")
    parser.add_argument("username", nargs="?", help="Username to make admin")
    parser.add_argument("--list", "-l", action="store_true", help="List all users")
    
    args = parser.parse_args()
    
    if args.list:
        list_users()
        sys.exit(0)
        
    if not args.username:
        parser.print_help()
        sys.exit(1)
        
    success = make_admin(args.username)
    sys.exit(0 if success else 1)