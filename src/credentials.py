"""
Credential loader — works for both local (.env) and Streamlit Cloud (st.secrets).
Import _get_client() and _get_sheet_id() from here everywhere.
"""

import os
import gspread
from pathlib import Path
from google.oauth2.service_account import Credentials

# Auto-load .env from the project root (works for both CLI and Streamlit)
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(dotenv_path=_env_path, override=False)
except ImportError:
    pass

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def has_credentials() -> bool:
    """
    Fast check — no network calls.
    Returns True if Google credentials are available (Streamlit secrets or .env).
    """
    try:
        import streamlit as st
        secrets = st.secrets
        if secrets.get("google_service_account") and secrets.get("GOOGLE_SHEET_ID"):
            return True
    except Exception:
        pass
    return bool(
        os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON") and os.getenv("GOOGLE_SHEET_ID")
    )


def _get_client() -> gspread.Client:
    """Return an authorised gspread client from st.secrets or .env."""
    try:
        import streamlit as st
        if "google_service_account" in st.secrets:
            info = dict(st.secrets["google_service_account"])
            # gspread expects plain dicts, not AttrDict
            info = {k: str(v) for k, v in info.items()}
            creds = Credentials.from_service_account_info(info, scopes=SCOPES)
            return gspread.authorize(creds)
    except Exception:
        pass

    # Fallback: local .env file path
    key_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not key_file:
        raise EnvironmentError(
            "No Google credentials found. Set GOOGLE_SERVICE_ACCOUNT_JSON in .env "
            "or configure st.secrets['google_service_account'] on Streamlit Cloud."
        )
    creds = Credentials.from_service_account_file(key_file, scopes=SCOPES)
    return gspread.authorize(creds)


def _get_sheet_id() -> str:
    """Return the Google Sheet ID from st.secrets or .env."""
    try:
        import streamlit as st
        val = st.secrets.get("GOOGLE_SHEET_ID")
        if val:
            return str(val)
    except Exception:
        pass
    val = os.getenv("GOOGLE_SHEET_ID")
    if not val:
        raise EnvironmentError("GOOGLE_SHEET_ID not set.")
    return val
