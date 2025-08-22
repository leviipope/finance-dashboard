"""Currency configuration and formatting utilities."""

import pandas as pd
import streamlit as st
import re
import json
from typing import Optional

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


import json
import streamlit as st
from ..data.github_storage import read_github_file, get_user_files, write_encrypted_github_file, read_encrypted_github_file

def format_currency(amount, currency: str ='HUF', show_symbol=True, compact=False):
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


from ..data.github_storage import read_encrypted_github_file, write_encrypted_github_file, get_user_files


def get_user_currency(username:str) -> Optional[str]:
    """Get the currency for a specific user from their data"""
    if st.session_state.is_guest:
        return st.session_state.get('currency', 'HUF')
    
    # Try to get from session state first (cached)
    if f"{username}_currency" in st.session_state:
        return st.session_state[f"{username}_currency"]
    
    # Try to load from stored data
    files = get_user_files(username)
    currency_file = files.get("currency") # Use .get for safety
    
    if currency_file:
        currency_content = read_encrypted_github_file(currency_file, username)
        if currency_content:
            try:
                currency_data = json.loads(currency_content)
                currency = currency_data.get("currency")
                if currency:
                    st.session_state[f"{username}_currency"] = currency
                    return currency
            except (json.JSONDecodeError, KeyError):
                pass  # Fallback to None if file is empty or malformed
    
    return None  # Default fallback if no currency is set


def save_user_currency(username: str, currency: str):
    """Save the user's selected currency."""
    if st.session_state.is_guest:
        st.session_state['currency'] = currency
        return

    files = get_user_files(username)
    currency_file = files.get("currency")
    if not currency_file:
        # This should ideally not happen if files are ensured at login
        st.error("Currency file not found for user.")
        return

    currency_data = {"currency": currency}
    content = json.dumps(currency_data, indent=2)
    commit_message = f"Set currency for user {username}"
    
    write_encrypted_github_file(currency_file, content, commit_message, username)
    st.session_state[f"{username}_currency"] = currency
