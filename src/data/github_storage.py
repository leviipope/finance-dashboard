"""GitHub storage functionality for data persistence."""

import json
import base64
import streamlit as st
from github import Github
from datetime import datetime
from ..utils.encryption import get_user_encryption_key, encrypt_data, decrypt_data, is_encrypted_data


# Initialize GitHub client
GITHUB_TOKEN = st.secrets.get("github", {}).get("token")
GITHUB_REPO_OWNER = st.secrets.get("github", {}).get("repo_owner")
GITHUB_REPO_NAME = st.secrets.get("github", {}).get("repo_name")
GITHUB_BRANCH = st.secrets.get("github", {}).get("branch", "main")

github_client = None
github_repo = None

if GITHUB_TOKEN and GITHUB_REPO_OWNER and GITHUB_REPO_NAME:
    try:
        github_client = Github(GITHUB_TOKEN)
        github_repo = github_client.get_repo(f"{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}")
        # Store in session state for access from other modules
        st.session_state.github_repo = github_repo
    except Exception as e:
        st.error(f"Error connecting to GitHub: {str(e)}")


def get_user_files(username):
    """Get file paths for a user's data"""
    if username == "admin":
        return {
            "dataframe": "data/dataframes/main_dataframe.csv",
            "categories": "data/categories/categories.json"
        }
    else:
        return {
            "dataframe": f"data/dataframes/{username}_dataframe.csv",
            "categories": f"data/categories/{username}_categories.json"
        }


def ensure_github_file_exists(file_path, default_content="{}"):
    """Ensure a GitHub file exists, create it if it doesn't"""
    if not github_repo:
        return False
    
    try: 
        github_repo.get_contents(file_path, ref=GITHUB_BRANCH)
        return True
    except Exception:
        try:
            # For non-admin users, encrypt the default content only for their own files
            final_content = default_content
            if (st.session_state.get("username") and 
                st.session_state.username != "admin" and 
                st.session_state.username != "guest" and
                st.session_state.username in file_path):  # Only encrypt if it's the user's own file
                
                encryption_key = get_user_encryption_key(st.session_state.username)
                if encryption_key:
                    final_content = encrypt_data(default_content, encryption_key)
            
            github_repo.create_file(
                file_path,
                f"Initialize {file_path}",
                final_content,
                branch=GITHUB_BRANCH
            )
            return True
        except Exception as e:
            st.error(f"Failed to create {file_path}: {str(e)}")
            return False


def read_github_file(file_path):
    """Read a file from GitHub repository"""
    if not github_repo:
        return None
    
    try:
        file_content = github_repo.get_contents(file_path, ref=GITHUB_BRANCH)
        content = base64.b64decode(file_content.content).decode('utf-8')
        return content
    except:
        return None


def read_encrypted_github_file(file_path, username):
    """Read and decrypt a GitHub file for a specific user"""
    if not github_repo:
        return None
    
    # Only process files for the currently logged-in user or admin
    if not st.session_state.get("username") or (
        st.session_state.username != username and 
        st.session_state.username != "admin" and 
        username != "admin"
    ):
        return None
    
    try:
        file_content = github_repo.get_contents(file_path, ref=GITHUB_BRANCH)
        content = base64.b64decode(file_content.content).decode('utf-8')
        
        # If admin, return content as-is (not encrypted)
        if username == "admin":
            return content
        
        # Check if the content is already encrypted
        if not is_encrypted_data(content):
            # Content is not encrypted (probably default content like "{}")
            return content
        
        # For regular users, decrypt the content
        encryption_key = get_user_encryption_key(username)
        if encryption_key:
            decrypted_data = decrypt_data(content, encryption_key)
            if decrypted_data is not None:
                return decrypted_data
            else:
                # Decryption failed, might be unencrypted legacy data
                return content
        else:
            return None
    except Exception:
        return None


def write_github_file(file_path, content, commit_message):
    """Write a file to GitHub repository"""
    if not github_repo:
        return False
    
    try:
        try:
            file_content = github_repo.get_contents(file_path, ref=GITHUB_BRANCH)
            github_repo.update_file(
                file_path,
                commit_message,
                content,
                file_content.sha,
                branch=GITHUB_BRANCH
            )
        except:
            github_repo.create_file(
                file_path,
                commit_message,
                content,
                branch=GITHUB_BRANCH
            )
        return True
    except Exception as e:
        st.error(f"Failed to write {file_path}: {str(e)}")
        return False


def write_encrypted_github_file(file_path, content, commit_message, username):
    """Encrypt and write a GitHub file for a specific user"""
    if not github_repo:
        return False
    
    # Only allow writing for the currently logged-in user
    if not st.session_state.get("username") or st.session_state.username != username:
        return False
    
    # If admin, save content as-is (not encrypted)
    if username == "admin":
        final_content = content
    else:
        # For regular users, encrypt the content
        encryption_key = get_user_encryption_key(username)
        if encryption_key:
            final_content = encrypt_data(content, encryption_key)
        else:
            st.error("Unable to get encryption key for user")
            return False
    
    return write_github_file(file_path, final_content, commit_message)


def delete_user_data(username):
    """Delete all user data including categories, dataframe, and user account"""
    if not username or username == "admin":
        return False, "Cannot delete admin user or invalid username"
    
    if not github_repo:
        return False, "GitHub storage not configured"
    
    try:
        files = get_user_files(username)
        errors = []
        
        # Delete user's dataframe file
        try:
            file_content = github_repo.get_contents(files["dataframe"], ref=GITHUB_BRANCH)
            github_repo.delete_file(
                files["dataframe"],
                f"Delete dataframe for user: {username} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                file_content.sha,
                branch=GITHUB_BRANCH
            )
        except Exception as e:
            if "Not Found" not in str(e):
                errors.append(f"Failed to delete dataframe: {str(e)}")
        
        # Delete user's categories file
        try:
            file_content = github_repo.get_contents(files["categories"], ref=GITHUB_BRANCH)
            github_repo.delete_file(
                files["categories"],
                f"Delete categories for user: {username} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                file_content.sha,
                branch=GITHUB_BRANCH
            )
        except Exception as e:
            if "Not Found" not in str(e):
                errors.append(f"Failed to delete categories: {str(e)}")
        
        # Remove user from users.json
        users_content = read_github_file("data/users.json")
        if users_content:
            try:
                users = json.loads(users_content)
                if username in users:
                    del users[username]
                    updated_users_content = json.dumps(users, indent=2)
                    success = write_github_file(
                        "data/users.json", 
                        updated_users_content, 
                        f"Delete user account: {username} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    if not success:
                        errors.append("Failed to update users.json")
                else:
                    errors.append("User not found in users.json")
            except Exception as e:
                errors.append(f"Failed to process users.json: {str(e)}")
        else:
            errors.append("Users.json not found")
        
        if errors:
            return False, "; ".join(errors)
        else:
            return True, "User data deleted successfully"
            
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"
