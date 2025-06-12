import pandas as pd
import streamlit as st
import os

st.set_page_config(page_title="Simple finance app", page_icon=":money_with_wings:", layout="wide") 

MAIN_DATAFRAME_FILE = "main_dataframe.csv"

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

        return df
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


def main():
    page = st.sidebar.radio("Go to", ["Customize Data", "Spending Analytics", "Incoming Analytics"])

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
                

            if selected_type == 'ALL':
                type_filter = main_df['Type'].notnull()  # Include all types
            else:
                type_filter = main_df['Type'] == selected_type

            if selected_transaction_type == 'ALL':
                transaction_type_filter = main_df['Amount'].notnull()  # Include all transactions
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

            column_config = {col: st.column_config.Column(col, disabled=True) for col in filtered_df.columns if col != 'Hide'}
            column_config['Hide'] = st.column_config.CheckboxColumn('Hide')

            main_df_to_edit = st.data_editor(filtered_df, column_config=column_config)

            if st.button("Apply Changes"):
                save_main_dataframe(main_df_to_edit)
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