import json
import os
import streamlit
import pandas
import plotly.express
from datetime import datetime # Added for date manipulations

streamlit.set_page_config(page_title="Finance Dashboard", page_icon=":money_with_wings:", layout="wide")

category_file = "my_categories.json"
# Renamed for clarity: for descriptions to always filter out globally
globally_removed_descriptions_file = "globally_removed_descriptions.json"
# New file for persisting individually removed transactions
singly_removed_transactions_file = "singly_removed_transactions.json"

if "categories" not in streamlit.session_state:
    streamlit.session_state.categories = {
        "Uncategorized": [],
        "Remove": []  # "Remove" category is for UI selection to delete a single transaction
    }

# For descriptions to always filter out globally
if "globally_removed_descriptions" not in streamlit.session_state:
    streamlit.session_state.globally_removed_descriptions = []

# For individually removed transaction data
if "singly_removed_transactions_data" not in streamlit.session_state:
    streamlit.session_state.singly_removed_transactions_data = []

if os.path.exists(category_file):
    with open(category_file, "r") as f:
        streamlit.session_state.categories = json.load(f)
        if "Remove" not in streamlit.session_state.categories:
            streamlit.session_state.categories["Remove"] = []

if os.path.exists(globally_removed_descriptions_file):
    try:
        with open(globally_removed_descriptions_file, "r") as f:
            streamlit.session_state.globally_removed_descriptions = json.load(f)
    except json.JSONDecodeError:
        streamlit.session_state.globally_removed_descriptions = []

if os.path.exists(singly_removed_transactions_file):
    try:
        with open(singly_removed_transactions_file, "r") as f:
            streamlit.session_state.singly_removed_transactions_data = json.load(f)
    except json.JSONDecodeError:
        streamlit.session_state.singly_removed_transactions_data = []


def save_categories():
    with open(category_file, "w") as f:
        json.dump(streamlit.session_state.categories, f)

# Saves the list of descriptions to always remove globally
def save_globally_removed_descriptions():
    with open(globally_removed_descriptions_file, "w") as f:
        json.dump(streamlit.session_state.globally_removed_descriptions, f)

# Saves the list of individually removed transactions
def save_singly_removed_transactions():
    with open(singly_removed_transactions_file, "w") as f:
        # Using default=str in case date objects are not already strings, though we aim to store them as strings.
        json.dump(streamlit.session_state.singly_removed_transactions_data, f, default=str)


def categorize_transactions(df):
    df["Category"] = "Uncategorized"
    for category, keywords in streamlit.session_state.categories.items():
        if category == "Uncategorized" or category == "Remove" or not keywords:
            continue
        lowered_keywords = [keyword.lower().strip() for keyword in keywords]
        for idx, row in df.iterrows():
            description_str = str(row["Description"]) if pandas.notna(row["Description"]) else ""
            details = description_str.lower().strip()
            if details in lowered_keywords:
                df.at[idx, "Category"] = category
    return df


def load_transactions(file):
    try:
        df_initial_load = pandas.read_csv(file)
        df_initial_load = df_initial_load.rename(columns={'Started Date': 'Date'})
        df_initial_load['Date'] = pandas.to_datetime(df_initial_load['Date']).dt.date
        df_initial_load['Amount'] = df_initial_load['Amount'] - df_initial_load['Fee']
        df_initial_load = df_initial_load.drop(columns=['Product', 'Completed Date', 'Fee', 'State', 'Balance'])
        
        if 'Note' not in df_initial_load.columns:
            df_initial_load['Note'] = ""
        else:
            df_initial_load['Note'] = df_initial_load['Note'].fillna("")

        # Filter based on singly_removed_transactions_data
        if streamlit.session_state.singly_removed_transactions_data:
            indices_to_drop_singly = []
            for original_idx, row in df_initial_load.iterrows():
                row_date_str = str(row['Date'])
                row_desc_str = str(row['Description'])
                current_row_amount_for_matching = abs(row['Amount'])

                for removed_tx_data in streamlit.session_state.singly_removed_transactions_data:
                    if (row_date_str == removed_tx_data['Date'] and
                        row_desc_str == removed_tx_data['Description'] and
                        round(current_row_amount_for_matching, 2) == round(removed_tx_data['Amount'], 2)):
                        indices_to_drop_singly.append(original_idx)
                        break 
            
            if indices_to_drop_singly:
                df_initial_load = df_initial_load.drop(index=list(set(indices_to_drop_singly)))
        
        df = df_initial_load 

        if "globally_removed_descriptions" in streamlit.session_state and streamlit.session_state.globally_removed_descriptions:
            df = df[~df["Description"].astype(str).isin(streamlit.session_state.globally_removed_descriptions)]
        
        return categorize_transactions(df)
    except Exception as e:
        streamlit.error(f"Error loading transactions: {e}")
        return None


