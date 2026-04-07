#!/usr/bin/env python3
"""
Script to refactor emojis in CLI to be configurable
"""

def get_icon(icon_type: str, use_emoji: bool = True) -> str:
    """Get icon/emoji for output formatting."""
    icons = {
        "search": ("🔍", "[SEARCH]"),
        "chart": ("📊", "[CHART]"),
        "calendar": ("📅", "[DATE]"),
        "check": ("✅", "[OK]"),
        "error": ("❌", "[ERROR]"),
        "warning": ("⚠️", "[WARN]"),
        "critical": ("🚨", "[CRIT]"),
        "bell": ("🔔", "[ALERT]"),
        "rocket": ("🚀", "[SETUP]"),
        "phone": ("📱", "[NOTIFY]"),
        "lightbulb": ("💡", "[TIP]"),
        "crystal_ball": ("🔮", "[FORECAST]"),
        "trend_up": ("📈", "[UP]"),
        "trend_down": ("📉", "[DOWN]"),
        "arrow_right": ("➡️", "[->]"),
        "test": ("🧪", "[TEST]"),
    }
    emoji, text = icons.get(icon_type, ("", ""))
    return emoji if use_emoji else text

# Replacements needed in cli.py:
replacements = [
    ('🔍', 'get_icon("search", config.get("use_emoji", False))'),
    ('📊', 'get_icon("chart", config.get("use_emoji", False))'),
    ('📅', 'get_icon("calendar", config.get("use_emoji", False))'),
    ('✅', 'get_icon("check", config.get("use_emoji", False))'),
    ('❌', 'get_icon("error", config.get("use_emoji", False))'),
    ('⚠️', 'get_icon("warning", config.get("use_emoji", False))'),
    ('🚨', 'get_icon("critical", config.get("use_emoji", False))'),
    ('🔔', 'get_icon("bell", config.get("use_emoji", False))'),
    ('🚀', 'get_icon("rocket", config.get("use_emoji", False))'),
    ('📱', 'get_icon("phone", config.get("use_emoji", False))'),
    ('💡', 'get_icon("lightbulb", config.get("use_emoji", False))'),
    ('🔮', 'get_icon("crystal_ball", config.get("use_emoji", False))'),
    ('📈', 'get_icon("trend_up", config.get("use_emoji", False))'),
    ('📉', 'get_icon("trend_down", config.get("use_emoji", False))'),
    ('➡️', 'get_icon("arrow_right", config.get("use_emoji", False))'),
    ('🧪', 'get_icon("test", config.get("use_emoji", False))'),
]

print("Add this function to cli.py after format_currency:")
print("""
def get_icon(icon_type: str, use_emoji: bool = True) -> str:
    \"\"\"Get icon/emoji for output formatting.\"\"\"
    icons = {
        "search": ("🔍", "[SEARCH]"),
        "chart": ("📊", "[CHART]"), 
        "calendar": ("📅", "[DATE]"),
        "check": ("✅", "[OK]"),
        "error": ("❌", "[ERROR]"),
        "warning": ("⚠️", "[WARN]"),
        "critical": ("🚨", "[CRIT]"),
        "bell": ("🔔", "[ALERT]"),
        "rocket": ("🚀", "[SETUP]"),
        "phone": ("📱", "[NOTIFY]"),
        "lightbulb": ("💡", "[TIP]"),
        "crystal_ball": ("🔮", "[FORECAST]"),
        "trend_up": ("📈", "[UP]"),
        "trend_down": ("📉", "[DOWN]"),
        "arrow_right": ("➡️", "[->]"),
        "test": ("🧪", "[TEST]"),
    }
    emoji, text = icons.get(icon_type, ("", ""))
    return emoji if use_emoji else text
""")