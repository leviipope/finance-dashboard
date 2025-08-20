"""User settings page for account management."""

import streamlit as st
import time
from ..data.github_storage import delete_user_data
from ..auth.authentication import change_password
from ..data.github_storage import get_user_files, read_encrypted_github_file
from ..utils.currency import get_user_currency


def user_settings_page():
    """User settings and account management page"""
    st.title("User Settings")
    
    if st.session_state.is_guest:
        st.info("👤 You are in Guest Mode. Settings are not available.")
        st.write("Guest users don't have persistent data to manage. Your data is temporary and will be cleared when you close the browser.")
        st.write("Guest mode features:")
        st.write("- ✅ Upload and analyze CSV files")
        st.write("- ✅ All analytics features")
        st.write("- ❌ Data persistence")
        st.write("- ❌ User settings")
        return
    
    username = st.session_state.username
    
    st.info(f"**Current User:** {username}")
    
    st.subheader("Category Overview")
    
    if st.session_state.categories:
        st.write("**Your Categories:**")
        for category, keywords in st.session_state.categories.items():
            if category != "Uncategorized":
                with st.expander(f"📁 {category} ({len(keywords)} keywords)"):
                    if keywords:
                        for keyword in keywords:
                            st.write(f"• {keyword}")
                    else:
                        st.write("No keywords defined")
    
    with st.expander("➕ Add New Category"):
        new_category = st.text_input("Category Name")
        if st.button("Create Category") and new_category:
            if new_category not in st.session_state.categories:
                st.session_state.categories[new_category] = []
                from ..data.processing import save_categories
                save_categories()
                st.success(f"Category '{new_category}' created!")
                st.rerun()
            else:
                st.error("Category already exists!")
    
    st.markdown("---")
    
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
            total_keywords = sum(len(keywords) for cat, keywords in st.session_state.categories.items() if cat != "Uncategorized")
            st.write(f"📊 Total keywords: {total_keywords}")
        else:
            st.write("❌ No categories data")
    
    with col2:
        st.markdown("**Storage Location:**")
        st.write(f"📁 Dataframe: `{files['dataframe']}`")
        st.write(f"📁 Categories: `{files['categories']}`")
        st.write(f"🔐 Data is encrypted with your password")
    
    st.markdown("---")

    # Danger zone
    st.subheader("⚠️ Danger Zone")
    
    with st.expander("🗑️ Delete All User Data", expanded=False):
        st.error("**WARNING: This action cannot be undone!**")
        st.write("This will permanently delete:")
        st.write("- Your user account")
        st.write("- All your financial data")
        st.write("- All your categories")
        
        confirm_text = st.text_input(
            f"Type '{username}' to confirm deletion:",
            placeholder=f"Type {username} here"
        )

        delete_button = st.button("🗑️ Delete My Account", type="primary", disabled=(confirm_text != username))
        
        if delete_button:
            if username == "admin":
                st.error("Admin account cannot be deleted!")
            else:
                with st.spinner("Deleting your account..."):
                    success, message = delete_user_data(username)
                if success:
                    st.success("Account deleted successfully!")
                    st.info("You will be logged out in 3 seconds...")
                    time.sleep(3)
                    # Reset session state
                    for key in ["logged_in", "username", "is_guest"]:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.session_state.categories = {"Uncategorized": []}
                    st.rerun()
                else:
                    st.error(f"Failed to delete account: {message}")
    
    st.markdown("---")
    
    # Currency Information Section
    st.markdown("#### Currency Information")
    
    current_currency = get_user_currency(st.session_state.username)
    st.info(f"**Chosen Currency:** {current_currency}")

    st.markdown("---")

    # App information
    st.subheader("ℹ️ About")
    st.write("**Revolut Analysis Dashboard**")
    st.write("Version: 2.0.0 (Modular)")
    st.write("A personal finance dashboard for analyzing Revolut transaction data.")
    
    with st.expander("🔧 Technical Details"):
        st.write("**Architecture:**")
        st.write("- Frontend: Streamlit")
        st.write("- Data Storage: GitHub")
        st.write("- Encryption: Fernet (AES 128)")
        st.write("- Charts: Plotly")
        st.write("- Data Processing: Pandas")
        
        st.write("**Security Features:**")
        st.write("- User data encryption")
        st.write("- Password hashing (PBKDF2)")
        st.write("- Session management")
        st.write("- Guest mode isolation")
