"""Data processing functionality for financial data."""

import pandas as pd
import streamlit as st
import json
from datetime import datetime
from io import StringIO
from ..utils.currency import detect_currency_from_df, CURRENCY_DECIMALS
from ..data.github_storage import (
    read_encrypted_github_file, 
    write_encrypted_github_file, 
    get_user_files,
    ensure_github_file_exists
)


def load_user_data(username):
    """Load user's categories and other data"""
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


def load_statement(file):
    """Load and process a CSV statement file"""
    try: 
        df = pd.read_csv(file)
        
        # Detect currency before dropping the Currency column
        detected_currency = detect_currency_from_df(df)
        
        # Store the detected currency for the current user in session state
        if st.session_state.get("username"):
            if st.session_state.is_guest:
                st.session_state['currency'] = detected_currency
            else:
                st.session_state[f"{st.session_state.username}_currency"] = detected_currency
        
        # Drop columns that exist in the dataframe
        columns_to_drop = []
        for col in ["Fee", "Completed Date", "Currency", "State"]:
            if col in df.columns:
                columns_to_drop.append(col)
        
        if columns_to_drop:
            df = df.drop(columns_to_drop, axis=1)
            
        df = df[df["Type"] != "INTEREST"]
        df['Started Date'] = pd.to_datetime(df['Started Date'])
        df = df.rename(columns={"Started Date": "Date"})

        df["Hide"] = False 
        # Update currency-specific hiding rules to be more generic
        df.loc[df['Description'].str.contains(f'To {detected_currency}', case=False, na=False), 'Hide'] = True
        df.loc[df['Description'] == 'Transfer from Revolut user', 'Hide'] = True
        df.loc[(df['Product'] == 'Current') & (df['Description'] == 'From Savings Account'), 'Hide'] = True
        df.loc[(df['Product'] == 'Current') & (df['Description'] == 'To Savings Account'), 'Hide'] = True

        # Round amounts based on currency decimal rules
        decimals = CURRENCY_DECIMALS.get(detected_currency, 2)
        if decimals == 0:
            df['Amount'] = df['Amount'].round().astype(int)
        else:
            df['Amount'] = df['Amount'].round(decimals)

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
    """Load the main dataframe for the current user"""
    if st.session_state.is_guest:
        return None
    
    files = get_user_files(st.session_state.username)
    csv_content = read_encrypted_github_file(files["dataframe"], st.session_state.username)
    
    if csv_content:
        try:
            df = pd.read_csv(StringIO(csv_content))
            df['Date'] = pd.to_datetime(df['Date'])
            return df
        except Exception as e:
            st.error(f"Error loading dataframe: {str(e)}")
            return None
    else:
        return None


def load_main_spending_dataframe():
    """Load main dataframe filtered for spending analysis"""
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
    """Merge new data with existing dataframe"""
    combined_df = pd.concat([main_df, new_df]).drop_duplicates(subset=['Date', 'Description', 'Balance'], keep='first')
    num_new_rows = len(combined_df) - len(main_df)
    return combined_df, num_new_rows


def save_main_dataframe(df):
    """Save the main dataframe"""
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
    """Save user categories"""
    if st.session_state.is_guest:
        return
    
    files = get_user_files(st.session_state.username)
    categories_content = json.dumps(st.session_state.categories, indent=2)
    
    commit_message = f"Update categories for user {st.session_state.username} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    success = write_encrypted_github_file(files["categories"], categories_content, commit_message, st.session_state.username)


def categorize_transactions(df):
    """Categorize transactions based on user-defined categories"""
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
    """Add a keyword to a category"""
    keyword = keyword.strip()
    if keyword and keyword not in st.session_state.categories.get(category, []):
        st.session_state.categories[category].append(keyword)
        save_categories()
        return True
    return False
