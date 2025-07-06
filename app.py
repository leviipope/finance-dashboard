import pandas as pd
import streamlit as st
import os
import json
import matplotlib.pyplot as plt
import plotly.express as px
import hashlib
import secrets
import time
from github import Github
import base64
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

st.set_page_config(page_title="Financial Dashboard", page_icon=":money_with_wings:", layout="wide") 

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
    except Exception as e:
        st.error(f"Error connecting to GitHub: {str(e)}")

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
    
    # Get user's password hash from the database
    users_content = read_github_file("data/users.json")
    if users_content:
        try:
            users = json.loads(users_content)
            if username in users:
                password_hash = users[username]["password"]
                return derive_key_from_password(username, password_hash)
        except Exception:
            pass
    return None

def ensure_github_file_exists(file_path, default_content="{}"):
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

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "is_guest" not in st.session_state:
    st.session_state.is_guest = False
if "categories" not in st.session_state:
    st.session_state.categories = {"Uncategorized": []}

def get_user_files(username):
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

def load_user_data(username):
    if st.session_state.is_guest:
        st.session_state.categories = {"Uncategorized": []}
        return
        
    files = get_user_files(username)
    
    categories_content = read_encrypted_github_file(files["categories"], username)
    if categories_content:
        try:
            st.session_state.categories = json.loads(categories_content)
        except:
            st.session_state.categories = {"Uncategorized": []}
    else:
        ensure_github_file_exists(files["categories"], json.dumps({"Uncategorized": []}))
        st.session_state.categories = {"Uncategorized": []}

if st.session_state.logged_in and st.session_state.username:
    load_user_data(st.session_state.username)

def load_statement(file):
    try: 
        df = pd.read_csv(file)
        df = df.drop(["Fee", "Completed Date", "Currency", "State"], axis=1)
        df = df[df["Type"] != "INTEREST"]
        df['Started Date'] = pd.to_datetime(df['Started Date'])
        df = df.rename(columns={"Started Date": "Date"})

        df["Hide"] = False 
        df.loc[df['Description'].str.startswith('To HUF'), 'Hide'] = True
        df.loc[df['Description'] == 'Transfer from Revolut user', 'Hide'] = True
        df.loc[(df['Product'] == 'Current') & (df['Description'] == 'From Savings Account'), 'Hide'] = True
        df.loc[(df['Product'] == 'Current') & (df['Description'] == 'To Savings Account'), 'Hide'] = True

        df['Amount'] = df['Amount'].round().astype(int)

        try:
            df['Balance'] = pd.to_numeric(df['Balance'], errors='coerce').round().astype('Int64')
            dropped_rows = df[df['Balance'].isnull()]
            
            if not dropped_rows.empty:
                st.warning(f"Dropped {len(dropped_rows)} rows due to invalid or null Balance:")
                for index, row in dropped_rows.iterrows():
                    st.warning(f"{row['Description']} {row['Amount']}")

            
            df = df.dropna(subset=['Balance'])
        except Exception as e:
            st.error(f"Error processing Balance column: {str(e)}")
            st.stop()

        return categorize_transactions(df)
    except Exception as e:
        st.error(f"Error reading the file: {str(e)}")
        return None

def load_main_dataframe():
    if st.session_state.is_guest:
        return None
    
    files = get_user_files(st.session_state.username)
    csv_content = read_encrypted_github_file(files["dataframe"], st.session_state.username)
    
    if csv_content:
        try:
            from io import StringIO
            df = pd.read_csv(StringIO(csv_content))
            df['Date'] = pd.to_datetime(df['Date'])
            return df
        except Exception as e:
            st.error(f"Error loading dataframe: {str(e)}")
            return None
    else:
        return None

def load_main_spending_dataframe():
    if st.session_state.is_guest:
        if 'guest_dataframe' in st.session_state:
            main_df = st.session_state.guest_dataframe.copy()
            main_df = main_df[main_df['Hide'] == False]
            main_df = main_df[main_df['Product'] != 'Deposit']
            return main_df
        return None
    
    main_df = load_main_dataframe()
    if main_df is not None:
        main_df = main_df[main_df['Hide'] == False].copy()
        main_df = main_df[main_df['Product'] != 'Deposit']
    return main_df

def merge_dataframes(main_df, new_df):
    combined_df = pd.concat([main_df, new_df]).drop_duplicates(subset=['Date', 'Description', 'Balance'], keep='first')
    num_new_rows = len(combined_df) - len(main_df)
    return combined_df, num_new_rows

def save_main_dataframe(df):
    if st.session_state.is_guest:
        return
    
    files = get_user_files(st.session_state.username)
    csv_content = df.to_csv(index=False)
    
    commit_message = f"Update dataframe for user {st.session_state.username} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    success = write_encrypted_github_file(files["dataframe"], csv_content, commit_message, st.session_state.username)
    
    if success:
        st.success("✅ Data saved")
    else:
        st.error("❌ Failed to save data")

