import pandas as pd
import streamlit as st
import os
import json
import matplotlib.pyplot as plt
import plotly.express as px

st.set_page_config(page_title="Revolut analysis", page_icon=":money_with_wings:", layout="wide") 

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
        df.loc[df['Description'].str.startswith('To HUF'), 'Hide'] = True
        df.loc[df['Description'] == 'Transfer from Revolut user', 'Hide'] = True
        df.loc[(df['Product'] == 'Current') & (df['Description'] == 'From Savings Account'), 'Hide'] = True
        df.loc[(df['Product'] == 'Current') & (df['Description'] == 'To Savings Account'), 'Hide'] = True

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

def load_main_spending_dataframe():
    main_df = load_main_dataframe()
    main_df = main_df[main_df['Hide'] == False].copy()
    main_df = main_df[main_df['Product'] != 'Deposit']
    return main_df

def merge_dataframes(main_df, new_df):
    combined_df = pd.concat([main_df, new_df]).drop_duplicates(subset=['Date', 'Description', 'Balance'], keep='first')
    num_new_rows = len(combined_df) - len(main_df)
    return combined_df, num_new_rows

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
            filtered_df = filtered_df.sort_values(by='Date', ascending=False)

            column_config = {col: st.column_config.Column(col, disabled=True) for col in filtered_df.columns if col not in ['Hide', 'Amount']}
            column_config['Category'] = st.column_config.SelectboxColumn(
                "Category",
                options=list(st.session_state.categories.keys())
            )
            column_config['Hide'] = st.column_config.CheckboxColumn('Hide')
            column_config['Amount'] = st.column_config.NumberColumn('Amount')

            main_df_to_edit = st.data_editor(filtered_df, column_config=column_config)

            if st.button("Apply Changes"):
                for idx, row in main_df_to_edit.iterrows():
                    new_category = row["Category"]
                    new_hide_status = row["Hide"]
                    new_amount = row["Amount"]
                    details = row["Description"]

                    if new_category != main_df.at[idx, "Category"]:
                        add_keyword_to_category(new_category, details)
                        main_df.at[idx, "Category"] = new_category
                    
                    if new_hide_status != main_df.at[idx, "Hide"]:
                        main_df.at[idx, "Hide"] = new_hide_status
                    
                    if new_amount != main_df.at[idx, "Amount"]:
                        main_df.at[idx, "Amount"] = new_amount

                main_df = categorize_transactions(main_df)
                save_main_dataframe(main_df)
                st.rerun()

        else:
            st.error("No data available to edit, please upload a CSV file.")

        col1, _ = st.columns([1, 2])

        with col1:
            upload_file = st.file_uploader("Upload your new Revolut statement", type=["csv"])
            if upload_file is not None:
                new_df = load_statement(upload_file)
                updated_df, num_new_rows = merge_dataframes(main_df, new_df)
                save_main_dataframe(updated_df)

                if num_new_rows == 0:
                    st.info("No new rows to merge. The main DataFrame is already up to date.")
                else:
                    st.info(f"Successfully added {num_new_rows} new rows into the main DataFrame. Refresh the page!")
                    st.toast("Data successfully uploaded! Refresh the page", icon="🔄")             

    if page == "Spending Analytics":
        st.title("Spending Analytics")
        
        main_df = load_main_spending_dataframe()

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
                    markers=True,
                    hover_data={'Description': True}
                )
                fig_balance_over_time.update_traces(
                    hovertemplate='Date: %{x}<br>Balance: %{y}<br>Description: %{customdata[0]}<extra></extra>'
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
                individual_spending = filtered_spending_df.copy()
                individual_spending['Amount'] = individual_spending['Amount'].abs()
                individual_spending = individual_spending.sort_values(by='Date')
                
                threshold = individual_spending['Amount'].quantile(0.9)
                individual_spending['Color'] = individual_spending['Amount'].apply(
                    lambda x: 'red' if x >= threshold else 'white'
                )

                fig_daily_spending = px.scatter(
                    individual_spending,
                    x='Date',
                    y='Amount',
                    title='Individual Spending Over Time',
                    hover_data={'Description': True, 'Color': False},
                    color='Color',
                    color_discrete_map={'red': "#FF5A3D", 'white': '#FFFFFF'}
                )
                fig_daily_spending.update_traces(
                    marker=dict(size=7),
                    hovertemplate='Date: %{x}<br>Amount: %{y}<br>Description: %{customdata[0]}<extra></extra>'
                )
                fig_daily_spending.update_layout(
                    yaxis_type="log",
                    xaxis=dict(nticks=20),
                    showlegend=False
                )
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
                    textfont=dict(size=14, color='white'),
                    hovertemplate='Date: %{x}<br>Amount: %{y}<extra></extra>'
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

                if st.checkbox("Show heatmap"):
                    daily_spending['Date'] = pd.to_datetime(daily_spending['Date'])
                    daily_spending['Day_of_Week'] = daily_spending['Date'].dt.day_name()
                    daily_spending['Week'] = daily_spending['Date'].dt.isocalendar().week
                    daily_spending['Month'] = daily_spending['Date'].dt.strftime('%Y-%m')
                    
                    sorted_months = sorted(daily_spending['Month'].unique())
                    
                    num_months = len(sorted_months)
                    if num_months == 1:
                        cols = st.columns([1, 1])  # Half screen
                        col_positions = [0]
                    elif num_months == 2:
                        cols = st.columns(2)  # Side by side
                        col_positions = [0, 1]
                    elif num_months == 3:
                        cols = st.columns(2)  # Three columns
                        col_positions = [0, 1, 0]
                    elif num_months == 4:
                        cols = st.columns(2)  # 2x2 layout
                        col_positions = [0, 1, 0, 1]
                    else:
                        cols = st.columns(2)  # 2x3 layout
                        col_positions = [i % 2 for i in range(num_months)]
                    
                    for i, month in enumerate(sorted_months):
                        month_data = daily_spending[daily_spending['Month'] == month]
                        
                        heatmap_data = month_data.pivot_table(
                            index='Week',
                            columns='Day_of_Week',
                            values='Amount',
                            fill_value=0
                        )
                        
                        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                        heatmap_data = heatmap_data.reindex(columns=day_order, fill_value=0)
                        
                        fig_heatmap_daily = px.imshow(
                            heatmap_data,
                            color_continuous_scale=[[0, '#2F2F2F'], [0.1, '#8B0000'], [1, '#FF0000']],
                            title=f'\t\t\t\t\tDaily Spending Heatmap - {month}',
                            aspect='equal'
                        )
                        fig_heatmap_daily.update_layout(
                            xaxis_title=None,
                            yaxis_title='Week of Year',
                            xaxis=dict(tickmode='array', tickvals=list(range(len(day_order))), ticktext=day_order),
                            yaxis=dict(tickmode='linear', dtick=1),
                            plot_bgcolor='#1E1E1E',
                            paper_bgcolor='#1E1E1E',
                            font=dict(color='white')
                        )
                        fig_heatmap_daily.update_traces(
                            hovertemplate='Day: %{x}<br>Week: %{y}<br>Amount: %{z:.0f} Ft<extra></extra>'
                        )

                        with cols[col_positions[i]]:
                            st.plotly_chart(fig_heatmap_daily, use_container_width=True)
                    

            if spending_ot_selector == "Weekly":
                weekly_spending = filtered_spending_df.copy()
                weekly_spending['Amount'] = weekly_spending['Amount'].abs()
                weekly_spending['Week'] = weekly_spending['Date'].dt.to_period('W').dt.start_time
                weekly_spending = weekly_spending.groupby('Week')['Amount'].sum().reset_index()
                weekly_spending = weekly_spending.sort_values(by='Week')
                weekly_spending['Amount_Label'] = weekly_spending['Amount'].apply(
                    lambda x: f'{x/1000:.0f}k' if x >= 1000 else f'{x:.0f}'
                )
                fig_weekly_spending = px.bar(
                    weekly_spending,
                    x='Week',
                    y='Amount',
                    title='Weekly Spending',
                    text='Amount_Label',
                    labels={'Week': 'Week', 'Amount': 'Weekly Spending (Ft)'},
                )
                fig_weekly_spending.update_traces(
                    textposition='inside',
                    textfont=dict(size=18, color='black'),
                    hovertemplate='Week: %{x}<br>Weekly Spending: %{y}<extra></extra>'
                )
                
                st.plotly_chart(fig_weekly_spending, use_container_width=True)

            # Spending add-up over time and top 10 transactions
            col1, col2 = st.columns([3,2])
            with col1:
                individual_spending = filtered_spending_df.copy()
                individual_spending['Amount'] = individual_spending['Amount'].abs()
                individual_spending = individual_spending.sort_values(by='Date')
                individual_spending['CumSum'] = individual_spending['Amount'].cumsum()
                fig_spending_add_up = px.line(
                    individual_spending,
                    x='Date',
                    y='CumSum',
                    title='Cumulative Spending Over Time',
                    markers=True,
                    hover_data={'Description': True}
                )
                fig_spending_add_up.update_layout(
                    yaxis_title=None,
                    xaxis_title='Date',
                )
                fig_spending_add_up.update_traces(
                    marker=dict(size=7),
                    hovertemplate='Date: %{x}<br>Total: %{y}<br>Description: %{customdata[0]}<extra></extra>'
                )
                fig_spending_add_up.update_traces(customdata=individual_spending[['Description']].values)
                st.plotly_chart(fig_spending_add_up, use_container_width=True)

            with col2:
                top_10_spending = filtered_spending_df.copy()
                top_10_spending['Amount'] = top_10_spending['Amount'].abs()
                top_10_spending = top_10_spending.sort_values(by='Amount', ascending=False).head(10)


                col1, _, col2 = st.columns([2, 1, 1])
                with col1:
                    st.markdown("<h6>10 Largest Transactions</h6>", unsafe_allow_html=True)
                with col2:
                    show_dates_checkbox = st.checkbox("Show Dates")

                if show_dates_checkbox:
                    st.dataframe(top_10_spending[['Description', 'Amount', 'Date']], hide_index=True)
                else:
                    st.dataframe(top_10_spending[['Description', 'Amount']], hide_index=True)

    if page == "Income Analytics":
        st.title("Income Analytics")

        main_df = load_main_dataframe()

        income_df = main_df[main_df['Amount'] > 0].copy()
        income_df = income_df[income_df['Hide'] == False]
        income_df = income_df[income_df['Product'] == 'Current']

        savings_df = main_df[main_df['Product'] == 'Deposit'].copy()
        savings_df = savings_df[savings_df['Hide'] == False]
        savings_df = savings_df.sort_values(by='Date')

        monthly_incomes = []
        monthly_savings = []
        for i in range(4):
            month_num = (pd.Timestamp.now().month - i - 1) % 12 + 1 
            month_data = income_df[income_df['Date'].dt.month == month_num]
            monthly_incomes.append(month_data['Amount'].sum())

            if i != 4:
                month_num = (pd.Timestamp.now().month - i - 1) % 12 + 1 
                saving_month_data = savings_df[savings_df['Date'].dt.month == month_num]
                saving_month_data = saving_month_data[saving_month_data['Amount'] > 0]
                monthly_savings.append(saving_month_data['Amount'].sum())

        col1, col2, col3 = st.columns(3)
        columns = [col1, col2, col3]

        for i in range(3):
            with columns[i]:
                month_date = pd.Timestamp.now() - pd.DateOffset(months=i)
                month_name = month_date.strftime('%B')
                current_income = monthly_incomes[i]
                previous_income = monthly_incomes[i + 1] if i + 1 < len(monthly_incomes) else 0
                
                st.metric(
                    label=f"{month_name} Income",
                    value=f"{current_income:,.0f} Ft",
                    delta=f"{current_income - previous_income:,.0f} Ft"
                )

                st.metric(
                    label=f"{month_name} Savings",
                    value=f"{monthly_savings[i]:,.0f} Ft",
                    delta=f"{monthly_savings[i] - (monthly_savings[i + 1] if i + 1 < len(monthly_savings) else 0):,.0f} Ft"
                )

                st.metric(
                    label=f"{month_name} Savings in %",
                    value=f"{(monthly_savings[i] / current_income * 100):.1f}%",
                    delta=f"{((monthly_savings[i] - (monthly_savings[i + 1] if i + 1 < len(monthly_savings) else 0)) / previous_income * 100):.1f}%"
                )

        if st.checkbox("Show income for specific months"):
            col1, col2, _ = st.columns([1, 1, 3])
            with col1:
                year_options = income_df['Date'].dt.year.unique()
                selected_years = st.multiselect("Select Years", options=sorted(year_options, reverse=True))
            with col2:
                month_options = list(range(1, 13))
                month_names = [pd.Timestamp(2000, i, 1).strftime('%B') for i in month_options]
                selected_months = st.multiselect("Select Months", 
                                               options=month_options,
                                               format_func=lambda x: month_names[x-1])
            
            if selected_years and selected_months:
                selected_incomes = []
                selected_labels = []
                
                for year in selected_years:
                    for month in selected_months:
                        month_data = income_df[
                            (income_df['Date'].dt.year == year) & 
                            (income_df['Date'].dt.month == month)
                        ]
                        income_amount = month_data['Amount'].sum()
                        selected_incomes.append(income_amount)
                        
                        month_name = pd.Timestamp(year, month, 1).strftime('%B %Y')
                        selected_labels.append(month_name)
                
                num_results = len(selected_incomes)
                rows_needed = (num_results + 2) // 3
                
                for row in range(rows_needed):
                    cols = st.columns(3)
                    for col_idx in range(3):
                        result_idx = row * 3 + col_idx
                        if result_idx < num_results:
                            with cols[col_idx]:
                                st.metric(
                                    label=selected_labels[result_idx],
                                    value=f"{selected_incomes[result_idx]:,.0f} Ft"
                                )
    
        fig_savings = px.line(
            savings_df,
            x='Date',
            y='Balance',
            title='Savings Account Balance Over Time',
        )
        fig_savings.update_traces(
            hovertemplate='Date: %{x}<br>Balance: %{y}<extra></extra>'
        )
        st.plotly_chart(fig_savings, use_container_width=True)

         
main()