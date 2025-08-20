"""Authentication functionality including login, registration, and password management."""

import hashlib
import secrets
import time
import json
import streamlit as st
from datetime import datetime
from ..data.github_storage import read_github_file, write_github_file, read_encrypted_github_file, write_encrypted_github_file
from ..data.processing import get_user_files
from ..utils.encryption import (
    derive_key_from_password, 
    encrypt_data, 
    decrypt_data,
)


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
    """Change user password and re-encrypt data"""
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

    # --- Re-encryption logic ---
    st.info("🔑 Your password is used to encrypt your data. Re-encrypting data with new password...")

    # 1. Get old and new encryption keys
    old_key = derive_key_from_password(username, stored_password)
    new_hashed_password = hash_password(new_password)
    new_key = derive_key_from_password(username, new_hashed_password)

    if not old_key or not new_key:
        st.error("Could not generate encryption keys. Aborting password change.")
        return False

    # 2. Get user data files
    files = get_user_files(username)
    files_to_reencrypt = [files["dataframe"], files["categories"]]

    # 3. Decrypt with old key, re-encrypt with new key
    for file_path in files_to_reencrypt:
        encrypted_content = read_github_file(file_path)
        if encrypted_content:
            try:
                decrypted_content = decrypt_data(encrypted_content, old_key)
                if decrypted_content is None:
                    # This could happen if data was not encrypted, or decryption failed
                    # We'll assume it failed and stop
                    st.error(f"Failed to decrypt {file_path} with old password. Aborting password change.")
                    return False

                # Re-encrypt with the new key
                reencrypted_content = encrypt_data(decrypted_content, new_key)
                if reencrypted_content is None:
                    st.error(f"Failed to re-encrypt {file_path} with new password. Aborting.")
                    return False

                # Write back to GitHub
                commit_message = f"Re-encrypt data for {username} due to password change"
                success = write_github_file(file_path, reencrypted_content, commit_message)
                if not success:
                    st.error(f"Failed to write re-encrypted data for {file_path}. Aborting.")
                    return False
            except Exception:
                # This case handles data that was not encrypted in the first place.
                # We will encrypt it with the new key.
                try:
                    reencrypted_content = encrypt_data(encrypted_content, new_key)
                    write_github_file(file_path, reencrypted_content, f"Encrypting existing data for {username} during password change")
                except Exception as e2:
                     st.error(f"Could not encrypt existing unencrypted data: {e2}")
                     return False

    st.success("Data re-encryption successful.")
    # --- Re-encryption logic ends ---

    # Update password in users.json
    users[username]["password"] = new_hashed_password
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
