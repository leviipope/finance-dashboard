"""Authentication pages for login, registration, and password management."""

import time
import streamlit as st
from ..auth.authentication import authenticate_user, register_user, change_password
from ..data.processing import load_user_data


def change_password_page():
    """Page for changing user password"""
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
    """Main login page with tabs for login, register, and guest mode"""
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
            with st.form("login_form"):
                username = st.text_input("Username", placeholder="Enter your username", key="login_username")
                password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_password")
                login = st.form_submit_button("Login", use_container_width=True, type="primary")

            if login:
                if authenticate_user(username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.is_guest = False
                    st.session_state.show_welcome_toast = True
                    load_user_data(username)
                    st.success("Login successful! Redirecting...")
                    st.rerun()
                else:
                    st.error("Invalid username or password!")
            
            # Change Password Button
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
            st.info("🎯 **Guest Mode Features:**\n- Upload (or pick demo) and analyze your CSV file\n- All dashboard analytics available\n- Data is temporary (not saved)\n- HUF is assumed")
            st.warning("⚠️ **Note:** Your data will be lost when you close the browser!")
            
            if st.button("👤 Continue as Guest", use_container_width=True, type="secondary"):
                st.session_state.logged_in = True
                st.session_state.username = "guest"
                st.session_state.is_guest = True
                st.session_state.categories = {"Uncategorized": []}
                st.success("Welcome, Guest! Please upload a CSV file to get started.")
                st.rerun()

    st.markdown("---")
    st.markdown(
        """
        <style>
        .footer {
            position: fixed;
            bottom: 0;
            width: 100%;
            padding: 10px 0;
            text-align: center;
            left: 0;
            z-index: 999;
        }
        .content {
            margin-bottom: 60px; /* Add space for footer */
        }
        </style>
        
        <div class="content"></div>
        
        <div class="footer">
            <p style="color: #666; font-size: 0.9em; margin: 0;">
                Developed by Polgari Levente | 
                <a href="https://github.com/leviipope" target="_blank">Github</a> | 
                <a href="https://leviipope.github.io/cv-website" target="_blank">Website</a> | 
                <a href="https://www.linkedin.com/in/levente-polg%C3%A1ri-9681a0303/" target="_blank">LinkedIn</a>
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
