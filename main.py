import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os

st.set_page_config(page_title="Simple finance app", page_icon=":money_with_wings:", layout="wide") # Set the page title and icon

def load_transactions(file):
    try:
        df = pd.read_csv(file) # Read the CSV file into a DataFrame
        df.columns = [col.strip() for col in df.columns] # Strip whitespace from column names
        df['Amount'] = df['Amount'].str.replace(',', '').astype(float) # Convert the 'Amount' column to float
        df['Date'] = pd.to_datetime(df['Date'], format='%d %b %Y') # Convert 'Date' column to datetime

        return df
    except Exception as e:
        st.error(f"Error reading the file: {str(e)}")
        return None

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
                st.write(debits_df)

            with tab2:
                st.write(credits_df)


main()