# The app was rewritten to use functional programming principles by Github Copilot
# It was purely for educational purposes.

import pandas as pd
import streamlit as st
import os
import json
import matplotlib.pyplot as plt
import plotly.express as px
from functools import partial, reduce
from typing import Dict, List, Optional, Tuple, Callable, Any

st.set_page_config(page_title="Revolut analysis", page_icon=":money_with_wings:", layout="wide") 

# Constants
MAIN_DATAFRAME_FILE = "main_dataframe.csv"
CATEGORY_FILE = "categories.json"
DEFAULT_CATEGORIES = {"Uncategorized": []}

# Pure functions for data operations
def load_categories() -> Dict[str, List[str]]:
    """Load categories from file or return default."""
    if os.path.exists(CATEGORY_FILE):
        with open(CATEGORY_FILE, "r") as f:
            return json.load(f)
    return DEFAULT_CATEGORIES

def save_categories_to_file(categories: Dict[str, List[str]]) -> None:
    """Save categories to file."""
    with open(CATEGORY_FILE, "w") as f:
        json.dump(categories, f)

def initialize_session_state() -> None:
    """Initialize session state with categories."""
    if "categories" not in st.session_state:
        st.session_state.categories = load_categories()

# Data transformation functions
def drop_columns(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    """Drop specified columns from dataframe."""
    return df.drop(columns, axis=1)

def filter_by_type(df: pd.DataFrame, type_value: str) -> pd.DataFrame:
    """Filter dataframe by type column."""
    return df[df["Type"] != type_value]

def rename_column(df: pd.DataFrame, old_name: str, new_name: str) -> pd.DataFrame:
    """Rename a column in dataframe."""
    return df.rename(columns={old_name: new_name})

def convert_to_datetime(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Convert column to datetime."""
    df_copy = df.copy()
    df_copy[column] = pd.to_datetime(df_copy[column])
    return df_copy

def add_hide_column(df: pd.DataFrame) -> pd.DataFrame:
    """Add Hide column with default False values."""
    df_copy = df.copy()
    df_copy["Hide"] = False
    return df_copy

def apply_hide_rules(df: pd.DataFrame) -> pd.DataFrame:
    """Apply business rules for hiding transactions."""
    df_copy = df.copy()
    
    hide_conditions = [
        df_copy['Description'].str.startswith('To HUF'),
        df_copy['Description'] == 'Transfer from Revolut user',
        (df_copy['Product'] == 'Current') & (df_copy['Description'] == 'From Savings Account'),
        (df_copy['Product'] == 'Current') & (df_copy['Description'] == 'To Savings Account')
    ]
    
    for condition in hide_conditions:
        df_copy.loc[condition, 'Hide'] = True
    
    return df_copy

def round_amounts(df: pd.DataFrame) -> pd.DataFrame:
    """Round amounts to integers."""
    df_copy = df.copy()
    df_copy['Amount'] = df_copy['Amount'].round().astype(int)
    return df_copy

def process_balance_column(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[pd.Series]]:
    """Process balance column and return cleaned df with dropped rows."""
    df_copy = df.copy()
    
    try:
        df_copy['Balance'] = pd.to_numeric(df_copy['Balance'], errors='coerce').round().astype('Int64')
        dropped_rows = df_copy[df_copy['Balance'].isnull()].copy()
        df_copy = df_copy.dropna(subset=['Balance'])
        return df_copy, dropped_rows.to_dict('records') if not dropped_rows.empty else []
    except Exception as e:
        st.error(f"Error processing Balance column: {str(e)}")
        st.stop()

def categorize_dataframe(df: pd.DataFrame, categories: Dict[str, List[str]]) -> pd.DataFrame:
    """Categorize transactions based on description matching."""
    df_copy = df.copy()
    df_copy["Category"] = "Uncategorized"

    for category, keywords in categories.items():
        if category == "Uncategorized" or not keywords:
            continue

        lowered_keywords = [keyword.lower().strip() for keyword in keywords]
        for idx, row in df_copy.iterrows():
            details = row["Description"].lower().strip()
            if details in lowered_keywords:
                df_copy.at[idx, "Category"] = category

    return df_copy

def compose_transformations(*funcs: Callable) -> Callable:
    """Compose multiple transformation functions."""
    return reduce(lambda f, g: lambda x: g(f(x)), funcs, lambda x: x)

def load_statement(file) -> Optional[pd.DataFrame]:
    """Load and process a bank statement file using functional composition."""
    try: 
        df = pd.read_csv(file)
        
        # Define transformation pipeline
        transform_pipeline = compose_transformations(
            partial(drop_columns, columns=["Fee", "Completed Date", "Currency", "State"]),
            partial(filter_by_type, type_value="INTEREST"),
            partial(convert_to_datetime, column='Started Date'),
            partial(rename_column, old_name="Started Date", new_name="Date"),
            add_hide_column,
            apply_hide_rules,
            round_amounts
        )
        
        # Apply transformations
        df_transformed = transform_pipeline(df)
        
        # Process balance column (has side effects for warnings)
        df_final, dropped_rows = process_balance_column(df_transformed)
        
        # Display warnings for dropped rows
        if dropped_rows:
            st.warning(f"Dropped {len(dropped_rows)} rows due to invalid or null Balance:")
            for row in dropped_rows:
                st.warning(f"{row['Description']} {row['Amount']}")
        
        return categorize_dataframe(df_final, st.session_state.categories)
    
    except Exception as e:
        st.error(f"Error reading the file: {str(e)}")
        return None

def load_main_dataframe() -> Optional[pd.DataFrame]:
    """Load main dataframe from file."""
    try:
        df = pd.read_csv(MAIN_DATAFRAME_FILE)
        return convert_to_datetime(df, 'Date')
    except FileNotFoundError:
        st.write("Could not find main_dataframe.csv")
        return None

def create_spending_dataframe(main_df: pd.DataFrame) -> pd.DataFrame:
    """Create spending dataframe by filtering main dataframe."""
    return (main_df
            .query('Hide == False')
            .query('Product != "Deposit"')
            .copy())

def merge_dataframes_functional(main_df: pd.DataFrame, new_df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    """Merge dataframes and return combined df with count of new rows."""
    combined_df = (pd.concat([main_df, new_df])
                   .drop_duplicates(subset=['Date', 'Description', 'Balance'], keep='first'))
    num_new_rows = len(combined_df) - len(main_df)
    return combined_df, num_new_rows

def save_dataframe_to_file(df: pd.DataFrame, filename: str = MAIN_DATAFRAME_FILE) -> None:
    """Save dataframe to CSV file."""
    df.to_csv(filename, index=False)

def add_keyword_to_category_functional(categories: Dict[str, List[str]], category: str, keyword: str) -> Tuple[Dict[str, List[str]], bool]:
    """Add keyword to category and return updated categories with success flag."""
    keyword = keyword.strip()
    if keyword and keyword not in categories.get(category, []):
        updated_categories = categories.copy()
        if category not in updated_categories:
            updated_categories[category] = []
        updated_categories[category] = updated_categories[category] + [keyword]
        return updated_categories, True
    return categories, False

# Color calculation functions
def calculate_spending_color(amount: float, max_amount: float = 2_000_000) -> str:
    """Calculate color based on spending amount using functional approach."""
    def interpolate_color(start_rgb: Tuple[int, int, int], end_rgb: Tuple[int, int, int], factor: float) -> Tuple[int, int, int]:
        """Interpolate between two RGB colors."""
        return tuple(int(start + (end - start) * factor) for start, end in zip(start_rgb, end_rgb))
    
    amount = abs(amount)
    normalized = min(amount / max_amount, 1.0)
    
    salmon_rgb = (250, 128, 114)
    dark_red_rgb = (139, 0, 0)
    
    r, g, b = interpolate_color(salmon_rgb, dark_red_rgb, normalized)
    return f"rgb({r}, {g}, {b})"

# Filter functions
def create_date_filter(df: pd.DataFrame, start_date, end_date) -> pd.Series:
    """Create date range filter."""
    return ((df['Date'].dt.date >= start_date) & (df['Date'].dt.date <= end_date))

def create_type_filter(df: pd.DataFrame, selected_type: str) -> pd.Series:
    """Create type filter."""
    if selected_type == 'ALL':
        return df['Type'].notnull()
    return df['Type'] == selected_type

def create_transaction_type_filter(df: pd.DataFrame, selected_transaction_type: str) -> pd.Series:
    """Create transaction type filter."""
    if selected_transaction_type == 'ALL':
        return df['Amount'].notnull()
    elif selected_transaction_type == 'Credits':
        return df['Amount'] < 0
    elif selected_transaction_type == 'Debits':
        return df['Amount'] > 0
    return df['Amount'].notnull()

def apply_filters(df: pd.DataFrame, *filters) -> pd.DataFrame:
    """Apply multiple filters to dataframe."""
    combined_filter = reduce(lambda a, b: a & b, filters)
    return df[combined_filter]

# State management functions
def update_session_categories(new_categories: Dict[str, List[str]]) -> None:
    """Update session state categories."""
    st.session_state.categories = new_categories
    save_categories_to_file(new_categories)

def add_category_to_session(category_name: str) -> bool:
    """Add new category to session state."""
    if category_name not in st.session_state.categories:
        updated_categories = st.session_state.categories.copy()
        updated_categories[category_name] = []
        update_session_categories(updated_categories)
        return True
    return False

def add_keyword_to_session_category(category: str, keyword: str) -> bool:
    """Add keyword to category in session state."""
    updated_categories, success = add_keyword_to_category_functional(st.session_state.categories, category, keyword)
    if success:
        update_session_categories(updated_categories)
    return success

def main():
    # Initialize session state
    initialize_session_state()
    
    page = st.sidebar.radio("Go to", ["Customize Data", "Spending Analytics", "Income Analytics"])

    if page == "Customize Data":
        customize_data_page()
    elif page == "Spending Analytics":
        spending_analytics_page()
    elif page == "Income Analytics":
        income_analytics_page()

def customize_data_page():
    """Functional approach to customize data page."""
    st.title("Main DataFrame")
    main_df = load_main_dataframe()
    
    if main_df is not None:
        # UI Controls
        date_range, selected_type, selected_transaction_type = create_filter_controls(main_df)
        handle_category_addition()
        
        # Apply filters
        filters = [
            create_date_filter(main_df, date_range[0], date_range[1]),
            create_type_filter(main_df, selected_type),
            create_transaction_type_filter(main_df, selected_transaction_type)
        ]
        
        filtered_df = apply_filters(main_df, *filters)
        filtered_df = categorize_dataframe(filtered_df, st.session_state.categories)
        filtered_df = filtered_df.sort_values(by='Date', ascending=False)

        # Data editor
        main_df_to_edit = create_data_editor(filtered_df)
        
        # Handle changes
        if st.button("Apply Changes"):
            handle_data_changes(main_df, main_df_to_edit)
    else:
        st.error("No data available to edit, please upload a CSV file.")
    
    # File upload
    handle_file_upload(main_df)

def create_filter_controls(main_df: pd.DataFrame) -> Tuple[Tuple, str, str]:
    """Create filter controls and return selected values."""
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
    
    return selected_date_range, selected_type, selected_transaction_type

def handle_category_addition():
    """Handle adding new categories."""
    if st.checkbox("I'd like to add a new category"):
        col1, _ = st.columns([2, 7])
        with col1:
            new_category = st.text_input("Enter new category name:")
            
        st.markdown("> **Note:** To only categorize a single transaction, put '!' at the beginning of the category name. (Not implemented yet)")

        add_button = st.button("Add category")

        if add_button and new_category:
            if add_category_to_session(new_category):
                st.rerun()

def create_data_editor(filtered_df: pd.DataFrame) -> pd.DataFrame:
    """Create data editor with proper column configuration."""
    column_config = {col: st.column_config.Column(col, disabled=True) for col in filtered_df.columns if col not in ['Hide', 'Amount']}
    column_config['Category'] = st.column_config.SelectboxColumn(
        "Category",
        options=list(st.session_state.categories.keys())
    )
    column_config['Hide'] = st.column_config.CheckboxColumn('Hide')
    column_config['Amount'] = st.column_config.NumberColumn('Amount')

    return st.data_editor(filtered_df, column_config=column_config)

def handle_data_changes(main_df: pd.DataFrame, main_df_to_edit: pd.DataFrame):
    """Handle changes made in data editor using functional approach."""
    def update_row(main_df: pd.DataFrame, idx: int, row: pd.Series) -> pd.DataFrame:
        """Update a single row in the main dataframe."""
        main_df_copy = main_df.copy()
        new_category = row["Category"]
        new_hide_status = row["Hide"]
        new_amount = row["Amount"]
        details = row["Description"]

        if new_category != main_df.at[idx, "Category"]:
            add_keyword_to_session_category(new_category, details)
            main_df_copy.at[idx, "Category"] = new_category
        
        if new_hide_status != main_df.at[idx, "Hide"]:
            main_df_copy.at[idx, "Hide"] = new_hide_status
        
        if new_amount != main_df.at[idx, "Amount"]:
            main_df_copy.at[idx, "Amount"] = new_amount
        
        return main_df_copy
    
    # Apply all changes
    updated_main_df = main_df.copy()
    for idx, row in main_df_to_edit.iterrows():
        updated_main_df = update_row(updated_main_df, idx, row)

    # Recategorize and save
    final_df = categorize_dataframe(updated_main_df, st.session_state.categories)
    save_dataframe_to_file(final_df)
    st.rerun()

def handle_file_upload(main_df: Optional[pd.DataFrame]):
    """Handle file upload functionality."""
    col1, _ = st.columns([1, 2])

    with col1:
        upload_file = st.file_uploader("Upload your new Revolut statement", type=["csv"])
        if upload_file is not None and main_df is not None:
            new_df = load_statement(upload_file)
            if new_df is not None:
                updated_df, num_new_rows = merge_dataframes_functional(main_df, new_df)
                save_dataframe_to_file(updated_df)

                if num_new_rows == 0:
                    st.info("No new rows to merge. The main DataFrame is already up to date.")
                else:
                    st.info(f"Successfully added {num_new_rows} new rows into the main DataFrame. Refresh the page!")
                    st.toast("Data successfully uploaded! Refresh the page", icon="🔄")             

def spending_analytics_page():
    """Functional approach to spending analytics page."""
    st.title("Spending Analytics")
    
    main_df = load_main_dataframe()
    if main_df is None:
        st.error("No data available")
        return
    
    spending_df = create_spending_dataframe(main_df)
    spending_df = spending_df[spending_df['Amount'] < 0].copy()

    # Date filter
    date_range = create_spending_date_filter(spending_df)
    filtered_spending_df = apply_filters(spending_df, create_date_filter(spending_df, date_range[0], date_range[1]))

    # Display total spending
    display_total_spending(filtered_spending_df)

    # Optional spending data display
    if st.checkbox("Show all spending data"):
        st.dataframe(filtered_spending_df)

    # Charts and analysis
    display_balance_chart(main_df, date_range)
    display_spending_over_time_analysis(filtered_spending_df)
    display_cumulative_and_top_transactions(filtered_spending_df)

def create_spending_date_filter(spending_df: pd.DataFrame) -> Tuple:
    """Create date filter for spending analytics."""
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
    return selected_date_range

def display_total_spending(filtered_spending_df: pd.DataFrame):
    """Display total spending with color coding."""
    total_spending = filtered_spending_df['Amount'].sum()
    spending_color = calculate_spending_color(total_spending)
    
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

def display_balance_chart(main_df: pd.DataFrame, date_range: Tuple):
    """Display balance over time chart."""
    balance_chart_data = main_df[
        (main_df['Product'] == 'Current') &
        (main_df['Date'].dt.date >= date_range[0]) &
        (main_df['Date'].dt.date <= date_range[1])
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

def display_spending_over_time_analysis(filtered_spending_df: pd.DataFrame):
    """Display spending over time analysis with different views."""
    col1, _ = st.columns([1, 5])
    with col1:
        spending_ot_selector = st.selectbox(
            "Spending Over Time",
            options=("Individual Transactions", "Daily", "Weekly")
        )

    if spending_ot_selector == "Individual Transactions":
        display_individual_spending_chart(filtered_spending_df)
    elif spending_ot_selector == "Daily":
        display_daily_spending_chart(filtered_spending_df)
    elif spending_ot_selector == "Weekly":
        display_weekly_spending_chart(filtered_spending_df)

def display_individual_spending_chart(filtered_spending_df: pd.DataFrame):
    """Display individual transactions scatter plot."""
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

def display_daily_spending_chart(filtered_spending_df: pd.DataFrame):
    """Display daily spending chart with optional heatmap."""
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
        display_spending_heatmap(daily_spending)

def display_spending_heatmap(daily_spending: pd.DataFrame):
    """Display spending heatmap by month and day of week."""
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

def display_weekly_spending_chart(filtered_spending_df: pd.DataFrame):
    """Display weekly spending chart."""
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

def display_cumulative_and_top_transactions(filtered_spending_df: pd.DataFrame):
    """Display cumulative spending and top transactions."""
    col1, col2 = st.columns([3,2])
    
    with col1:
        display_cumulative_spending_chart(filtered_spending_df)
    
    with col2:
        display_top_transactions(filtered_spending_df)

def display_cumulative_spending_chart(filtered_spending_df: pd.DataFrame):
    """Display cumulative spending over time."""
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

def display_top_transactions(filtered_spending_df: pd.DataFrame):
    """Display top 10 largest transactions."""
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

def income_analytics_page():
    """Functional approach to income analytics page."""
    st.title("Income Analytics")

    main_df = load_main_dataframe()
    if main_df is None:
        st.error("No data available")
        return

    income_df, savings_df = prepare_income_data(main_df)
    monthly_incomes, monthly_savings = calculate_monthly_metrics(income_df, savings_df)
    
    display_monthly_metrics(monthly_incomes, monthly_savings)
    
    if st.checkbox("Show income for specific months"):
        display_custom_income_metrics(income_df)
    
    display_savings_chart(savings_df)

def prepare_income_data(main_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Prepare income and savings dataframes."""
    income_df = (main_df
                .query('Amount > 0')
                .query('Hide == False')
                .query('Product == "Current"')
                .copy())

    savings_df = (main_df
                 .query('Product == "Deposit"')
                 .query('Hide == False')
                 .sort_values(by='Date')
                 .copy())
    
    return income_df, savings_df

def calculate_monthly_metrics(income_df: pd.DataFrame, savings_df: pd.DataFrame) -> Tuple[List[float], List[float]]:
    """Calculate monthly income and savings metrics."""
    monthly_incomes = []
    monthly_savings = []
    
    for i in range(4):
        month_num = (pd.Timestamp.now().month - i - 1) % 12 + 1 
        month_data = income_df[income_df['Date'].dt.month == month_num]
        monthly_incomes.append(month_data['Amount'].sum())

        if i != 4:
            saving_month_data = savings_df[
                (savings_df['Date'].dt.month == month_num) & 
                (savings_df['Amount'] > 0)
            ]
            monthly_savings.append(saving_month_data['Amount'].sum())
    
    return monthly_incomes, monthly_savings

def display_monthly_metrics(monthly_incomes: List[float], monthly_savings: List[float]):
    """Display monthly income and savings metrics."""
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

            savings_percentage = (monthly_savings[i] / current_income * 100) if current_income > 0 else 0
            previous_savings_percentage = ((monthly_savings[i] - (monthly_savings[i + 1] if i + 1 < len(monthly_savings) else 0)) / previous_income * 100) if previous_income > 0 else 0
            
            st.metric(
                label=f"{month_name} Savings in %",
                value=f"{savings_percentage:.1f}%",
                delta=f"{previous_savings_percentage:.1f}%"
            )

def display_custom_income_metrics(income_df: pd.DataFrame):
    """Display custom income metrics for selected months."""
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
        selected_metrics = calculate_selected_income_metrics(income_df, selected_years, selected_months)
        display_selected_income_metrics(selected_metrics)

def calculate_selected_income_metrics(income_df: pd.DataFrame, selected_years: List[int], selected_months: List[int]) -> List[Tuple[str, float]]:
    """Calculate income metrics for selected years and months."""
    selected_metrics = []
    
    for year in selected_years:
        for month in selected_months:
            month_data = income_df[
                (income_df['Date'].dt.year == year) & 
                (income_df['Date'].dt.month == month)
            ]
            income_amount = month_data['Amount'].sum()
            month_name = pd.Timestamp(year, month, 1).strftime('%B %Y')
            selected_metrics.append((month_name, income_amount))
    
    return selected_metrics

def display_selected_income_metrics(selected_metrics: List[Tuple[str, float]]):
    """Display selected income metrics in a grid layout."""
    num_results = len(selected_metrics)
    rows_needed = (num_results + 2) // 3
    
    for row in range(rows_needed):
        cols = st.columns(3)
        for col_idx in range(3):
            result_idx = row * 3 + col_idx
            if result_idx < num_results:
                label, amount = selected_metrics[result_idx]
                with cols[col_idx]:
                    st.metric(
                        label=label,
                        value=f"{amount:,.0f} Ft"
                    )

def display_savings_chart(savings_df: pd.DataFrame):
    """Display savings account balance over time chart."""
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

# Run the application
if __name__ == "__main__":
    main()