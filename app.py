import pandas as pd
import streamlit as st
import os
import json

st.set_page_config(page_title="Simple finance app", page_icon=":money_with_wings:", layout="wide") 

MAIN_DATAFRAME_FILE = "main_dataframe.csv"

category_file = "categories.json"

if "categories" not in st.session_state:
    st.session_state.categories = {
        "Uncategorized": []
    }

if os.path.exists(category_file):
    with open(category_file, "r") as f:
        st.session_state.categories = json.load(f)

def load_statement(file):
    try: 
        df = pd.read_csv(file)
        df = df.drop(["Fee", "Completed Date", "Currency", "State"], axis=1)
        df = df[df["Type"] != "INTEREST"]
        df['Started Date'] = pd.to_datetime(df['Started Date'])
        df = df.rename(columns={"Started Date": "Date"})
        df["Hide"] = False
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
    try:
        df = pd.read_csv(MAIN_DATAFRAME_FILE)
        df['Date'] = pd.to_datetime(df['Date'])
        return df
    except FileNotFoundError:
        st.write("Could not find main_dataframe.csv")
        return None

def merge_dataframes(main_df, new_df):
    combined_df = pd.concat([main_df, new_df]).drop_duplicates(subset=['Date', 'Description', 'Amount'], keep='last')
    return combined_df

def save_main_dataframe(df):
    df.to_csv(MAIN_DATAFRAME_FILE, index=False)

def save_categories():
    with open(category_file, "w") as f:
        json.dump(st.session_state.categories, f)

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

def main():
    page = st.sidebar.radio("Go to", ["Customize Data", "Spending Analytics", "Income Analytics"])

    if page == "Customize Data":
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

            column_config = {col: st.column_config.Column(col, disabled=True) for col in filtered_df.columns if col != 'Hide'}
            column_config['Category'] = st.column_config.SelectboxColumn(
                "Category",
                options=list(st.session_state.categories.keys())
            )
            column_config['Hide'] = st.column_config.CheckboxColumn('Hide')

            main_df_to_edit = st.data_editor(filtered_df, column_config=column_config)

            if st.button("Apply Changes"):
                for idx, row in main_df_to_edit.iterrows():
                    new_category = row["Category"]
                    details = row["Description"]

                    if new_category != main_df.at[idx, "Category"]:
                        add_keyword_to_category(new_category, details)
                        main_df.at[idx, "Category"] = new_category

                save_main_dataframe(main_df)

        else:
            st.error("No data available to edit")

        col1, _ = st.columns([1,2])

        with col1:
            upload_file = st.file_uploader("Upload your new Revolut statement", type=["csv"])
            if upload_file is not None:
                new_df = load_statement(upload_file)
                updated_df = merge_dataframes(main_df, new_df)
                save_main_dataframe(updated_df)

main()