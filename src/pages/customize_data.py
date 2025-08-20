"""Data customization page for editing transactions and categories."""

import time
import pandas as pd
import streamlit as st
from ..data.processing import (
    load_main_dataframe, 
    load_statement, 
    merge_dataframes, 
    save_main_dataframe,
    categorize_transactions,
    add_keyword_to_category,
    save_categories
)


def customize_data_page():
    """Page for customizing and editing transaction data"""
    if st.session_state.is_guest:
        st.title("Data Customization (Guest Mode)")
        if 'guest_dataframe' not in st.session_state:
            st.error("No data available. Please upload a CSV file first.")
            return
        main_df = st.session_state.guest_dataframe.copy()
    else:
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

        # Apply filters
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

        # Configure data editor
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
            
            if st.session_state.is_guest:
                st.session_state.guest_dataframe = main_df
                st.success("Changes applied to guest session!")
            else:
                save_main_dataframe(main_df)
                st.success("Changes saved permanently! Refreshing...")
                time.sleep(2)
            st.rerun()

    else:
        if st.session_state.is_guest:
            st.error("No data available. Please upload a CSV file first.")
        else:
            st.error("No data available to edit, please upload a CSV file.")

    # File upload for non-guest users
    if not st.session_state.is_guest:
        col1, _ = st.columns([1, 2])

        with col1:
            upload_file = st.file_uploader("Upload your new Revolut statement", type=["csv"])
            
            from ..utils.currency import get_user_currency

            if upload_file is not None:
                user_currency = get_user_currency(st.session_state.username)
                new_df = load_statement(upload_file, user_currency)
                if new_df is not None:
                    if main_df is not None:
                        updated_df, num_new_rows = merge_dataframes(main_df, new_df)
                    else:
                        updated_df = new_df
                        num_new_rows = len(new_df)
                    
                    save_main_dataframe(updated_df)

                    if num_new_rows == 0:
                        st.info("No new rows to merge. The main DataFrame is already up to date.")
                    else:
                        st.info(f"Successfully added {num_new_rows} new rows into the main DataFrame. Refresh the page!")
                        st.info("Due to streamlits limitations, you will be asked to login again!")
                        st.toast("Data successfully uploaded! Refresh the page and login", icon="🔄")
