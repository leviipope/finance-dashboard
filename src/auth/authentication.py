"""Authentication functionality including login, registration, and password management."""

import hashlib
import secrets
import time
import json
import streamlit as st
from datetime import datetime
from ..data.github_storage import read_github_file, write_github_file


def hash_password(password):
    """Hash a password with salt"""
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return salt + password_hash.hex()


def verify_password(stored_password, provided_password):
    """Verify a password against stored hash"""
    salt = stored_password[:32]
    stored_hash = stored_password[32:]
    password_hash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return stored_hash == password_hash.hex()


def authenticate_user(username, password):
    """Authenticate a user with username and password"""
    if not username or not password:
        return False
    
    users_content = read_github_file("data/users.json")
    
    if users_content:
        try:
            users = json.loads(users_content)
            if username in users:
                stored_password = users[username]["password"]
                return verify_password(stored_password, password)
        except:
            pass
    
    return False


def register_user(username, password, confirm_password):
    """Register a new user"""
    if not username or not password:
        st.error("Please fill in all fields!")
        return False
    
    if password != confirm_password:
        st.error("Passwords don't match!")
        return False
    
    if username == "guest":
        st.error("Username 'guest' is reserved!")
        return False
    
    users_content = read_github_file("data/users.json")
    users = {}
    
    if users_content:
        try:
            users = json.loads(users_content)
        except:
            users = {}
    
    if username in users:
        st.error("Username already exists!")
        return False
    
    hashed_password = hash_password(password)
    users[username] = {
        "password": hashed_password,
        "created_at": datetime.now().isoformat()
    }
    
    users_content = json.dumps(users, indent=2)
    commit_message = f"Register new user: {username} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    success = write_github_file("data/users.json", users_content, commit_message)
    
    if success:
        st.success(f"🎉 Registration successful! Welcome {username}")
        st.balloons()
        time.sleep(1)
        return True
    else:
        st.error("Failed to register user. Please try again.")
        return False


def change_password(username, old_password, new_password, confirm_password):
    """Change user password"""
    if not username or not old_password or not new_password:
        st.error("Please fill in all fields!")
        return False
    
    if new_password != confirm_password:
        st.error("New passwords don't match!")
        return False
    
    users_content = read_github_file("data/users.json")
    
    if not users_content:
        st.error("User database not found!")
        return False
    
    try:
        users = json.loads(users_content)
    except:
        st.error("Error reading user database!")
        return False
    
    if username not in users:
        st.error("User not found!")
        return False
    
    # Verify old password
    stored_password = users[username]["password"]
    if not verify_password(stored_password, old_password):
        st.error("Current password is incorrect!")
        return False
    
    # Update password
    hashed_password = hash_password(new_password)
    users[username]["password"] = hashed_password
    users[username]["password_changed_at"] = datetime.now().isoformat()
    
    users_content = json.dumps(users, indent=2)
    commit_message = f"Password changed for user: {username} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    success = write_github_file("data/users.json", users_content, commit_message)
    
    if success:
        st.success("🔐 Password changed successfully!")
        time.sleep(2)
        return True
    else:
        st.error("Failed to change password. Please try again.")
        return False
