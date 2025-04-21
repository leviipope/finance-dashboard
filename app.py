import json
import os
import streamlit
import pandas
import plotly.express

streamlit.set_page_config(page_title="Finance Dashboard", page_icon=":money_with_wings:", layout="wide")

category_file = "my_categories.json"

if "categories" not in streamlit.session_state:
    streamlit.session_state.categories = {
        "Uncategorized": []
    }

if os.path.exists(category_file):
    with open(category_file, "r") as f:
        streamlit.session_state.categories = json.load(f)

def save_categories():
    with open(category_file, "w") as f:
        json.dump(streamlit.session_state.categories, f)

def categorize_transactions(df):
    df["Category"] = "Uncategorized"

    for category, keywords in streamlit.session_state.categories.items():
        if category == "Uncategorized" or not keywords:
            continue

        lowered_keywords = [keyword.lower().strip() for keyword in keywords]

        for idx, row in df.iterrows():
            details = row["Description"].lower().strip()
            if details in lowered_keywords:
                df.at[idx, "Category"] = category

    return df

def load_transactions(file):
    try:
        df = pandas.read_csv(file)
        df = df.rename(columns={'Started Date': 'Date'})
        df['Date'] = pandas.to_datetime(df['Date']).dt.date
        df['Amount'] = df['Amount'] - df['Fee']
        df = df.drop(columns=['Product', 'Completed Date', 'Fee', 'State', 'Balance'])

        return categorize_transactions(df)
    except Exception as e:
        streamlit.error(f"Error loading transactions: {e}")
        return None
    
def add_keyword_to_category(category, keyword):
    keyword = keyword.strip()
    if keyword and keyword not in streamlit.session_state.categories[category]:
        streamlit.session_state.categories[category].append(keyword)
        save_categories()
        streamlit.rerun()

def main():
    streamlit.title("Finance Dashboard")

    upload_file = streamlit.file_uploader("Upload your bank statement (CSV)", type=["csv"])

    if upload_file:
        df = load_transactions(upload_file)

        if df is not None:
            credits_df = df[df['Amount'] < 0].copy()
            credits_df['Amount'] = credits_df['Amount'].abs()
            debits_df = df[df['Amount'] > 0].copy()

            streamlit.session_state.credits_df = credits_df

            tab1, tab2 = streamlit.tabs(["Credits", "Debits"])

            with tab1:
                new_category = streamlit.text_input("New category name")
                add_button = streamlit.button("Add category")

                if add_button and new_category:
                    if new_category not in streamlit.session_state.categories:
                        streamlit.session_state.categories[new_category] = []
                        save_categories()
                        streamlit.rerun()

                streamlit.subheader("Expenses")
                edited_df = streamlit.data_editor(
                    streamlit.session_state.credits_df[["Date", "Description", "Amount", "Category"]],
                    column_config = {
                        "Date": streamlit.column_config.DateColumn("Date", format = "YYYY/MM/DD"),
                        "Amount": streamlit.column_config.NumberColumn("Amount", format = "%.0i HUF"),
                        "Category": streamlit.column_config.SelectboxColumn(
                            "Category",
                             options=list(streamlit.session_state.categories.keys()),
                             default="Uncategorized")
                    },
                    hide_index=True,
                    use_container_width=True
                )

                save_button = streamlit.button("Apply Changes", type="primary")
                if save_button:
                    for idx, row in edited_df.iterrows():
                        new_category = row["Category"]
                        if new_category == streamlit.session_state.credits_df.at[idx, "Category"]:
                            continue

                        details = row["Description"]
                        streamlit.session_state.credits_df.at[idx, "Category"] = new_category
                        add_keyword_to_category(new_category, details)

            with tab2:
                streamlit.subheader("Debits")
                streamlit.dataframe(debits_df)

main()