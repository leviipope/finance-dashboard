import pandas as pd
import streamlit as st
import os

st.set_page_config(page_title="Simple finance app", page_icon=":money_with_wings:", layout="wide") 

MAIN_DATAFRAME_FILE = "main_dataframe.csv"

def load_statement(file):
    try: 
        df = pd.read_csv(file)
        df = df.drop(["Fee","Completed Date","Currency","State"], axis=1)
        df = df[df["Type"] != "INTEREST"]
        df['Started Date'] = pd.to_datetime(df['Started Date'])
        df = df.rename(columns={"Started Date": "Date"})
        df["Hide"] = False

        return df
    except Exception as e:
        st.error(f"Error reading the file: {str(e)}")
        return None

def load_main_dataframe():
    try:
        df = pd.read_csv(MAIN_DATAFRAME_FILE)
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
            column_config = {col: st.column_config.Column(col, disabled=True) for col in main_df.columns if col != 'Hide'}
            column_config['Hide'] = st.column_config.CheckboxColumn('Hide')

            main_df_to_edit = st.data_editor(main_df, column_config=column_config)

            if st.button("Apply Changes"):
                save_main_dataframe(main_df_to_edit)
        else:
            st.error("No data available to edit")


        upload_file = st.file_uploader("Upload your new Revolut statement", type=["csv"])
        if upload_file is not None:
            new_df = load_statement(upload_file)
            updated_df = merge_dataframes(main_df, new_df)
            save_main_dataframe(updated_df)




        
main()