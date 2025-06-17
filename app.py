import pandas as pd
import streamlit as st
import os
import json
import matplotlib.pyplot as plt
import plotly.express as px

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

def get_spending_color(amount):
    amount = abs(amount)
    max_amount = 2_000_000
    normalized = min(amount / max_amount, 1.0)
    
    # Interpolate between salmon (low) and dark red (high)
    # Salmon: #FA8072, Dark Red: #8B0000
    salmon_r, salmon_g, salmon_b = 250, 128, 114
    dark_red_r, dark_red_g, dark_red_b = 139, 0, 0
    
    r = int(salmon_r + (dark_red_r - salmon_r) * normalized)
    g = int(salmon_g + (dark_red_g - salmon_g) * normalized)
    b = int(salmon_b + (dark_red_b - salmon_b) * normalized)
    
    return f"rgb({r}, {g}, {b})"

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
                    new_hide_status = row["Hide"]
                    details = row["Description"]

                    if new_category != main_df.at[idx, "Category"]:
                        add_keyword_to_category(new_category, details)
                        main_df.at[idx, "Category"] = new_category
                    
                    if new_hide_status != main_df.at[idx, "Hide"]:
                        main_df.at[idx, "Hide"] = new_hide_status

                main_df = categorize_transactions(main_df)
                save_main_dataframe(main_df)
                st.rerun()

        else:
            st.error("No data available to edit")

        col1, _ = st.columns([1, 2])

        with col1:
            upload_file = st.file_uploader("Upload your new Revolut statement", type=["csv"])
            if upload_file is not None:
                new_df = load_statement(upload_file)
                updated_df = merge_dataframes(main_df, new_df)
                save_main_dataframe(updated_df)

    if page == "Spending Analytics":
        st.title("Spending Analytics")
        
        main_df = load_main_dataframe()
        main_df = main_df[main_df['Hide'] == False].copy()

        if main_df is not None:
            spending_df = main_df[main_df['Amount'] < 0].copy()

            col1, _, col2 = st.columns([4, 1, 9])
            with col1:
                min_date = spending_df['Date'].min().date()
                max_date = spending_df['Date'].max().date()
                selected_date_range = st.slider(
                    "Filter by Date",
                    min_date,
                    max_date,
                    (
                        (max_date.replace(day=7) - pd.DateOffset(months=1)).date(),
                        max_date
                    )
                )

            filtered_spending_df = spending_df[
                (spending_df['Date'].dt.date >= selected_date_range[0]) &
                (spending_df['Date'].dt.date <= selected_date_range[1])
            ]

            with col2:    
                total_spending = filtered_spending_df['Amount'].sum()
                spending_color = get_spending_color(total_spending)
                
                st.markdown(
                    f"""
                    <div style="
                        background-color: transparent;
                        padding: 15px;
                        border-radius: 10px;
                        text-align: center;
                        font-weight: bold;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        display: inline-block;
                        width: auto;
                    ">
                        <div style="font-size: 32px; color: white;">
                            Total spent in the selected period: <span style="color: {spending_color};">{abs(total_spending):,.0f} Ft</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            if st.checkbox("Show all spending data"):
                st.dataframe(filtered_spending_df)

            # Balance over time line chart
            balance_chart_data = main_df[
                (main_df['Product'] == 'Current') &
                (main_df['Date'].dt.date >= selected_date_range[0]) &
                (main_df['Date'].dt.date <= selected_date_range[1])
            ].copy()

            balance_chart_data = balance_chart_data.sort_values(by='Date')

            if not balance_chart_data.empty:
                fig_balance_over_time = px.area(
                    balance_chart_data,
                    x='Date',
                    y='Balance',
                    title='Account Balance Over Time',
                    markers=True
                )
                st.plotly_chart(fig_balance_over_time, use_container_width=True)
            else:
                st.write("No 'Current' account balance data to display for the selected period.")
            
            col1, _ = st.columns([1, 5])
            with col1:
                spending_ot_selector = st.selectbox(
                    "Spending Over Time",
                    options=("Individual Transactions", "Daily", "Weekly")
                )

            if spending_ot_selector == "Individual Transactions":
                daily_spending_detailed = filtered_spending_df.copy()
                daily_spending_detailed['Amount'] = daily_spending_detailed['Amount'].abs()
                daily_spending_detailed = daily_spending_detailed.sort_values(by='Date')

                fig_daily_spending = px.scatter(
                    daily_spending_detailed,
                    x='Date',
                    y='Amount',
                    title='Individual Spending Over Time',
                    hover_data={'Description': True}
                )
                fig_daily_spending.update_traces(marker=dict(size=7, color='white'))
                fig_daily_spending.update_layout(yaxis_type="log",xaxis=dict(nticks=20))
                st.plotly_chart(fig_daily_spending, use_container_width=True)

            if spending_ot_selector == "Daily":
                daily_spending = filtered_spending_df.groupby(filtered_spending_df['Date'].dt.date)['Amount'].sum().reset_index()
                daily_spending['Amount'] = daily_spending['Amount'].abs()
                daily_spending = daily_spending.sort_values(by='Date')
                daily_spending['Amount Label'] = daily_spending['Amount'].apply(lambda x: f'{x/1000:.0f}k' if x >= 1000 else f'{x:.0f}')
                fig_daily_spending = px.scatter(
                    daily_spending,
                    x='Date',
                    y='Amount',
                    title='Spending Over Time',
                    text='Amount Label'
                )
                fig_daily_spending.update_traces(
                    marker=dict(size=7,color='white'),
                    textposition='bottom center',
                    textfont=dict(size=14, color='white')
                )
                fig_daily_spending.update_layout(
                    yaxis_type="log",
                    xaxis=dict(
                        tickvals=daily_spending['Date'],
                        ticktext=[date.strftime('%m %d') for date in daily_spending['Date']],
                        tickangle=45
                    )
                )
                st.plotly_chart(fig_daily_spending, use_container_width=True)

            
main()