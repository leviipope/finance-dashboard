"""Encryption and decryption utilities."""

import json
import base64
import streamlit as st
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def derive_key_from_password(username, password_hash):
    """Derive encryption key from username and password hash"""
    salt = username.encode('utf-8')[:16].ljust(16, b'0')  # Use username as salt, pad to 16 bytes
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password_hash.encode('utf-8')))
    return key


def encrypt_data(data, key):
    """Encrypt data using Fernet encryption"""
    fernet = Fernet(key)
    encrypted_data = fernet.encrypt(data.encode('utf-8'))
    return base64.b64encode(encrypted_data).decode('utf-8')


def decrypt_data(encrypted_data, key):
    """Decrypt data using Fernet encryption"""
    try:
        fernet = Fernet(key)
        decoded_data = base64.b64decode(encrypted_data.encode('utf-8'))
        decrypted_data = fernet.decrypt(decoded_data)
        return decrypted_data.decode('utf-8')
    except Exception as e:
        st.error(f"Failed to decrypt data: {str(e)}")
        return None


def is_encrypted_data(data):
    """Check if data appears to be encrypted (base64 encoded)"""
    try:
        # Check if it's valid base64 and has the right length
        if len(data) % 4 != 0:
            return False
        decoded = base64.b64decode(data.encode('utf-8'))
        # Encrypted data should be longer and have specific patterns
        return len(decoded) > 50
    except Exception:
        return False


def get_user_encryption_key(username):
    """Get the encryption key for a user"""
    if username == "admin":
        return None  # Admin data is not encrypted
    
    # Only get encryption key for the currently logged-in user
    if not st.session_state.get("username") or st.session_state.username != username:
        return None
    
    # Import here to avoid circular imports - this needs to be done differently
    # We'll create a simple file reader that doesn't depend on github_storage
    import os
    try:
        # First try to read from a local cache or use github_repo directly
        if hasattr(st.session_state, 'github_repo') and st.session_state.github_repo:
            github_repo = st.session_state.github_repo
            file_content = github_repo.get_contents("data/users.json")
            users_content = base64.b64decode(file_content.content).decode('utf-8')
        else:
            # Fallback: try to get github_repo from secrets
            GITHUB_TOKEN = st.secrets.get("github", {}).get("token")
            GITHUB_REPO_OWNER = st.secrets.get("github", {}).get("repo_owner")
            GITHUB_REPO_NAME = st.secrets.get("github", {}).get("repo_name")
            GITHUB_BRANCH = st.secrets.get("github", {}).get("branch", "main")
            
            if GITHUB_TOKEN and GITHUB_REPO_OWNER and GITHUB_REPO_NAME:
                from github import Github
                github_client = Github(GITHUB_TOKEN)
                github_repo = github_client.get_repo(f"{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}")
                file_content = github_repo.get_contents("data/users.json", ref=GITHUB_BRANCH)
                users_content = base64.b64decode(file_content.content).decode('utf-8')
            else:
                return None
                
        users = json.loads(users_content)
        if username in users:
            password_hash = users[username]["password"]
            return derive_key_from_password(username, password_hash)
    except Exception:
        pass
    return None
