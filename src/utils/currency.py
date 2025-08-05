"""Currency configuration and formatting utilities."""

import pandas as pd
import streamlit as st
import re

# Currency configuration and formatting
CURRENCY_SYMBOLS = {
    'USD': '$',
    'EUR': '€',
    'GBP': '£',
    'JPY': '¥',
    'CNY': '¥',
    'CAD': 'C$',
    'AUD': 'A$',
    'CHF': 'CHF',
    'HUF': 'Ft',
    'PLN': 'zł',
    'CZK': 'Kč',
    'SEK': 'kr',
    'NOK': 'kr',
    'DKK': 'kr',
    'RON': 'lei',
    'BGN': 'лв',
    'HRK': 'kn',
    'RUB': '₽',
    'TRY': '₺',
    'INR': '₹',
    'KRW': '₩',
    'SGD': 'S$',
    'HKD': 'HK$',
    'MXN': 'MX$',
    'BRL': 'R$',
    'ZAR': 'R',
    'NZD': 'NZ$',
    'THB': '฿',
    'MYR': 'RM',
    'IDR': 'Rp',
    'PHP': '₱',
    'VND': '₫'
}

# Currency decimal places (some currencies don't use decimals)
CURRENCY_DECIMALS = {
    'JPY': 0,  # Japanese Yen doesn't use decimals
    'KRW': 0,  # Korean Won doesn't use decimals
    'VND': 0,  # Vietnamese Dong doesn't use decimals
    'IDR': 0,  # Indonesian Rupiah doesn't use decimals
    'HUF': 0,  # Hungarian Forint doesn't use decimals
    'CLP': 0,  # Chilean Peso doesn't use decimals
    'ISK': 0,  # Icelandic Krona doesn't use decimals
}


def detect_currency_from_df(df):
    """Detect currency from the DataFrame"""
    if 'Currency' in df.columns and not df['Currency'].empty:
        # Standardize currency values (uppercase and strip whitespace)
        currencies = df['Currency'].str.strip().str.upper()
        # Get the most common non-null currency in the dataset
        if not currencies.dropna().empty:
            return currencies.dropna().mode().iloc[0]
    
    # If no Currency column or couldn't detect, try to infer from other columns
    for col in df.columns:
        # Check for currency in column names
        if 'currency' in col.lower():
            values = df[col].astype(str).str.strip().str.upper()
            for curr in CURRENCY_SYMBOLS.keys():
                if values.str.contains(curr).any():
                    return curr
    
    # Check for currency symbols in monetary columns
    amount_cols = [c for c in df.columns if any(x in c.lower() for x in ['amount', 'price', 'value', 'cost', 'total'])]
    for col in amount_cols:
        values = df[col].astype(str)
        for curr, symbol in CURRENCY_SYMBOLS.items():
            if values.str.contains(re.escape(symbol), regex=True).any():
                return curr
    
    # Default fallback
    return 'HUF'


def format_currency(amount, currency='HUF', show_symbol=True, compact=False):
    """Format amount with appropriate currency symbol and formatting"""
    currency = currency.upper()
    symbol = CURRENCY_SYMBOLS.get(currency, currency)
    decimals = CURRENCY_DECIMALS.get(currency, 2)
    
    # Handle compact formatting (e.g., 1.5k instead of 1,500)
    if compact and abs(amount) >= 1000:
        if abs(amount) >= 1_000_000:
            compact_amount = amount / 1_000_000
            suffix = 'M'
        else:
            compact_amount = amount / 1000
            suffix = 'k'
        
        if decimals == 0:
            formatted_amount = f"{compact_amount:.0f}{suffix}"
        else:
            formatted_amount = f"{compact_amount:.1f}{suffix}"
    else:
        if decimals == 0:
            formatted_amount = f"{amount:,.0f}"
        else:
            formatted_amount = f"{amount:,.{decimals}f}"
    
    if show_symbol:
        # For currencies with symbols that typically go after the amount
        if currency in ['HUF', 'PLN', 'CZK', 'SEK', 'NOK', 'DKK', 'RON']:
            return f"{formatted_amount} {symbol}"
        else:
            return f"{symbol}{formatted_amount}"
    else:
        return formatted_amount


def get_user_currency(username):
    """Get the currency for a specific user from their data"""
    from ..data.github_storage import read_encrypted_github_file, get_user_files
    from io import StringIO
    
    if st.session_state.is_guest:
        return st.session_state.get('currency', 'HUF')
    
    # Try to get from session state first (cached)
    if f"{username}_currency" in st.session_state:
        return st.session_state[f"{username}_currency"]
    
    # Try to load from stored data
    files = get_user_files(username)
    currency_file = files["dataframe"]
    
    df_content = read_encrypted_github_file(currency_file, username)
    if df_content:
        try:
            df = pd.read_csv(StringIO(df_content))
            currency = detect_currency_from_df(df)
            st.session_state[f"{username}_currency"] = currency
            return currency
        except Exception as e:
            st.error(f"Error detecting currency: {e}")
    
    return 'HUF'  # Default fallback
