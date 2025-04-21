from unicodedata import category

import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os

from streamlit import column_config

# Set Streamlit page configuration: title, icon, and layout.
st.set_page_config(page_title="Simple finance app", page_icon=":money_with_wings:", layout="wide") # Set the page title and icon

category_file = "categories.json"

# Initialize categories in session state if not already present.
if "categories" not in st.session_state:
    st.session_state.categories = { # Default category structure
        "Uncategorized": []
    }

# Load categories from the JSON file if it exists.
if os.path.exists(category_file):
    with open(category_file, "r") as f:
        st.session_state.categories = json.load(f) # Load categories from JSON file

def save_categories():
    with open(category_file, "w") as f:
        json.dump(st.session_state.categories, f) # Save categories to JSON file

# Automatically categorizes transactions based on defined keywords.
def categorize_transactions(df):
    # Initialize the 'Category' column with 'Uncategorized' for all rows.
    df["Category"] = "Uncategorized"

    # Iterate through each category and its associated keywords stored in session state.
    for category, keywords in st.session_state.categories.items():
        if category == "Uncategorized" or not keywords: # We're not going to categorize anything as uc. and if we don't have anything (keywords) to c. then we can't do anything
            continue

        lowered_keywords = [keyword.lower().strip() for keyword in keywords]

        # Iterate through each transaction (row) in the DataFrame.
        for idx, row in df.iterrows():
            details = row["Details"].lower().strip()
            # If the transaction details exactly match any of the keywords for the current category.
            if details in lowered_keywords:
                # Assign the current category to the transaction.
                df.at[idx, "Category"] = category

    # Return the DataFrame with updated categories.
    return df

# Parses CSV bank statements, converting dates and amounts to the correct format.
def load_transactions(file):
    try:
        df = pd.read_csv(file) # Read the CSV file into a DataFrame
        df.columns = [col.strip() for col in df.columns] # Strip whitespace from column names
        df['Amount'] = df['Amount'].str.replace(',', '').astype(float) # Convert the 'Amount' column to float
        df['Date'] = pd.to_datetime(df['Date'], format='%d %b %Y') # Convert 'Date' column to datetime

        # Apply automatic categorization based on keywords.
        return categorize_transactions(df)
    except Exception as e:
        st.error(f"Error reading the file: {str(e)}")
        return None

# Adds a transaction keyword to a category for automatic categorization.
def add_keyword_to_category(category, keyword):
    keyword = keyword.strip()
    # Check if the keyword is not empty and not already present in the category's keyword list.
    if keyword and keyword not in st.session_state.categories[category]:
        # Append the new keyword to the list for the specified category.
        st.session_state.categories[category].append(keyword)
        # Save the updated categories to the JSON file.
        save_categories()
        return True

    return False

def main():
    st.title("Simple Finance App") # Set the title of the app

    upload_file = st.file_uploader("Upload a CSV file", type=["csv"]) # File uploader for CSV files

    # Process the uploaded file if one is provided.
    if upload_file is not None:
        df  = load_transactions(upload_file)

        if df is not None:
            # Pandas filter operation for separate debits and credits
            debits_df = df[df['Debit/Credit'] == 'Debit'].copy() 
            credits_df = df[df['Debit/Credit'] == 'Credit'].copy()

            # Store the debits DataFrame in session state for persistence across reruns.
            st.session_state.debits_df = debits_df.copy()

            tab1, tab2 = st.tabs(["Expenses (Debits)", "Payments (Credits)"])

            # Content for the "Expenses (Debits)" tab.
            with tab1:
                # Input field for adding a new category name.
                new_category = st.text_input("New category name")
                # Button to trigger adding the new category.
                add_button = st.button("Add category")

                # If we pressed the button AND new category has some value
                if add_button and new_category: 
                    # Check if the category doesn't already exist.
                    if new_category not in st.session_state.categories:
                        st.session_state.categories[new_category] = []
                        save_categories()
                        # Rerun the Streamlit app to reflect the changes immediately.
                        st.rerun()

                st.subheader("Your expenses")
                # Display an editable data grid (data editor) for debits.
                edited_df = st.data_editor(
                    st.session_state.debits_df[["Date", "Details", "Amount", "Category"]],
                    column_config = {
                        "Date": st.column_config.DateColumn("Date", format = "DD/MM/YYYY"),
                        "Amount": st.column_config.NumberColumn("Amount", format = "%.2f AED"),
                        "Category": st.column_config.SelectboxColumn( # Category column as a dropdown
                            "Category",
                            # Populate dropdown options with existing category names.
                            options=list(st.session_state.categories.keys())
                        )
                    },
                    hide_index = True,
                    use_container_width = True,
                    key = "category_editor"
                )

                save_button = st.button("Apply Changes", type="primary")
                if save_button:
                    # Iterate through the rows of the edited DataFrame.
                    for idx, row in edited_df.iterrows():
                        new_category = row["Category"]
                        # Compare with the original category in the session state DataFrame.
                        if new_category == st.session_state.debits_df.at[idx, "Category"]:
                            # Skip if the category hasn't changed.
                            continue

                        details = row["Details"]
                        st.session_state.debits_df.at[idx, "Category"] = new_category
                        add_keyword_to_category(new_category, details)

            st.subheader('Expense Summary')
            # Group the debits DataFrame by category and sum the amounts.
            category_totals = st.session_state.debits_df.groupby("Category")["Amount"].sum().reset_index()
            category_totals = category_totals.sort_values("Amount", ascending=False)
            
            # Display the category totals in a DataFrame.
            st.dataframe(
                category_totals,
                column_config={
                    "Amount": st.column_config.NumberColumn("Amount", format="%,.2f AED")
                },
                use_container_width=True,
                hide_index=True
            )

            # plotly.express pie chart
            fig = px.pie(
                category_totals,
                values = "Amount",
                names = "Category",
                title = "Expenses by Category"
            )
            # Display the Plotly chart in Streamlit.
            st.plotly_chart(fig, use_container_width=True)

            with tab2:
                st.subheader("Payment Summary")
                total_payments = credits_df["Amount"].sum()
                # Display the total payments using a Streamlit metric component.
                st.metric("Total Payments",f"{total_payments:.2f} AED")
                st.dataframe(credits_df, hide_index=True, use_container_width=True)

main()