def save_categories():
    if st.session_state.is_guest:
        return
    
    files = get_user_files(st.session_state.username)
    categories_content = json.dumps(st.session_state.categories, indent=2)
    
    commit_message = f"Update categories for user {st.session_state.username} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    success = write_encrypted_github_file(files["categories"], categories_content, commit_message, st.session_state.username)

def categorize_transactions(df):
    df["Category"] = "Uncategorized"

    for category, keywords in st.session_state.categories.items():
        if category == "Uncategorized" or not keywords:
            continue

        lowered_keywords = [keyword.lower().strip() for keyword in keywords]
        for idx, row in df.iterrows():
            details = row["Description"].lower().strip()

            if details in lowered_keywords:
                df.at[idx, "Category"] = category

    return df

def add_keyword_to_category(category, keyword):
    keyword = keyword.strip()
    if keyword and keyword not in st.session_state.categories.get(category, []):
        st.session_state.categories[category].append(keyword)
        save_categories()
        return True
    return False

def get_spending_color(amount):
    amount = abs(amount)
    max_amount = 2_000_000
    normalized = min(amount / max_amount, 1.0)
    
    # Interpolate between salmon (low) and dark red (high)
    # Salmon: #FA8072, Dark Red: #8B0000
    salmon_r, salmon_g, salmon_b = 250, 128, 114
    dark_red_r, dark_red_g, dark_red_b = 139, 0, 0
    
    r = int(salmon_r + (dark_red_r - salmon_r) * normalized)
    g = int(salmon_g + (dark_red_g - salmon_g) * normalized)
    b = int(salmon_b + (dark_red_b - salmon_b) * normalized)
    
    return f"rgb({r}, {g}, {b})"

def hash_password(password):
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return salt + password_hash.hex()

def verify_password(stored_password, provided_password):
    salt = stored_password[:32]
    stored_hash = stored_password[32:]
    password_hash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return stored_hash == password_hash.hex()

def authenticate_user(username, password):
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

