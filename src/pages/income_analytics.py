"""Income analytics page with income tracking and savings analysis."""

import pandas as pd
import streamlit as st
import plotly.express as px
from ..data.processing import load_main_dataframe
from ..utils.currency import get_user_currency, format_currency


def income_analytics_page():
    """Main income analytics page"""
    st.title("Income Analytics")

    if st.session_state.is_guest:
        if 'guest_dataframe' not in st.session_state:
            st.error("No data available. Please upload a CSV file first.")
            return
        main_df = st.session_state.guest_dataframe.copy()
    else:
        main_df = load_main_dataframe()
        
    if main_df is None:
        st.error("No data available for income analytics.")
        return

    # Get user's currency
    user_currency = get_user_currency(st.session_state.username)
    if user_currency is None:
        user_currency = "HUF"
        st.warning("No currency set for user, defaulting to HUF.")

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
            savings_data = savings_df[savings_df['Date'].dt.month == month_num]
            monthly_savings.append(abs(savings_data['Amount'].sum()))

    # Display monthly income metrics
    col1, col2, col3 = st.columns(3)
    columns = [col1, col2, col3]

    for i in range(3):
        with columns[i]:
            month_date = pd.Timestamp.now() - pd.DateOffset(months=i)
            month_name = month_date.strftime('%B')
            current_income = monthly_incomes[i]
            previous_income = monthly_incomes[i + 1] if i + 1 < len(monthly_incomes) else 0
            
            st.write(type(user_currency) is str)
            income_formatted = format_currency(current_income, user_currency)
            income_delta = format_currency(current_income - previous_income, user_currency)
            
            st.metric(
                label=f"{month_name} Income",
                value=income_formatted,
                delta=income_delta
            )

            savings_formatted = format_currency(monthly_savings[i], user_currency)
            savings_delta = format_currency(monthly_savings[i] - (monthly_savings[i + 1] if i + 1 < len(monthly_savings) else 0), user_currency)
            
            st.metric(
                label=f"{month_name} Savings",
                value=savings_formatted,
                delta=savings_delta
            )

            st.metric(
                label=f"{month_name} Savings in %",
                value=f"{(monthly_savings[i] / current_income * 100):.1f}%",
                delta=f"{((monthly_savings[i] - (monthly_savings[i + 1] if i + 1 < len(monthly_savings) else 0)) / previous_income * 100):.1f}%"
            )

    if st.checkbox("Show income for specific month(s)"):
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

    # Create monthly income trend chart
    # Aggregate income data by month
    income_df['YearMonth'] = income_df['Date'].dt.to_period('M')
    monthly_income_trend = income_df.groupby('YearMonth').agg({'Amount': 'sum'}).reset_index()
    monthly_income_trend['Date'] = monthly_income_trend['YearMonth'].dt.to_timestamp()
    monthly_income_trend = monthly_income_trend.sort_values('Date')
    monthly_income_trend['Month'] = monthly_income_trend['Date'].dt.strftime('%b %Y')
    
    # Create and display the monthly income trend chart using a bar chart
    fig_income_trend = px.bar(
        monthly_income_trend,
        x='Month',
        y='Amount',
        title='Monthly Income Distribution',
        labels={'Amount': 'Income Amount', 'Month': 'Month'},
        text_auto=True,
        color='Amount',
        color_continuous_scale='Viridis'
    )
    fig_income_trend.update_traces(
        hovertemplate='Income: %{y:,.0f} ' + user_currency + '<extra></extra>'
    )
    fig_income_trend.update_layout(
        xaxis_title="Month",
        yaxis_title=f"Income ({user_currency})",
        xaxis={'categoryorder': 'array', 'categoryarray': monthly_income_trend['Month'].tolist()}
    )
    st.plotly_chart(fig_income_trend, use_container_width=True)

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