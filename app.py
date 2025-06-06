import pandas as pd
import streamlit as st

st.set_page_config(page_title="Simple finance app", page_icon=":money_with_wings:", layout="wide") 

def load_statement(file):
    try: 
        df = pd.read_csv(file)
        df = df.drop(["Fee","Completed Date","Currency","State"], axis=1)
        df = df[df["Type"] != "INTEREST"]
        # Finished coding here
        # Tried to check the type of the data in the amounts column

        return df
    except Exception as e:
        st.error(f"Error reading the file: {str(e)}")
        return None


def main():
    page = st.sidebar.radio("Go to", ["Edit Dataframe", "Analytics etc."])

    if page == "Edit Dataframe":
        st.title("Revolut Analytics Dashboard")

        # upload_file = st.file_uploader("Upload your Revolut statement", type=["csv"])
        upload_file = "./account-statement.csv"

        if upload_file is not None:
            df = load_statement(upload_file)
            main_df_to_edit = st.data_editor(df)

        
main()