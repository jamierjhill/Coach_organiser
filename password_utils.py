# password_utils.py
import hashlib
import os
import secrets

def generate_salt():
    """Generate a random salt for password hashing."""
    return secrets.token_hex(16)

def hash_password(password, salt=None):
    """
    Hash a password using SHA-256 with a salt.
    
    Args:
        password: The plaintext password to hash
        salt: Optional salt to use (generates a new one if not provided)
        
    Returns:
        tuple: (hashed_password, salt)
    """
    if salt is None:
        salt = generate_salt()
        
    # Combine password and salt then hash
    password_bytes = password.encode('utf-8')
    salt_bytes = salt.encode('utf-8')
    hash_obj = hashlib.sha256(password_bytes + salt_bytes)
    hashed = hash_obj.hexdigest()
    
    return hashed, salt

def verify_password(stored_password, stored_salt, provided_password):
    """
    Verify if a provided password matches the stored hash.
    
    Args:
        stored_password: The stored hashed password
        stored_salt: The salt used to hash the stored password
        provided_password: The plaintext password to verify
        
    Returns:
        bool: True if the password matches, False otherwise
    """
    hashed, _ = hash_password(provided_password, stored_salt)
    return secrets.compare_digest(hashed, stored_password)