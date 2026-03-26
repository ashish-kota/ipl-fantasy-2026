import os
import pandas as pd

_WHITELIST_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "India_Finance_Team_members.xls")


def load_allowed_emails():
    """
    Load allowed emails from the India_Finance_Team_members.xls file.

    Expected:
    - A column containing email addresses (case-insensitive header, e.g. 'Email' or 'email').
    Returns a set of lowercased email strings.
    """
    try:
        if not os.path.exists(_WHITELIST_PATH):
            return set()

        df = pd.read_excel(_WHITELIST_PATH)
        # Try common email column names
        email_col = None
        for col in df.columns:
            if str(col).strip().lower() in {"email", "emails", "email_id", "mail"}:
                email_col = col
                break

        if email_col is None:
            return set()

        emails = (
            df[email_col]
            .dropna()
            .astype(str)
            .str.strip()
            .str.lower()
        )
        return set(emails)
    except Exception:
        # Fail closed: if whitelist fails to load, treat as empty (no one allowed)
        return set()
