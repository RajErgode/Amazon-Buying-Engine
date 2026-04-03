"""
src/auth.py
-----------
Login gate for the VirVentures Returnability Engine.
Credentials are read from Streamlit secrets (never hardcoded).
"""

import streamlit as st

ORANGE = "#F47920"
NAVY   = "#1B3A5C"


def _get_credentials() -> tuple[str, str]:
    """Read username and password from Streamlit secrets."""
    try:
        username = st.secrets["auth"]["username"]
        password = st.secrets["auth"]["password"]
        return username, password
    except Exception:
        return None, None


def require_login():
    """
    Call at the top of every page.
    If the user is not authenticated, show the login screen and stop execution.
    Authenticated state persists across page navigation via st.session_state.
    """
    if st.session_state.get("authenticated"):
        return   # already logged in — let the page render

    valid_user, valid_pass = _get_credentials()

    # ── Page config already set by caller — just render login UI ─────────────
    st.markdown(f"""
    <style>
    /* Hide Streamlit sidebar and top bar on login page */
    [data-testid="stSidebar"]        {{ display: none !important; }}
    [data-testid="stHeader"]         {{ background: transparent; }}
    #MainMenu, footer, header        {{ visibility: hidden; }}

    .login-wrapper {{
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 80vh;
    }}
    .login-card {{
        background: #ffffff;
        border-radius: 16px;
        padding: 48px 56px;
        width: 420px;
        box-shadow: 0 8px 40px rgba(27,58,92,0.13);
        border-top: 5px solid {ORANGE};
    }}
    .login-logo {{
        text-align: center;
        margin-bottom: 8px;
    }}
    .login-logo .brand {{
        font-size: 1.7rem;
        font-weight: 800;
        color: {NAVY};
        letter-spacing: -0.5px;
    }}
    .login-logo .brand span {{
        color: {ORANGE};
    }}
    .login-subtitle {{
        text-align: center;
        color: #6B7280;
        font-size: 0.88rem;
        margin-bottom: 32px;
    }}
    .login-error {{
        background: #FEF2F2;
        border: 1px solid #FECACA;
        color: #DC2626;
        border-radius: 8px;
        padding: 10px 14px;
        font-size: 0.88rem;
        margin-bottom: 16px;
        text-align: center;
    }}
    </style>

    <div class="login-wrapper">
      <div class="login-card">
        <div class="login-logo">
          <div class="brand">Vir<span>Ventures</span></div>
        </div>
        <div class="login-subtitle">Returnability Intelligence Platform</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Centre the form using columns
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown(
            f'<h3 style="text-align:center;color:{NAVY};margin-bottom:24px;">Sign In</h3>',
            unsafe_allow_html=True,
        )

        username_input = st.text_input(
            "Username",
            placeholder="Enter your username",
            key="login_username",
        )
        password_input = st.text_input(
            "Password",
            type="password",
            placeholder="Enter your password",
            key="login_password",
        )

        st.markdown("<br>", unsafe_allow_html=True)

        login_btn = st.button(
            "Sign In",
            use_container_width=True,
            type="primary",
            key="login_btn",
        )

        if login_btn:
            if valid_user is None:
                st.error("Auth credentials not configured. Add [auth] section to Streamlit secrets.")
            elif username_input == valid_user and password_input == valid_pass:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.markdown(
                    '<div class="login-error">Incorrect username or password. Please try again.</div>',
                    unsafe_allow_html=True,
                )

        st.markdown(
            f'<p style="text-align:center;color:#9CA3AF;font-size:0.78rem;margin-top:24px;">'
            f'VirVentures &copy; 2026 &nbsp;|&nbsp; Authorised access only</p>',
            unsafe_allow_html=True,
        )

    st.stop()


def render_logout():
    """Render a logout button in the sidebar."""
    with st.sidebar:
        st.markdown("---")
        user = st.secrets.get("auth", {}).get("username", "User") if hasattr(st, "secrets") else "User"
        st.markdown(
            f'<p style="font-size:0.8rem;color:#6B7280;margin-bottom:4px;">Signed in as <b>{user}</b></p>',
            unsafe_allow_html=True,
        )
        if st.button("Sign Out", use_container_width=True):
            st.session_state["authenticated"] = False
            st.rerun()
