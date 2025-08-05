"""
Financial Dashboard - Main Application Entry Point

A modular Streamlit application for analyzing Revolut financial data.
This refactored version separates concerns into different modules for better maintainability.
"""

import streamlit as st
from src.pages.auth_pages import login_page, change_password_page
from src.pages.customize_data import customize_data_page
from src.data.github_storage import github_repo
from src.data.processing import load_statement

# Set page configuration
st.set_page_config(
    page_title="Financial Dashboard", 
    page_icon=":money_with_wings:", 
    layout="wide"
)

# Initialize session state
def initialize_session_state():
    """Initialize session state variables"""
    defaults = {
        "logged_in": False,
        "username": None,
        "is_guest": False,
        "categories": {"Uncategorized": []},
        "show_change_password": False,
        "show_welcome_toast": False
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def guest_file_upload():
    """Handle file upload for guest users"""
    st.title("Guest Mode - Upload Your Data")
    
    uploaded_file = st.file_uploader("Upload your Revolut statement to get started", type=["csv"])
    
    if uploaded_file is not None:
        guest_df = load_statement(uploaded_file)
        if guest_df is not None:
            st.session_state.guest_dataframe = guest_df
            st.success("File uploaded successfully! You can now use all analytics features.")
            return True
        else:
            st.error("Error processing the uploaded file.")
            return False
    else:
        st.info("Please upload a CSV file to continue with guest mode.")
        return False


def main_sidebar():
    """Render the main sidebar with user info and logout"""
    with st.sidebar:
        if st.session_state.is_guest:
            st.info("👤 **Guest Mode**\nData is temporary")
        else:
            if st.session_state.username == "admin":
                st.info("🛡️ **Admin User**")
        
        if st.button("Logout"):
            # Reset session state
            for key in ["logged_in", "username", "is_guest", "guest_dataframe", "show_welcome_toast"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.categories = {"Uncategorized": []}
            st.rerun()
        st.markdown("---")


def main_app():
    """Main application logic"""
    initialize_session_state()
    
    # Handle authentication flow
    if not st.session_state.logged_in:
        if st.session_state.show_change_password:
            change_password_page()
        else:
            login_page()
        return
    
    # Show GitHub storage warning for non-guest users
    if not github_repo and not st.session_state.is_guest:
        st.error("⚠️ GitHub storage not configured. Running in offline mode.")
        st.info("💡 Configure GitHub secrets to enable data persistence.")

    # Show welcome toast once after login
    if st.session_state.get("show_welcome_toast", False):
        st.toast(f"👋 Welcome, **{st.session_state.username}**!")
        st.session_state.show_welcome_toast = False

    # Render sidebar
    main_sidebar()
    
    # Handle guest mode file upload
    if st.session_state.is_guest:
        if not guest_file_upload():
            return
    
    # Main navigation
    page = st.sidebar.radio(
        "Go to", 
        ["Customize Data", "Spending Analytics", "Income Analytics", "User Settings"]
    )

    # Route to appropriate page
    if page == "Customize Data":
        customize_data_page()
    elif page == "Spending Analytics":
        # Import and call spending analytics page
        from src.pages.spending_analytics import spending_analytics_page
        spending_analytics_page()
    elif page == "Income Analytics":
        # Import and call income analytics page
        from src.pages.income_analytics import income_analytics_page
        income_analytics_page()
    elif page == "User Settings":
        # Import and call user settings page
        from src.pages.user_settings import user_settings_page
        user_settings_page()


if __name__ == "__main__":
    main_app()
