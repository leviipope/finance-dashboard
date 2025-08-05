"""Application configuration and constants."""

# App metadata
APP_NAME = "Revolut Analysis Dashboard"
APP_VERSION = "2.0.0"
APP_DESCRIPTION = "A modular personal finance dashboard for analyzing Revolut transaction data"

# GitHub configuration keys
GITHUB_CONFIG_KEYS = {
    "token": "github.token",
    "repo_owner": "github.repo_owner", 
    "repo_name": "github.repo_name",
    "branch": "github.branch"
}

# Default file paths
DEFAULT_PATHS = {
    "users": "data/users.json",
    "admin_dataframe": "data/dataframes/main_dataframe.csv",
    "admin_categories": "data/categories/categories.json"
}

# Session state defaults
SESSION_DEFAULTS = {
    "logged_in": False,
    "username": None,
    "is_guest": False,
    "categories": {"Uncategorized": []},
    "show_change_password": False,
    "show_welcome_toast": False
}

# UI configuration
UI_CONFIG = {
    "sidebar_width": 300,
    "chart_height": 400,
    "max_file_size": 200  # MB
}
