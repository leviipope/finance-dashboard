"""Utility functions for UI and data visualization."""

def get_spending_color(amount):
    """Get color for spending amount visualization"""
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