def add_keyword_to_category(category, keyword, do_save_and_rerun=True):
    keyword = str(keyword).strip()
    changed = False
    if category in streamlit.session_state.categories and \
       category != "Remove" and \
       isinstance(streamlit.session_state.categories[category], list):
        if keyword and keyword not in streamlit.session_state.categories[category]:
            streamlit.session_state.categories[category].append(keyword)
            changed = True
    if changed and do_save_and_rerun:
        save_categories()
        streamlit.rerun()
    return changed


def main():
    streamlit.title("Finance Dashboard")
    upload_file = streamlit.file_uploader("Upload your bank statement (CSV)", type=["csv"])

    if "credits_df" not in streamlit.session_state and upload_file:
        df_loaded = load_transactions(upload_file)
        if df_loaded is not None:
            credits_df = df_loaded[df_loaded['Amount'] < 0].copy()
            credits_df['Amount'] = credits_df['Amount'].abs()
            if 'Note' not in credits_df.columns:
                credits_df['Note'] = ""
            else:
                credits_df['Note'] = credits_df['Note'].fillna("")
            
            debits_df = df_loaded[df_loaded['Amount'] > 0].copy()
            # Filter out "Interest earned" from debits
            if not debits_df.empty:
                debits_df = debits_df[~debits_df['Description'].astype(str).str.contains("interest earned", case=False, na=False)]

            if 'Note' not in debits_df.columns: # Ensure Note column exists after filtering
                debits_df['Note'] = ""
            else:
                debits_df['Note'] = debits_df['Note'].fillna("")

            streamlit.session_state.credits_df = credits_df
            streamlit.session_state.debits_df = debits_df
        else:
            streamlit.session_state.credits_df = pandas.DataFrame(columns=["Date", "Description", "Amount", "Category", "Note"])
            streamlit.session_state.debits_df = pandas.DataFrame(columns=["Date", "Description", "Amount", "Category", "Note"])

    if "credits_df" in streamlit.session_state:
        tab1, tab2 = streamlit.tabs(["Credits", "Debits"])

        with tab1:
            new_category_name = streamlit.text_input("New category name")
            add_category_button = streamlit.button("Add category")
            if add_category_button and new_category_name:
                if new_category_name not in streamlit.session_state.categories:
                    streamlit.session_state.categories[new_category_name] = []
                    save_categories()
                    streamlit.rerun()

            if "Remove" not in streamlit.session_state.categories: 
                streamlit.session_state.categories["Remove"] = []

            streamlit.subheader("Filter by Date")
            # Prepare filtered_credits_df which is the input to the data_editor
            if not streamlit.session_state.credits_df.empty and "Date" in streamlit.session_state.credits_df.columns:
                min_date_data = streamlit.session_state.credits_df["Date"].min()
                max_date_data = streamlit.session_state.credits_df["Date"].max()

                if pandas.isna(min_date_data) or pandas.isna(max_date_data):
                    streamlit.warning("No date data available to filter.")
                    filtered_credits_df = streamlit.session_state.credits_df.copy()
                    default_slider_value = (datetime.now().date(), datetime.now().date()) # Fallback if no data
                    if pandas.notna(min_date_data) and pandas.notna(max_date_data): # Should not happen here
                        default_slider_value = (min_date_data, max_date_data)

                else:
                    today = pandas.Timestamp.today().date()
                    first_day_of_current_month = today.replace(day=1)

                    # Ideal default range
                    default_start = first_day_of_current_month
                    default_end = today
                    
                    # Clamp defaults to the actual data range
                    actual_default_start = max(min_date_data, default_start)
                    actual_default_end = min(max_date_data, default_end)

                    # If the calculated default range is invalid (e.g., start > end because all data is old),
                    # fall back to the month of the latest data point in the dataset.
                    if actual_default_start > actual_default_end:
                        # Default to the month of the latest data point
                        start_val = max_date_data.replace(day=1)
                        # Ensure this start_val is not before min_date_data
                        start_val = max(min_date_data, start_val)
                        end_val = max_date_data
                        default_slider_value = (start_val, end_val)
                    else:
                        default_slider_value = (actual_default_start, actual_default_end)

                    selected_date_range = streamlit.slider(
                        "Select date range",
                        min_value=min_date_data,
                        max_value=max_date_data,
                        value=default_slider_value, # Use calculated default
                        format="YYYY/MM/DD",
                        key="credits_date_slider" 
                    )
                    filtered_credits_df = streamlit.session_state.credits_df[
                        (streamlit.session_state.credits_df["Date"] >= selected_date_range[0]) &
                        (streamlit.session_state.credits_df["Date"] <= selected_date_range[1])
                    ]
            else:
                streamlit.info("Upload data or ensure 'Date' column exists to enable date filtering and view expenses.")
                filtered_credits_df = pandas.DataFrame(columns=["Date", "Description", "Amount", "Category", "Note"])

            streamlit.subheader("Expenses")
            category_options = list(streamlit.session_state.categories.keys()) if streamlit.session_state.categories else ["Uncategorized"]
            if "Uncategorized" not in category_options:
                category_options.append("Uncategorized")

            columns_to_display_credits = ["Date", "Description", "Amount", "Category", "Note"]
            
            credits_editor_input_display_df = filtered_credits_df.copy()
            if "Note" not in credits_editor_input_display_df.columns and not credits_editor_input_display_df.empty:
                credits_editor_input_display_df["Note"] = ""
            elif credits_editor_input_display_df.empty: 
                 credits_editor_input_display_df = pandas.DataFrame(columns=columns_to_display_credits)


            edited_df = streamlit.data_editor(
                credits_editor_input_display_df[columns_to_display_credits], 
                column_config={
                    "Date": streamlit.column_config.DateColumn("Date", format="YYYY/MM/DD"),
                    "Amount": streamlit.column_config.NumberColumn("Amount", format="%.0f HUF"),
                    "Category": streamlit.column_config.SelectboxColumn(
                        "Category",
                        options=category_options,
                        default="Uncategorized"),
                    "Note": streamlit.column_config.TextColumn("Note")
                },
                hide_index=True,
                use_container_width=True,
                key="data_editor_credits"
            )

            save_button = streamlit.button("Apply Changes", type="primary")
            if save_button:
                made_changes_to_credits_df = False
                made_changes_to_categories = False
                made_changes_to_singly_removed_list = False
                indices_to_drop_from_credits_df = []

                num_rows_in_editor_input_credits = len(filtered_credits_df.index) 
                num_rows_from_editor_output_credits = len(edited_df.index)
                rows_to_process_credits = min(num_rows_in_editor_input_credits, num_rows_from_editor_output_credits)

                if num_rows_from_editor_output_credits != num_rows_in_editor_input_credits:
                     streamlit.warning(
                        f"Credits editor row count mismatch. Input: {num_rows_in_editor_input_credits}, Output: {num_rows_from_editor_output_credits}. "
                        "Processing based on the minimum of these counts."
                    )
                
                for i in range(rows_to_process_credits):
                    edited_row_series = edited_df.iloc[i]
                    original_credit_idx = filtered_credits_df.index[i] 

                    if original_credit_idx not in streamlit.session_state.credits_df.index:
                        streamlit.warning(f"Original index {original_credit_idx} (from credits editor's {i}-th row) "
                                          f"not found in main credits DataFrame. Skipping.")
                        continue
                    
                    original_transaction_in_credits_df = streamlit.session_state.credits_df.loc[original_credit_idx]
                    original_category_in_credits_df = original_transaction_in_credits_df["Category"]
                    description_from_editor = str(edited_row_series["Description"]) 
                    new_category_from_editor = edited_row_series["Category"]
                    new_note_from_editor = str(edited_row_series["Note"]) if "Note" in edited_row_series and pandas.notna(edited_row_series["Note"]) else ""
                    original_note_in_credits_df = str(original_transaction_in_credits_df["Note"]) if "Note" in original_transaction_in_credits_df and pandas.notna(original_transaction_in_credits_df["Note"]) else ""

                    if new_category_from_editor == "Remove":
                        if original_category_in_credits_df != "Remove": 
                            tx_date_str = str(original_transaction_in_credits_df['Date'])
                            tx_desc = str(original_transaction_in_credits_df['Description'])
                            tx_amount = float(original_transaction_in_credits_df['Amount'])
                            singly_removed_item = {"Date": tx_date_str, "Description": tx_desc, "Amount": round(tx_amount, 2)}
                            
                            already_marked = any(
                                item["Date"] == singly_removed_item["Date"] and
                                item["Description"] == singly_removed_item["Description"] and
                                round(item["Amount"], 2) == singly_removed_item["Amount"]
                                for item in streamlit.session_state.singly_removed_transactions_data
                            )
                            if not already_marked:
                                streamlit.session_state.singly_removed_transactions_data.append(singly_removed_item)
                                made_changes_to_singly_removed_list = True
                            
                            indices_to_drop_from_credits_df.append(original_credit_idx)
                            made_changes_to_credits_df = True
                        
                    elif new_category_from_editor != original_category_in_credits_df:
                        streamlit.session_state.credits_df.loc[original_credit_idx, "Category"] = new_category_from_editor
                        made_changes_to_credits_df = True
                        if add_keyword_to_category(new_category_from_editor, str(original_transaction_in_credits_df['Description']), do_save_and_rerun=False):
                            made_changes_to_categories = True
                    
                    if str(original_transaction_in_credits_df['Description']) != description_from_editor and new_category_from_editor != "Remove":
                         streamlit.session_state.credits_df.loc[original_credit_idx, "Description"] = description_from_editor
                         made_changes_to_credits_df = True

                    if new_note_from_editor != original_note_in_credits_df:
                        streamlit.session_state.credits_df.loc[original_credit_idx, "Note"] = new_note_from_editor
                        made_changes_to_credits_df = True
                
                if indices_to_drop_from_credits_df:
                    streamlit.session_state.credits_df = streamlit.session_state.credits_df.drop(index=list(set(indices_to_drop_from_credits_df)))

                if made_changes_to_categories:
                    save_categories()
                
                if made_changes_to_singly_removed_list:
                    save_singly_removed_transactions()

                if made_changes_to_credits_df or made_changes_to_categories or made_changes_to_singly_removed_list:
                    streamlit.rerun()

            if not filtered_credits_df.empty: 
                streamlit.subheader("Spending Analysis")
                col1, col2 = streamlit.columns(2)
                with col1:
                    streamlit.markdown("##### Daily Spending")
                    daily_spending = filtered_credits_df.groupby("Date")["Amount"].sum().reset_index()
                    fig_line = plotly.express.line(daily_spending, x="Date", y="Amount", title="Daily Spending")
                    fig_line.update_xaxes(tickformat="%m/%d")
                    streamlit.plotly_chart(fig_line, use_container_width=True)
                with col2:
                    streamlit.markdown("##### Spending by Category")
                    category_spending = filtered_credits_df.groupby("Category")["Amount"].sum().reset_index()
                    fig_pie = plotly.express.pie(category_spending, values="Amount", names="Category", title="Spending by Category")
                    streamlit.plotly_chart(fig_pie, use_container_width=True)
            elif "credits_df" in streamlit.session_state and not streamlit.session_state.credits_df.empty:
                streamlit.info("No data to display in charts based on current filters.")


        with tab2:
            streamlit.subheader("Debits")
            if "debits_df" in streamlit.session_state and not streamlit.session_state.debits_df.empty:
                debits_editable_df = streamlit.session_state.debits_df.copy() 
                debits_editable_df['YearMonth'] = pandas.to_datetime(debits_editable_df['Date']).dt.strftime('%Y %B')
                unique_months = sorted(debits_editable_df['YearMonth'].unique(), reverse=True)
                
                debits_to_show_monthly_filtered = debits_editable_df 
                selected_month = None 

                filter_col, _ = streamlit.columns([1, 2])
                with filter_col:
                    if unique_months:
                        options_list = ["All Months"] + unique_months
                        
                        default_selection_value = "All Months" 
                        current_year_month_str = datetime.now().strftime('%Y %B')

                        if current_year_month_str in unique_months:
                            default_selection_value = current_year_month_str
                        elif unique_months: 
                            default_selection_value = unique_months[0] 

                        default_idx = 0 
                        try:
                            default_idx = options_list.index(default_selection_value)
                        except ValueError:
                            pass 
                        
                        selected_month = streamlit.selectbox(
                            "Select Month", 
                            options=options_list, 
                            index=default_idx, 
                            key="debit_month_selector"
                        )
                        if selected_month and selected_month != "All Months":
                            debits_to_show_monthly_filtered = debits_editable_df[debits_editable_df['YearMonth'] == selected_month]
                    else:
                        streamlit.info("No date information available to filter by month.")
                
                if not debits_to_show_monthly_filtered.empty:
                    total_income_for_month = debits_to_show_monthly_filtered['Amount'].sum()
                    month_label = selected_month if selected_month and selected_month != "All Months" else "All Loaded Data"
                    # Display total income in green
                    streamlit.markdown(f"**Total Income for {month_label}: <span style='color:green;'>{total_income_for_month:,.0f} HUF</span>**", unsafe_allow_html=True)
                elif selected_month and selected_month != "All Months": 
                     # Display total income in green
                     streamlit.markdown(f"**Total Income for {selected_month}: <span style='color:green;'>0 HUF</span>**", unsafe_allow_html=True)

                show_debits_table = streamlit.checkbox("Show/Edit Debits Table", key="show_debits_table_checkbox")
                if show_debits_table:
                    columns_to_display_debits = ["Date", "Description", "Amount", "Category"]
                    categories_in_view = list(debits_to_show_monthly_filtered['Category'].unique())
                    debit_category_options_for_editor = sorted(list(set(["Remove", "Uncategorized"] + categories_in_view)))
 
                    debits_for_editor = debits_to_show_monthly_filtered[columns_to_display_debits].copy()
                    if debits_to_show_monthly_filtered.empty: 
                        debits_for_editor = pandas.DataFrame(columns=columns_to_display_debits)
                    
                    edited_debits_df = streamlit.data_editor(
                        debits_for_editor, 
                        column_config={
                            "Date": streamlit.column_config.DateColumn("Date", format="YYYY/MM/DD"),
                            "Amount": streamlit.column_config.NumberColumn("Amount", format="%.0f HUF"),
                            "Category": streamlit.column_config.SelectboxColumn(
                                "Category", options=debit_category_options_for_editor, default="Uncategorized"
                            ),
                        },
                        hide_index=True, 
                        use_container_width=True,
                        key="data_editor_debits"
                    )

                    save_debits_button = streamlit.button("Apply Debit Changes", type="primary", key="save_debits")
                    if save_debits_button:
                        made_changes_to_debits_df = False
                        made_changes_to_singly_removed_list_debits = False
                        indices_to_drop_from_debits_df = []

                        num_rows_in_editor_input = len(debits_for_editor.index)
                        num_rows_from_editor_output = len(edited_debits_df.index)
                        rows_to_process = min(num_rows_in_editor_input, num_rows_from_editor_output)

                        if num_rows_from_editor_output != num_rows_in_editor_input:
                            streamlit.warning(
                                f"Debits editor row count mismatch. Input: {num_rows_in_editor_input}, Output: {num_rows_from_editor_output}. "
                                "Processing based on the minimum of these counts."
                            )

                        for i in range(rows_to_process):
                            edited_row_series = edited_debits_df.iloc[i]
                            original_idx_in_filtered_view = debits_for_editor.index[i]
                            original_idx = original_idx_in_filtered_view

                            if original_idx not in streamlit.session_state.debits_df.index:
                                streamlit.warning(f"Original index {original_idx} (from debits editor's {i}-th row, "
                                                  f"derived from filtered view) not found in main debits DataFrame. Skipping.")
                                continue

                            original_transaction_in_debits_df = streamlit.session_state.debits_df.loc[original_idx]
                            original_category_in_debits_df = original_transaction_in_debits_df["Category"]
                            new_category_from_editor = edited_row_series["Category"]

                            if new_category_from_editor == "Remove":
                                date_str = str(original_transaction_in_debits_df['Date'])
                                desc_str = str(original_transaction_in_debits_df['Description'])
                                amount_float = float(original_transaction_in_debits_df['Amount'])
                                
                                transaction_to_mark_removed = {
                                    "Date": date_str,
                                    "Description": desc_str,
                                    "Amount": round(amount_float, 2)
                                }
                                
                                is_already_persisted_as_removed = any(
                                    persisted_item["Date"] == transaction_to_mark_removed["Date"] and
                                    persisted_item["Description"] == transaction_to_mark_removed["Description"] and
                                    round(persisted_item["Amount"], 2) == transaction_to_mark_removed["Amount"]
                                    for persisted_item in streamlit.session_state.singly_removed_transactions_data
                                )
                                
                                if not is_already_persisted_as_removed:
                                    streamlit.session_state.singly_removed_transactions_data.append(transaction_to_mark_removed)
                                    made_changes_to_singly_removed_list_debits = True
                                
                                indices_to_drop_from_debits_df.append(original_idx)
                                made_changes_to_debits_df = True
                            elif new_category_from_editor != original_category_in_debits_df:
                                streamlit.session_state.debits_df.loc[original_idx, "Category"] = new_category_from_editor
                                made_changes_to_debits_df = True
                        
                        if indices_to_drop_from_debits_df:
                            streamlit.session_state.debits_df = streamlit.session_state.debits_df.drop(index=list(set(indices_to_drop_from_debits_df)))
                        
                        if made_changes_to_singly_removed_list_debits:
                            save_singly_removed_transactions()
                        
                        if made_changes_to_debits_df or made_changes_to_singly_removed_list_debits:
                            streamlit.rerun()
                
                # Monthly Income Bar Chart
                streamlit.subheader("Monthly Income Analysis")
                if not debits_editable_df.empty:
                    monthly_income_summary = debits_editable_df.groupby('YearMonth', as_index=False)['Amount'].sum()
                    # Convert 'YearMonth' to a datetime object for proper sorting
                    monthly_income_summary['SortKey'] = pandas.to_datetime(monthly_income_summary['YearMonth'], format='%Y %B')
                    monthly_income_summary = monthly_income_summary.sort_values('SortKey').drop(columns=['SortKey'])

                    fig_monthly_income = plotly.express.bar(
                        monthly_income_summary,
                        x='YearMonth',
                        y='Amount',
                        title="Total Income per Month",
                        labels={'YearMonth': 'Month', 'Amount': 'Total Income (HUF)'},
                        text_auto=True  # Display values on bars
                    )
                    # Ensure the x-axis order is maintained as per the sorted dataframe
                    fig_monthly_income.update_xaxes(categoryorder='array', categoryarray=monthly_income_summary['YearMonth'])
                    fig_monthly_income.update_layout(xaxis_title="Month", yaxis_title="Total Income (HUF)")
                    streamlit.plotly_chart(fig_monthly_income, use_container_width=True)
                else:
                    streamlit.info("No debit data available to display monthly income chart.")

            else:
                streamlit.info("No debit transactions to display or data not loaded.")
    else:
        streamlit.info("Please upload a CSV file to see your financial data.")

if __name__ == "__main__":
    main()