def change_password_page():
    st.markdown(
        """
        <div style="text-align: center; padding: 30px 0;">
            <h1 style="color: #4CAF50; font-size: 3.5em; margin-bottom: 10px;">Change Password</h1>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    _, col2, _ = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h3 style='text-align: center; margin-bottom: 30px;'>Update Your Password</h3>", unsafe_allow_html=True)
        
        username = st.text_input("Username", placeholder="Enter your username", key="change_username")
        current_password = st.text_input("Current Password", type="password", placeholder="Enter current password", key="current_password")
        new_password = st.text_input("New Password", type="password", placeholder="Enter new password", key="new_password")
        confirm_new_password = st.text_input("Confirm New Password", type="password", placeholder="Confirm new password", key="confirm_new_password")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Change Password", use_container_width=True, type="primary"):
                if change_password(username, current_password, new_password, confirm_new_password):
                    st.success("Password changed successfully! Redirecting to login...")
                    time.sleep(2)
                    st.session_state.show_change_password = False
                    st.rerun()
        
        with col2:
            if st.button("Back to Login", use_container_width=True, type="secondary"):
                st.session_state.show_change_password = False
                st.rerun()

def login_page():
    st.markdown(
        """
        <div style="text-align: center; padding: 30px 0;">
            <h1 style="color: #4CAF50; font-size: 3.5em; margin-bottom: 10px;">Revolut Analysis Dashboard</h1>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    tab1, tab2, tab3 = st.tabs(["Login", "Register", "👤 Guest Mode"])
    
    with tab1:
        st.markdown("<h3 style='text-align: center; margin-bottom: 30px;'>Login to Your Account</h3>", unsafe_allow_html=True)
        
        _, col2, _ = st.columns([1, 2, 1])
        with col2:
            username = st.text_input("Username", placeholder="Enter your username", key="login_username")
            password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_password")
            
            if st.button("Login", use_container_width=True, type="primary"):
                if authenticate_user(username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.is_guest = False
                    load_user_data(username)
                    st.success("Login successful! Redirecting...")
                    st.rerun()
                else:
                    st.error("Invalid username or password!")
            
            # Change Password Button
            st.markdown("---")
            if st.button("🔐 Change Password", use_container_width=True, type="secondary"):
                st.session_state.show_change_password = True
                st.rerun()
    
    with tab2:
        st.markdown("<h3 style='text-align: center; margin-bottom: 30px;'>Create New Account</h3>", unsafe_allow_html=True)
        
        _, col2, _ = st.columns([1, 2, 1])
        with col2:
            new_username = st.text_input("Choose Username", placeholder="Enter new username", key="reg_username")
            new_password = st.text_input("Choose Password", type="password", placeholder="Enter new password", key="reg_password")
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password", key="reg_confirm")
            
            if st.button("Register", use_container_width=True, type="primary"):
                if register_user(new_username, new_password, confirm_password):
                    st.success("You can now login!")
                    time.sleep(3)
                    st.rerun()
    
    with tab3:
        st.markdown("<h3 style='text-align: center; margin-bottom: 30px;'>Try as Guest</h3>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.info("🎯 **Guest Mode Features:**\n- Upload and analyze your CSV file\n- All dashboard analytics available\n- Data is temporary (not saved)")
            st.warning("⚠️ **Note:** Your data will be lost when you close the browser!")
            
            if st.button("👤 Continue as Guest", use_container_width=True, type="secondary"):
                st.session_state.logged_in = True
                st.session_state.username = "guest"
                st.session_state.is_guest = True
                st.session_state.categories = {"Uncategorized": []}
                st.success("Welcome, Guest! Please upload a CSV file to get started.")
                st.rerun()

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

def main():
    # Initialize session state for change password page
    if "show_change_password" not in st.session_state:
        st.session_state.show_change_password = False
    
    if not st.session_state.logged_in:
        if st.session_state.show_change_password:
            change_password_page()
        else:
            login_page()
        return
    
    if not github_repo and not st.session_state.is_guest:
        st.error("⚠️ GitHub storage not configured. Running in offline mode.")
        st.info("💡 Configure GitHub secrets to enable data persistence.")
    
    with st.sidebar:
        if st.session_state.is_guest:
            st.info("👤 **Guest Mode**\nData is temporary")
        else:
            st.success(f"👋 Welcome, **{st.session_state.username}**!")
            if st.session_state.username == "admin":
                st.info("🛡️ **Admin User**")
        
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.is_guest = False
            st.session_state.categories = {"Uncategorized": []}
            st.rerun()
        st.markdown("---")
    
    if st.session_state.is_guest:
        st.title("Guest Mode - Upload Your Data")
        
        uploaded_file = st.file_uploader("Upload your Revolut statement to get started", type=["csv"])
        
        if uploaded_file is not None:
            guest_df = load_statement(uploaded_file)
            if guest_df is not None:
                st.session_state.guest_dataframe = guest_df
                st.success("File uploaded successfully! You can now use all analytics features.")
            else:
                st.error("Error processing the uploaded file.")
                return
        else:
            st.info("Please upload a CSV file to continue with guest mode.")
            return
    
    page = st.sidebar.radio("Go to", ["Customize Data", "Spending Analytics", "Income Analytics", "User Settings"])

    if page == "Customize Data":
        if st.session_state.is_guest:
            st.title("Data Customization (Guest Mode)")
            if 'guest_dataframe' not in st.session_state:
                st.error("No data available. Please upload a CSV file first.")
                return
            main_df = st.session_state.guest_dataframe.copy()
        else:
            st.title("Main DataFrame")
            main_df = load_main_dataframe()
        
        if main_df is not None:

            col1, _, col2, col3, _ = st.columns([5, 1, 2, 2, 3])

            with col1:
                min_date = main_df['Date'].min().date()
                max_date = main_df['Date'].max().date()
                selected_date_range = st.slider(
                    "Filter by Date",
                    min_date,
                    max_date,
                    (min_date, max_date)
                )

            with col2:
                type_options = ['ALL'] + list(main_df['Type'].unique())
                selected_type = st.selectbox("Filter by Type", options=type_options)
                
            with col3:
                transaction_type_options = ['ALL'] + list(["Credits", "Debits"])
                selected_transaction_type = st.selectbox("Filter by transaction type", options=transaction_type_options)

            if st.checkbox("I'd like to add a new category"):
                col1, _ = st.columns([2, 7])
                with col1:
                    new_category = st.text_input("Enter new category name:")
                    
                st.markdown("> **Note:** To only categorize a single transaction, put '!' at the beginning of the category name. (Not implemented yet)")

                add_button = st.button("Add category")

                if add_button and new_category:
                    if new_category not in st.session_state.categories:
                        st.session_state.categories[new_category] = []
                        save_categories()
                        st.rerun()
                

            if selected_type == 'ALL':
                type_filter = main_df['Type'].notnull()
            else:
                type_filter = main_df['Type'] == selected_type

            if selected_transaction_type == 'ALL':
                transaction_type_filter = main_df['Amount'].notnull()
            elif selected_transaction_type == 'Credits':
                transaction_type_filter = main_df['Amount'] < 0
            elif selected_transaction_type == 'Debits':
                transaction_type_filter = main_df['Amount'] > 0

            filtered_df = main_df[
                (main_df['Date'].dt.date >= selected_date_range[0]) &
                (main_df['Date'].dt.date <= selected_date_range[1]) &
                type_filter &
                transaction_type_filter
            ]

            filtered_df = categorize_transactions(filtered_df)
            filtered_df = filtered_df.sort_values(by='Date', ascending=False)

            column_config = {col: st.column_config.Column(col, disabled=True) for col in filtered_df.columns if col not in ['Hide', 'Amount']}
            column_config['Category'] = st.column_config.SelectboxColumn(
                "Category",
                options=list(st.session_state.categories.keys())
            )
            column_config['Hide'] = st.column_config.CheckboxColumn('Hide')
            column_config['Amount'] = st.column_config.NumberColumn('Amount')

            main_df_to_edit = st.data_editor(filtered_df, column_config=column_config)

            if st.button("Apply Changes"):
                for idx, row in main_df_to_edit.iterrows():
                    new_category = row["Category"]
                    new_hide_status = row["Hide"]
                    new_amount = row["Amount"]
                    details = row["Description"]

                    if new_category != main_df.at[idx, "Category"]:
                        add_keyword_to_category(new_category, details)
                        main_df.at[idx, "Category"] = new_category
                    
                    if new_hide_status != main_df.at[idx, "Hide"]:
                        main_df.at[idx, "Hide"] = new_hide_status
                    
                    if new_amount != main_df.at[idx, "Amount"]:
                        main_df.at[idx, "Amount"] = new_amount

                main_df = categorize_transactions(main_df)
                
                if st.session_state.is_guest:
                    st.session_state.guest_dataframe = main_df
                    st.success("Changes applied to guest session!")
                else:
                    save_main_dataframe(main_df)
                    st.success("Changes saved permanently! Refreshing...")
                    time.sleep(2)
                st.rerun()

        else:
            if st.session_state.is_guest:
                st.error("No data available. Please upload a CSV file first.")
            else:
                st.error("No data available to edit, please upload a CSV file.")

        if not st.session_state.is_guest:
            col1, _ = st.columns([1, 2])

            with col1:
                upload_file = st.file_uploader("Upload your new Revolut statement", type=["csv"])
                if upload_file is not None:
                    new_df = load_statement(upload_file)
                    if new_df is not None:
                        if main_df is not None:
                            updated_df, num_new_rows = merge_dataframes(main_df, new_df)
                        else:
                            updated_df = new_df
                            num_new_rows = len(new_df)
                        
                        save_main_dataframe(updated_df)

                        if num_new_rows == 0:
                            st.info("No new rows to merge. The main DataFrame is already up to date.")
                        else:
                            st.info(f"Successfully added {num_new_rows} new rows into the main DataFrame. Refresh the page!")
                            st.info("Due to streamlits limitations, you will be asked to login again!")
                            st.toast("Data successfully uploaded! Refresh the page and login", icon="🔄")             

    if page == "Spending Analytics":
        st.title("Spending Analytics")
        
        main_df = load_main_spending_dataframe()

        if main_df is not None:
            spending_df = main_df[main_df['Amount'] < 0].copy()

            col1, _, col2 = st.columns([4, 1, 9])
            with col1:
                min_date = spending_df['Date'].min().date()
                max_date = spending_df['Date'].max().date()
                selected_date_range = st.slider(
                    "Filter by Date",
                    min_date,
                    max_date,
                    (
                        (max_date.replace(day=7) - pd.DateOffset(months=1)).date(),
                        max_date
                    )
                )

            filtered_spending_df = spending_df[
                (spending_df['Date'].dt.date >= selected_date_range[0]) &
                (spending_df['Date'].dt.date <= selected_date_range[1])
            ]

            with col2:    
                total_spending = filtered_spending_df['Amount'].sum()
                spending_color = get_spending_color(total_spending)
                
                st.markdown(
                    f"""
                    <div style="
                        background-color: transparent;
                        padding: 15px;
                        border-radius: 10px;
                        text-align: center;
                        font-weight: bold;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        display: inline-block;
                        width: auto;
                    ">
                        <div style="font-size: 32px; color: white;">
                            Total spent in the selected period: <span style="color: {spending_color};">{abs(total_spending):,.0f} Ft</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            if st.checkbox("Show all spending data"):
                st.dataframe(filtered_spending_df)

            # Monthly spending metrics
            col1, col2, col3 = st.columns(3)
            monthly_spending = filtered_spending_df.copy()
            monthly_spending['Date'] = monthly_spending['Date'].dt.to_period('M').dt.to_timestamp()
            monthly_spending = monthly_spending.groupby('Date')['Amount'].sum().reset_index()
            monthly_spending['Amount'] = monthly_spending['Amount'].abs()
            monthly_spending = monthly_spending.sort_values(by='Date', ascending=False)
            monthly_spending['Amount_Label'] = monthly_spending['Amount'].apply(
                lambda x: f'{x/1000:.0f}k Ft' if x >= 1000 else f'{x:.0f} Ft'
            )
            for i in range(3):
                if i < len(monthly_spending):
                    month_data = monthly_spending.iloc[i]
                    with col1 if i == 0 else col2 if i == 1 else col3:
                        st.metric(
                            label=month_data['Date'].strftime('%B %Y'),
                            value=month_data['Amount_Label'],
                            delta = f"{int(monthly_spending.iloc[i]['Amount'] - (monthly_spending.iloc[i+1]['Amount'] if i+1 < len(monthly_spending) else 0))} Ft",
                            delta_color = "inverse"
                        )
                else:
                    with col1 if i == 0 else col2 if i == 1 else col3:
                        st.metric(label="No data", value="0 Ft", delta="0 Ft")

            if st.checkbox("Show spending for specific month(s)"):
                col1, col2, _ = st.columns([1, 1, 3])
                with col1:
                    year_options = spending_df['Date'].dt.year.unique()
                    selected_years = st.multiselect("Select Years", options=sorted(year_options, reverse=True))
                with col2:
                    month_options = list(range(1, 13))
                    month_names = [pd.Timestamp(2000, i, 1).strftime('%B') for i in month_options]
                    selected_months = st.multiselect("Select Months", 
                                                   options=month_options,
                                                   format_func=lambda x: month_names[x-1])
                
                if selected_years and selected_months:
                    selected_spending = []
                    selected_labels = []
                    
                    for year in selected_years:
                        for month in selected_months:
                            month_data = spending_df[
                                (spending_df['Date'].dt.year == year) & 
                                (spending_df['Date'].dt.month == month)
                            ]
                            spending_amount = abs(month_data['Amount'].sum())
                            selected_spending.append(spending_amount)
                            
                            month_name = pd.Timestamp(year, month, 1).strftime('%B %Y')
                            selected_labels.append(month_name)
                    
                    num_results = len(selected_spending)
                    rows_needed = (num_results + 2) // 3
                    
                    for row in range(rows_needed):
                        cols = st.columns(3)
                        for col_idx in range(3):
                            result_idx = row * 3 + col_idx
                            if result_idx < num_results:
                                with cols[col_idx]:
                                    st.metric(
                                        label=selected_labels[result_idx],
                                        value=f"{selected_spending[result_idx]:,.0f} Ft"
                                    )

            # Balance over time line chart
            balance_chart_data = main_df[
                (main_df['Product'] == 'Current') &
                (main_df['Date'].dt.date >= selected_date_range[0]) &
                (main_df['Date'].dt.date <= selected_date_range[1])
            ].copy()

            balance_chart_data = balance_chart_data.sort_values(by='Date')

            if not balance_chart_data.empty:
                fig_balance_over_time = px.area(
                    balance_chart_data,
                    x='Date',
                    y='Balance',
                    title='Account Balance Over Time',
                    markers=True,
                    hover_data={'Description': True}
                )
                fig_balance_over_time.update_traces(
                    hovertemplate='Date: %{x}<br>Balance: %{y}<br>Description: %{customdata[0]}<extra></extra>'
                )
                st.plotly_chart(fig_balance_over_time, use_container_width=True)
            else:
                st.write("No 'Current' account balance data to display for the selected period.")
            
            col1, _ = st.columns([1, 5])
            with col1:
                spending_ot_selector = st.selectbox(
                    "Spending Over Time",
                    options=("Individual Transactions", "Daily", "Weekly")
                )

            if spending_ot_selector == "Individual Transactions":
                individual_spending = filtered_spending_df.copy()
                individual_spending['Amount'] = individual_spending['Amount'].abs()
                individual_spending = individual_spending.sort_values(by='Date')
                
                threshold = individual_spending['Amount'].quantile(0.9)
                individual_spending['Color'] = individual_spending['Amount'].apply(
                    lambda x: 'red' if x >= threshold else 'white'
                )

                fig_daily_spending = px.scatter(
                    individual_spending,
                    x='Date',
                    y='Amount',
                    title='Individual Spending Over Time',
                    hover_data={'Description': True, 'Color': False},
                    color='Color',
                    color_discrete_map={'red': "#FF5A3D", 'white': '#FFFFFF'}
                )
                fig_daily_spending.update_traces(
                    marker=dict(size=7),
                    hovertemplate='Date: %{x}<br>Amount: %{y}<br>Description: %{customdata[0]}<extra></extra>'
                )
                fig_daily_spending.update_layout(
                    yaxis_type="log",
                    xaxis=dict(nticks=20),
                    showlegend=False
                )
                st.plotly_chart(fig_daily_spending, use_container_width=True)

            if spending_ot_selector == "Daily":
                daily_spending = filtered_spending_df.groupby(filtered_spending_df['Date'].dt.date)['Amount'].sum().reset_index()
                daily_spending['Amount'] = daily_spending['Amount'].abs()
                daily_spending = daily_spending.sort_values(by='Date')
                daily_spending['Amount Label'] = daily_spending['Amount'].apply(lambda x: f'{x/1000:.0f}k' if x >= 1000 else f'{x:.0f}')
                fig_daily_spending = px.scatter(
                    daily_spending,
                    x='Date',
                    y='Amount',
                    title='Spending Over Time',
                    text='Amount Label'
                )
                fig_daily_spending.update_traces(
                    marker=dict(size=7,color='white'),
                    textposition='bottom center',
                    textfont=dict(size=14, color='white'),
                    hovertemplate='Date: %{x}<br>Amount: %{y}<extra></extra>'
                )
                fig_daily_spending.update_layout(
                    yaxis_type="log",
                    xaxis=dict(
                        tickvals=daily_spending['Date'],
                        ticktext=[date.strftime('%m %d') for date in daily_spending['Date']],
                        tickangle=45
                    )
                )
                st.plotly_chart(fig_daily_spending, use_container_width=True)

                if st.checkbox("Show heatmap"):
                    daily_spending['Date'] = pd.to_datetime(daily_spending['Date'])
                    daily_spending['Day_of_Week'] = daily_spending['Date'].dt.day_name()
                    daily_spending['Week'] = daily_spending['Date'].dt.isocalendar().week
                    daily_spending['Month'] = daily_spending['Date'].dt.strftime('%Y-%m')
                    
                    sorted_months = sorted(daily_spending['Month'].unique())
                    
                    num_months = len(sorted_months)
                    if num_months == 1:
                        cols = st.columns([1, 1])  # Half screen
                        col_positions = [0]
                    elif num_months == 2:
                        cols = st.columns(2)  # Side by side
                        col_positions = [0, 1]
                    elif num_months == 3:
                        cols = st.columns(2)  # Three columns
                        col_positions = [0, 1, 0]
                    elif num_months == 4:
                        cols = st.columns(2)  # 2x2 layout
                        col_positions = [0, 1, 0, 1]
                    else:
                        cols = st.columns(2)  # 2x3 layout
                        col_positions = [i % 2 for i in range(num_months)]
                    
                    for i, month in enumerate(sorted_months):
                        month_data = daily_spending[daily_spending['Month'] == month]
                        
                        heatmap_data = month_data.pivot_table(
                            index='Week',
                            columns='Day_of_Week',
                            values='Amount',
                            fill_value=0
                        )
                        
                        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                        heatmap_data = heatmap_data.reindex(columns=day_order, fill_value=0)
                        
                        fig_heatmap_daily = px.imshow(
                            heatmap_data,
                            color_continuous_scale=[[0, '#2F2F2F'], [0.1, '#8B0000'], [1, '#FF0000']],
                            title=f'\t\t\t\t\tDaily Spending Heatmap - {month}',
                            aspect='equal'
                        )
                        fig_heatmap_daily.update_layout(
                            xaxis_title=None,
                            yaxis_title='Week of Year',
                            xaxis=dict(tickmode='array', tickvals=list(range(len(day_order))), ticktext=day_order),
                            yaxis=dict(tickmode='linear', dtick=1),
                            plot_bgcolor='#1E1E1E',
                            paper_bgcolor='#1E1E1E',
                            font=dict(color='white')
                        )
                        fig_heatmap_daily.update_traces(
                            hovertemplate='Day: %{x}<br>Week: %{y}<br>Amount: %{z:.0f} Ft<extra></extra>'
                        )

                        with cols[col_positions[i]]:
                            st.plotly_chart(fig_heatmap_daily, use_container_width=True)
                    

            if spending_ot_selector == "Weekly":
                weekly_spending = filtered_spending_df.copy()
                weekly_spending['Amount'] = weekly_spending['Amount'].abs()
                weekly_spending['Week'] = weekly_spending['Date'].dt.to_period('W').dt.start_time
                weekly_spending = weekly_spending.groupby('Week')['Amount'].sum().reset_index()
                weekly_spending = weekly_spending.sort_values(by='Week')
                weekly_spending['Amount_Label'] = weekly_spending['Amount'].apply(
                    lambda x: f'{x/1000:.0f}k' if x >= 1000 else f'{x:.0f}'
                )
                fig_weekly_spending = px.bar(
                    weekly_spending,
                    x='Week',
                    y='Amount',
                    title='Weekly Spending',
                    text='Amount_Label',
                    labels={'Week': 'Week', 'Amount': 'Weekly Spending (Ft)'},
                )
                fig_weekly_spending.update_traces(
                    textposition='inside',
                    textfont=dict(size=18, color='black'),
                    hovertemplate='Week: %{x}<br>Weekly Spending: %{y}<extra></extra>'
                )
                
                st.plotly_chart(fig_weekly_spending, use_container_width=True)

            # Spending add-up over time and top 10 transactions
            col1, col2 = st.columns([3,2])
            with col1:
                individual_spending = filtered_spending_df.copy()
                individual_spending['Amount'] = individual_spending['Amount'].abs()
                individual_spending = individual_spending.sort_values(by='Date')
                individual_spending['CumSum'] = individual_spending['Amount'].cumsum()
                fig_spending_add_up = px.line(
                    individual_spending,
                    x='Date',
                    y='CumSum',
                    title='Cumulative Spending Over Time',
                    markers=True,
                    hover_data={'Description': True}
                )
                fig_spending_add_up.update_layout(
                    yaxis_title=None,
                    xaxis_title='Date',
                )
                fig_spending_add_up.update_traces(
                    marker=dict(size=7),
                    hovertemplate='Date: %{x}<br>Total: %{y}<br>Description: %{customdata[0]}<extra></extra>'
                )
                fig_spending_add_up.update_traces(customdata=individual_spending[['Description']].values)
                st.plotly_chart(fig_spending_add_up, use_container_width=True)

            with col2:
                top_10_spending = filtered_spending_df.copy()
                top_10_spending['Amount'] = top_10_spending['Amount'].abs()
                top_10_spending = top_10_spending.sort_values(by='Amount', ascending=False).head(10)


                col1, _, col2 = st.columns([2, 1, 1])
                with col1:
                    st.markdown("<h6>10 Largest Transactions</h6>", unsafe_allow_html=True)
                with col2:
                    show_dates_checkbox = st.checkbox("Show Dates")

                if show_dates_checkbox:
                    st.dataframe(top_10_spending[['Description', 'Amount', 'Date']], hide_index=True)
                else:
                    st.dataframe(top_10_spending[['Description', 'Amount']], hide_index=True)

    if page == "Income Analytics":
        st.title("Income Analytics")

        if st.session_state.is_guest:
            if 'guest_dataframe' not in st.session_state:
                st.error("No data available. Please upload a CSV file first.")
                return
            main_df = st.session_state.guest_dataframe.copy()
        else:
            main_df = load_main_dataframe()
            
        if main_df is None:
            st.error("No data available for income analytics.")
            return

        income_df = main_df[main_df['Amount'] > 0].copy()
        income_df = income_df[income_df['Hide'] == False]
        income_df = income_df[income_df['Product'] == 'Current']

        savings_df = main_df[main_df['Product'] == 'Deposit'].copy()
        savings_df = savings_df[savings_df['Hide'] == False]
        savings_df = savings_df.sort_values(by='Date')

        monthly_incomes = []
        monthly_savings = []
        for i in range(4):
            month_num = (pd.Timestamp.now().month - i - 1) % 12 + 1 
            month_data = income_df[income_df['Date'].dt.month == month_num]
            monthly_incomes.append(month_data['Amount'].sum())

            if i != 4:
                month_num = (pd.Timestamp.now().month - i - 1) % 12 + 1 
                saving_month_data = savings_df[savings_df['Date'].dt.month == month_num]
                saving_month_data = saving_month_data[saving_month_data['Amount'] > 0]
                monthly_savings.append(saving_month_data['Amount'].sum())

        col1, col2, col3 = st.columns(3)
        columns = [col1, col2, col3]

        for i in range(3):
            with columns[i]:
                month_date = pd.Timestamp.now() - pd.DateOffset(months=i)
                month_name = month_date.strftime('%B')
                current_income = monthly_incomes[i]
                previous_income = monthly_incomes[i + 1] if i + 1 < len(monthly_incomes) else 0
                
                st.metric(
                    label=f"{month_name} Income",
                    value=f"{current_income:,.0f} Ft",
                    delta=f"{current_income - previous_income:,.0f} Ft"
                )

                st.metric(
                    label=f"{month_name} Savings",
                    value=f"{monthly_savings[i]:,.0f} Ft",
                    delta=f"{monthly_savings[i] - (monthly_savings[i + 1] if i + 1 < len(monthly_savings) else 0):,.0f} Ft"
                )

                st.metric(
                    label=f"{month_name} Savings in %",
                    value=f"{(monthly_savings[i] / current_income * 100):.1f}%",
                    delta=f"{((monthly_savings[i] - (monthly_savings[i + 1] if i + 1 < len(monthly_savings) else 0)) / previous_income * 100):.1f}%"
                )

        if st.checkbox("Show income for specific month(s)"):
            col1, col2, _ = st.columns([1, 1, 3])
            with col1:
                year_options = income_df['Date'].dt.year.unique()
                selected_years = st.multiselect("Select Years", options=sorted(year_options, reverse=True))
            with col2:
                month_options = list(range(1, 13))
                month_names = [pd.Timestamp(2000, i, 1).strftime('%B') for i in month_options]
                selected_months = st.multiselect("Select Months", 
                                               options=month_options,
                                               format_func=lambda x: month_names[x-1])
            
            if selected_years and selected_months:
                selected_incomes = []
                selected_labels = []
                
                for year in selected_years:
                    for month in selected_months:
                        month_data = income_df[
                            (income_df['Date'].dt.year == year) & 
                            (income_df['Date'].dt.month == month)
                        ]
                        income_amount = month_data['Amount'].sum()
                        selected_incomes.append(income_amount)
                        
                        month_name = pd.Timestamp(year, month, 1).strftime('%B %Y')
                        selected_labels.append(month_name)
                
                num_results = len(selected_incomes)
                rows_needed = (num_results + 2) // 3
                
                for row in range(rows_needed):
                    cols = st.columns(3)
                    for col_idx in range(3):
                        result_idx = row * 3 + col_idx
                        if result_idx < num_results:
                            with cols[col_idx]:
                                st.metric(
                                    label=selected_labels[result_idx],
                                    value=f"{selected_incomes[result_idx]:,.0f} Ft"
                                )
    
        fig_savings = px.line(
            savings_df,
            x='Date',
            y='Balance',
            title='Savings Account Balance Over Time',
        )
        fig_savings.update_traces(
            hovertemplate='Date: %{x}<br>Balance: %{y}<extra></extra>'
        )
        st.plotly_chart(fig_savings, use_container_width=True)

    if page == "User Settings":
        st.title("User Settings")
        
        if st.session_state.is_guest:
            st.info("👤 **Guest Mode**")
            st.write("Guest users don't have persistent data to manage. Your data is temporary and will be cleared when you close the browser.")
            return
        
        st.markdown("### Account Management")
        
        # User info
        st.info(f"**Current User:** {st.session_state.username}")
        
        # Change Password Section
        st.markdown("#### Change Password")
        with st.expander("🔐 Change Your Password"):
            col1, col2 = st.columns(2)
            with col1:
                old_password = st.text_input("Current Password", type="password", key="settings_old_password")
                new_password = st.text_input("New Password", type="password", key="settings_new_password")
                confirm_new_password = st.text_input("Confirm New Password", type="password", key="settings_confirm_password")
            
            if st.button("Update Password", type="primary"):
                if change_password(st.session_state.username, old_password, new_password, confirm_new_password):
                    st.success("Password updated successfully!")
                    time.sleep(2)
                    st.rerun()
        
        st.markdown("---")
        
        # Data Management Section
        st.markdown("#### Data Management")
        
        # Show data info
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Your Data:**")
            files = get_user_files(st.session_state.username)
            
            # Check if files exist
            dataframe_exists = read_encrypted_github_file(files["dataframe"], st.session_state.username) is not None
            categories_exists = read_encrypted_github_file(files["categories"], st.session_state.username) is not None
            
            if dataframe_exists:
                st.write("✅ Transaction data")
            else:
                st.write("❌ No transaction data")
            
            if categories_exists:
                st.write("✅ Categories data")
                st.write(f"📊 {len(st.session_state.categories)} categories configured")
            else:
                st.write("❌ No categories data")
        
        with col2:
            st.markdown("**Storage Location:**")
            st.write(f"📁 Dataframe: `{files['dataframe']}`")
            st.write(f"📁 Categories: `{files['categories']}`")
            st.write(f"🔐 Data is encrypted with your password")
        
        st.markdown("---")
        
        # Danger Zone
        st.markdown("#### ⚠️ Danger Zone")
        
        with st.expander("🗑️ Delete All User Data", expanded=False):
            st.error("**WARNING: This action cannot be undone!**")
            st.write("This will permanently delete:")
            st.write("- All your transaction data")
            st.write("- All your categories and settings") 
            st.write("- Your user account")
            st.write("- You will be logged out immediately")
            
            st.markdown("**To confirm deletion, type your username below:**")
            confirmation_username = st.text_input("Enter your username to confirm:", key="delete_confirmation")
            
            if confirmation_username == st.session_state.username:
                if st.button("🗑️ DELETE ALL MY DATA", type="primary", help="This will permanently delete all your data"):
                    with st.spinner("Deleting your data..."):
                        success, message = delete_user_data(st.session_state.username)
                        
                    if success:
                        st.success("✅ All your data has been successfully deleted.")
                        st.info("You will be logged out in 3 seconds...")
                        time.sleep(3)
                        
                        # Log out the user
                        st.session_state.logged_in = False
                        st.session_state.username = None
                        st.session_state.is_guest = False
                        st.session_state.categories = {"Uncategorized": []}
                        
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to delete data: {message}")
            elif confirmation_username:
                st.warning("⚠️ Username doesn't match. Please type your exact username to confirm deletion.")
            
            if not confirmation_username:
                st.button("🗑️ DELETE ALL MY DATA", disabled=True, help="Enter your username to enable this button")

         
main()