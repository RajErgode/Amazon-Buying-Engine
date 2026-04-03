"""
src/auth.py
-----------
Login gate for the VirVentures Returnability Engine.
Credentials are read from Streamlit secrets (never hardcoded).

Usage in every page (top of file, after set_page_config + apply_theme):
    from src.auth import check_auth, render_logout
    if not check_auth():
        st.stop()
    render_logout()
"""

import streamlit as st

ORANGE = "#F47920"
NAVY   = "#1B3A5C"


def _get_credentials():
    """Read username and password from Streamlit secrets."""
    try:
        username = st.secrets["auth"]["username"]
        password = st.secrets["auth"]["password"]
        return str(username).strip(), str(password).strip()
    except Exception:
        return None, None


def check_auth() -> bool:
    """
    Show login screen if not authenticated.
    Returns True if the user is logged in, False if the login screen was shown.
    Caller must call st.stop() when this returns False.
    """
    if st.session_state.get("authenticated"):
        return True

    valid_user, valid_pass = _get_credentials()

    # ── Hide sidebar on login page ────────────────────────────────────────────
    st.markdown("""
    <style>
    [data-testid="stSidebar"]  { display: none !important; }
    [data-testid="stHeader"]   { background: transparent; }
    #MainMenu, footer          { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

    # ── Branded header ────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="text-align:center;padding:48px 0 8px 0;">
      <div style="font-size:2rem;font-weight:800;color:{NAVY};letter-spacing:-0.5px;">
        Vir<span style="color:{ORANGE};">Ventures</span>
      </div>
      <div style="color:#6B7280;font-size:0.9rem;margin-top:4px;">
        Returnability Intelligence Platform
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Login card ────────────────────────────────────────────────────────────
    _, card, _ = st.columns([1, 1.2, 1])
    with card:
        st.markdown(f"""
        <div style="background:#fff;border-radius:16px;padding:40px 44px;
                    box-shadow:0 8px 40px rgba(27,58,92,0.13);
                    border-top:5px solid {ORANGE};margin-top:8px;">
          <h3 style="text-align:center;color:{NAVY};margin-bottom:24px;font-size:1.3rem;">
            Sign In
          </h3>
        </div>
        """, unsafe_allow_html=True)

        username_input = st.text_input(
            "Username",
            placeholder="Enter your username",
            key="_auth_user",
        )
        password_input = st.text_input(
            "Password",
            type="password",
            placeholder="Enter your password",
            key="_auth_pass",
        )

        st.markdown("<br>", unsafe_allow_html=True)
        login_btn = st.button("Sign In", use_container_width=True, type="primary")

        if login_btn:
            if valid_user is None:
                st.error("Auth credentials not configured in Streamlit secrets.")
            elif username_input.strip() == valid_user and password_input == valid_pass:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Incorrect username or password.")

        st.markdown(
            f'<p style="text-align:center;color:#9CA3AF;font-size:0.75rem;margin-top:20px;">'
            f'VirVentures &copy; 2026 &nbsp;|&nbsp; Authorised access only</p>',
            unsafe_allow_html=True,
        )

    return False


def render_logout():
    """Render logout button at the bottom of the sidebar."""
    try:
        user = st.secrets["auth"]["username"]
    except Exception:
        user = "User"

    with st.sidebar:
        st.markdown("---")
        st.markdown(
            f'<p style="font-size:0.8rem;color:#6B7280;margin-bottom:4px;">'
            f'Signed in as <b>{user}</b></p>',
            unsafe_allow_html=True,
        )
        if st.button("Sign Out", use_container_width=True, key="_logout_btn"):
            st.session_state["authenticated"] = False
            st.rerun()
