import streamlit as st
from utils.database import init_db, verify_user, create_user

st.set_page_config(
    page_title="IPL Fantasy 2026",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = None


def logout():
    st.session_state.logged_in = False
    st.session_state.user = None
    st.rerun()


def show_login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            "<h1 style='text-align:center;'>🏏 IPL Fantasy 2026</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='text-align:center; color:grey;'>Predict. Compete. Win.</p>",
            unsafe_allow_html=True,
        )
        st.divider()

        tab_login, tab_register = st.tabs(["🔐 Login", "📝 Register"])

        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="your@email.com")
                password = st.text_input(
                    "Password", type="password", placeholder="Enter your password"
                )
                submitted = st.form_submit_button("Login", use_container_width=True)

            if submitted:
                if not email or not password:
                    st.error("Please enter your email and password.")
                else:
                    user = verify_user(email, password)
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.user = user
                        st.success(f"Welcome back, {user['display_name']}! 🎉")
                        st.rerun()
                    else:
                        st.error("Invalid email or password.")

        with tab_register:
            with st.form("register_form"):
                new_display = st.text_input("Full Name *", placeholder="Your full name")
                new_email = st.text_input("Email *", placeholder="your@email.com")
                new_team = st.text_input(
                    "Fantasy Team Name *", placeholder="e.g. Super Strikers XI"
                )
                new_password = st.text_input(
                    "Password *", type="password", placeholder="Min 6 characters"
                )
                new_password2 = st.text_input(
                    "Confirm Password *", type="password", placeholder="Repeat password"
                )
                reg_submitted = st.form_submit_button(
                    "Create Account", use_container_width=True
                )

            if reg_submitted:
                if not all([new_display, new_email, new_team, new_password, new_password2]):
                    st.error("Please fill in all required fields (*).")
                elif "@" not in new_email or "." not in new_email:
                    st.error("Please enter a valid email address.")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters.")
                elif new_password != new_password2:
                    st.error("Passwords do not match.")
                else:
                    ok, msg = create_user(new_email, new_password, new_display, new_team)
                    if ok:
                        st.success(msg + " Please log in.")
                    else:
                        st.error(msg)


def show_sidebar():
    user = st.session_state.user
    with st.sidebar:
        st.markdown(f"### 👤 {user['display_name']}")
        st.markdown(f"🏏 **Team:** {user.get('team_name', '—')}")
        st.markdown(f"📧 {user.get('email', '')}")
        st.divider()
        st.page_link("app.py", label="🏠 Home")
        st.page_link("pages/1_Home.py", label="📊 Dashboard")
        st.page_link("pages/2_Predictions.py", label="🎯 Predictions")
        st.page_link("pages/3_Leaderboard.py", label="🏆 Leaderboard")
        if user.get("role") == "admin":
            st.page_link("pages/4_Admin.py", label="⚙️ Admin Panel")
        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            logout()


if not st.session_state.logged_in:
    show_login_page()
else:
    show_sidebar()
    user = st.session_state.user
    st.markdown(
        "<h1 style='text-align:center;'>🏏 IPL Fantasy 2026</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p style='text-align:center;'>Welcome, <b>{user['display_name']}</b>! "
        "Use the sidebar to navigate.</p>",
        unsafe_allow_html=True,
    )
    st.info("👈 Use the sidebar to go to Dashboard, Predictions, or Leaderboard.")
