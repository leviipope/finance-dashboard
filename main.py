from unicodedata import category

import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os

st.set_page_config(page_title="Simple finance app", page_icon=":money_with_wings:", layout="wide") # Set the page title and icon

category_file = "categories.json"

if "catergories" not in st.session_state:
    st.session_state.catergories = {
        "Uncategorized": []
    }

if os.path.exists(category_file):
    with open(category_file, "r") as f:
        st.session_state.catergories = json.load(f) # Load categories from JSON file

def save_categories():
    with open(category_file, "w") as f:
        json.dump(st.session_state.catergories, f) # Save categories to JSON file

def categorize_transactions(df):
    df["Category"] = "Uncategorized"

    for category, keywords in st.session_state.catergories.items():
        if category == "Uncategorized" or not keywords: # We're not going to categorize anything as uc. and if we don't have anything (keywords) to c.  then we can't do anything
            continue

        lowered_keywords = [keyword.lower().strip() for keyword in keywords]

        for idx, row in df.iterrows():
            details = row["Deatils"].lower().strip()
            if details in lowered_keywords:
                df.at[idx, "Category"] = category

    return df

def load_transactions(file):
    try:
        df = pd.read_csv(file) # Read the CSV file into a DataFrame
        df.columns = [col.strip() for col in df.columns] # Strip whitespace from column names
        df['Amount'] = df['Amount'].str.replace(',', '').astype(float) # Convert the 'Amount' column to float
        df['Date'] = pd.to_datetime(df['Date'], format='%d %b %Y') # Convert 'Date' column to datetime

        return categorize_transactions(df)
    except Exception as e:
        st.error(f"Error reading the file: {str(e)}")
        return None

def add_keyword_to_category(category, keyword):
    keyword = keyword.strip()
    if keyword and keyword not in st.session_state.catergories[category]:
        st.session_state.catergories[category].append(keyword)
        save_categories()
        return True

    return False

def main():
    st.title("Simple Finance App") # Set the title of the app

    upload_file = st.file_uploader("Upload a CSV file", type=["csv"]) # File uploader for CSV files

    if upload_file is not None:
        df  = load_transactions(upload_file)

        if df is not None:
            debits_df = df[df['Debit/Credit'] == 'Debit'].copy() # Pandas filter operation for debits
            credits_df = df[df['Debit/Credit'] == 'Credit'].copy()

            tab1, tab2 = st.tabs(["Expenses (Debits)", "Payments (Credits)"]) # Create tabs for debits and credits
            with tab1:
                new_category = st.text_input("New category name")
                add_button = st.button("Add category")

                if add_button and new_category: # If new category has some value inside of it AND we pressed the button
                    if new_category not in st.session_state.catergories:
                        st.session_state.catergories[new_category] = []
                        save_categories()
                        st.rerun()

                st.write(debits_df)

            with tab2:
                st.write(credits_df)

main()