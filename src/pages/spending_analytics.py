"""Spending analytics page with visualizations and metrics."""

import pandas as pd
import streamlit as st
import plotly.express as px
from ..data.processing import load_main_spending_dataframe
from ..utils.currency import get_user_currency, format_currency, CURRENCY_SYMBOLS
from ..utils.ui_helpers import get_spending_color


def spending_analytics_page():
    """Main spending analytics page"""
    st.title("Spending Analytics")
    
    main_df = load_main_spending_dataframe()

    if main_df is not None:
        # Get user's currency
        user_currency = get_user_currency(st.session_state.username)
        
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
            formatted_total = format_currency(abs(total_spending), user_currency)
            
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
                        Total spent in the selected period: <span style="color: {spending_color};">{formatted_total}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        if st.checkbox("Show all spending data"):
            st.dataframe(filtered_spending_df)

        # Monthly spending metrics
        display_monthly_metrics(spending_df, user_currency)
        
        # Month selector
        display_month_selector(spending_df, user_currency)
        
        # Balance over time chart
        display_balance_chart(main_df, selected_date_range)
        
        # Spending over time analysis
        display_spending_over_time(filtered_spending_df, user_currency)
        
        # Cumulative spending and top transactions
        display_cumulative_and_top_spending(filtered_spending_df, user_currency)

    else:
        st.error("No spending data available for analysis.")


def display_monthly_metrics(spending_df, user_currency):
    """Display monthly spending metrics"""
    col1, col2, col3 = st.columns(3)
    monthly_spending = spending_df.copy()
    monthly_spending['Date'] = monthly_spending['Date'].dt.to_period('M').dt.to_timestamp()
    monthly_spending = monthly_spending.groupby('Date')['Amount'].sum().reset_index()
    monthly_spending['Amount'] = monthly_spending['Amount'].abs()
    monthly_spending = monthly_spending.sort_values(by='Date', ascending=False)
    monthly_spending['Amount_Label'] = monthly_spending['Amount'].apply(
        lambda x: format_currency(x, user_currency, compact=True)
    )
    
    for i in range(3):
        if i < len(monthly_spending):
            month_data = monthly_spending.iloc[i]
            delta_amount = int(monthly_spending.iloc[i]['Amount'] - (monthly_spending.iloc[i+1]['Amount'] if i+1 < len(monthly_spending) else 0))
            delta_formatted = format_currency(delta_amount, user_currency)
            with col1 if i == 0 else col2 if i == 1 else col3:
                st.metric(
                    label=month_data['Date'].strftime('%B %Y'),
                    value=month_data['Amount_Label'],
                    delta=delta_formatted,
                    delta_color="inverse"
                )
        else:
            zero_formatted = format_currency(0, user_currency)
            with col1 if i == 0 else col2 if i == 1 else col3:
                st.metric(label="No data", value=zero_formatted, delta=zero_formatted)


def display_month_selector(spending_df, user_currency):
    """Display month selector for specific spending analysis"""
    if st.checkbox("Show spending for specific month(s)"):
        col1, col2, _ = st.columns([1, 1, 3])
        with col1:
            year_options = spending_df['Date'].dt.year.unique()
            selected_years = st.multiselect("Select Years", options=sorted(year_options, reverse=True))
        with col2:
            month_options = list(range(1, 13))
            month_names = [pd.Timestamp(2000, i, 1).strftime('%B') for i in month_options]
            selected_months = st.multiselect("Select Months", 
                                           options=month_options,
                                           format_func=lambda x: month_names[x-1])
        
        if selected_years and selected_months:
            selected_spending = []
            selected_labels = []
            
            for year in selected_years:
                for month in selected_months:
                    month_data = spending_df[
                        (spending_df['Date'].dt.year == year) & 
                        (spending_df['Date'].dt.month == month)
                    ]
                    spending_amount = abs(month_data['Amount'].sum())
                    selected_spending.append(spending_amount)
                    
                    month_name = pd.Timestamp(year, month, 1).strftime('%B %Y')
                    selected_labels.append(month_name)
            
            num_results = len(selected_spending)
            rows_needed = (num_results + 2) // 3
            
            for row in range(rows_needed):
                cols = st.columns(3)
                for col_idx in range(3):
                    result_idx = row * 3 + col_idx
                    if result_idx < num_results:
                        with cols[col_idx]:
                            formatted_spending = format_currency(selected_spending[result_idx], user_currency)
                            st.metric(
                                label=selected_labels[result_idx],
                                value=formatted_spending
                            )


def display_balance_chart(main_df, selected_date_range):
    """Display balance over time chart"""
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


def display_spending_over_time(filtered_spending_df, user_currency):
    """Display spending over time analysis with different views"""
    col1, _ = st.columns([1, 4])
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

        fig_individual_spending = px.scatter(
            individual_spending,
            x='Date',
            y='Amount',
            title='Individual Spending Over Time',
            hover_data={'Description': True, 'Color': False},
            color='Color',
            color_discrete_map={'red': "#FF5A3D", 'white': '#FFFFFF'}
        )
        fig_individual_spending.update_traces(
            marker=dict(size=7),
            hovertemplate='Date: %{x}<br>Amount: %{y}<br>Description: %{customdata[0]}<extra></extra>'
        )
        fig_individual_spending.update_layout(
            yaxis_type="log",
            xaxis=dict(nticks=20),
            showlegend=False
        )
        st.plotly_chart(fig_individual_spending, use_container_width=True)

    elif spending_ot_selector == "Daily":
        daily_spending = filtered_spending_df.groupby(filtered_spending_df['Date'].dt.date)['Amount'].sum().reset_index()
        daily_spending['Amount'] = daily_spending['Amount'].abs()
        daily_spending = daily_spending.sort_values(by='Date')
        daily_spending['Amount Label'] = daily_spending['Amount'].apply(lambda x: f'{x/1000:.0f}k' if x >= 1000 else f'{x:.0f}')
        
        fig_daily_spending = px.scatter(
            daily_spending,
            x='Date',
            y='Amount',
            title='Daily Spending Over Time',
            text='Amount Label'
        )
        fig_daily_spending.update_traces(
            marker=dict(size=7, color='white'),
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
            st.subheader("Heatmap of Daily Spending")
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
                    title=f'\t\t\t\t{month}',
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
                    hovertemplate=f'Day: %{{x}}<br>Week: %{{y}}<br>Amount: %{{z:.0f}} {CURRENCY_SYMBOLS.get(user_currency, user_currency)}<extra></extra>'
                )

                with cols[col_positions[i]]:
                    st.plotly_chart(fig_heatmap_daily, use_container_width=True)

    elif spending_ot_selector == "Weekly":
        weekly_spending = filtered_spending_df.copy()
        weekly_spending['Amount'] = weekly_spending['Amount'].abs()
        weekly_spending['Week'] = weekly_spending['Date'].dt.to_period('W').dt.start_time
        weekly_spending = weekly_spending.groupby('Week')['Amount'].sum().reset_index()
        weekly_spending = weekly_spending.sort_values(by='Week')
        weekly_spending['Amount_Label'] = weekly_spending['Amount'].apply(
            lambda x: format_currency(x, user_currency, compact=True, show_symbol=False)
        )
        currency_label = f'Weekly Spending ({CURRENCY_SYMBOLS.get(user_currency, user_currency)})'
        
        fig_weekly_spending = px.bar(
            weekly_spending,
            x='Week',
            y='Amount',
            title='Weekly Spending',
            text='Amount_Label',
            labels={'Week': 'Week', 'Amount': currency_label},
        )
        fig_weekly_spending.update_traces(
            textposition='inside',
            textfont=dict(size=18, color='black'),
            hovertemplate='Week: %{x}<br>Weekly Spending: %{y}<extra></extra>'
        )
        
        st.plotly_chart(fig_weekly_spending, use_container_width=True)


def display_cumulative_and_top_spending(filtered_spending_df, user_currency):
    """Display cumulative spending and top transactions"""
    col1, col2 = st.columns([3, 2])
    
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
            st.markdown("<h5>10 Largest Transactions</h5>", unsafe_allow_html=True)
        with col2:
            show_dates_checkbox = st.checkbox("Show dates", value=False)

        if show_dates_checkbox:
            display_columns = ['Description', 'Amount', 'Date']
            formatted_df = top_10_spending[display_columns].copy()
            formatted_df['Amount'] = formatted_df['Amount'].apply(
                lambda x: format_currency(x, user_currency, compact=True)
            )
        else:
            display_columns = ['Description', 'Amount'] 
            formatted_df = top_10_spending[display_columns].copy()
            formatted_df['Amount'] = formatted_df['Amount'].apply(
                lambda x: format_currency(x, user_currency, compact=True)
            )
        
        st.dataframe(formatted_df, hide_index=True, use_container_width=True)
