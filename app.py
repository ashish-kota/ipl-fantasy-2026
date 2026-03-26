import streamlit as st
from utils.database import init_db, verify_user, create_user, log_auth_event
from utils.nav import render_sidebar, HIDE_AUTO_NAV_CSS
from utils.whitelist import load_allowed_emails

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
    # Sidebar on login page
    with st.sidebar:
        if st.button("Help", key="login_help", type="secondary"):
            st.session_state.show_login_help = True

        if st.session_state.get("show_login_help"):
            st.info(
                """
**If any issues, contact:**

- Shourya Kothiyal  
- Vishwa S  
- Mehul Agarwal  
- Priyawart Rana  
- Sai Kiran Kanduri  
- Ashish Kota
                """.strip()
            )

        st.divider()

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
                        log_auth_event("login_success", email, "Login successful")
                        st.session_state.logged_in = True
                        st.session_state.user = user
                        st.success(f"Welcome back, {user['display_name']}! 🎉")
                        st.rerun()
                    else:
                        log_auth_event("login_fail", email, "Invalid email or password")
                        st.error("Invalid email or password.")

        with tab_register:
            allowed_emails = load_allowed_emails()

            with st.form("register_form"):
                new_display = st.text_input("Full Name *", placeholder="Your full name")
                new_email = st.text_input("Email *", placeholder="your@email.com")
                new_password = st.text_input(
                    "Password *", type="password", placeholder="Min 6 characters"
                )
                new_password2 = st.text_input(
                    "Confirm Password *", type="password", placeholder="Repeat password"
                )
                reg_submitted = st.form_submit_button(
                    "Create Account", use_container_width=True
                )

            ALLOWED_DOMAINS = ["@qti.qualcomm.com"]
            ALLOWED_EMAILS = ["admin@iplf.com"]

            if reg_submitted:
                email_lower = new_email.lower().strip()
                domain_ok = any(email_lower.endswith(d) for d in ALLOWED_DOMAINS)
                explicit_ok = email_lower in ALLOWED_EMAILS
                in_whitelist = email_lower in allowed_emails if allowed_emails else False

                if not all([new_display, new_email, new_password, new_password2]):
                    st.error("Please fill in all required fields (*).")
                    log_auth_event("register_fail", new_email, "Missing required fields")
                elif not (in_whitelist or explicit_ok):
                    st.error("You currently dont have permission to register. Please contact the admin.")
                    log_auth_event("register_fail", new_email, "Not in whitelist")
                elif "@" not in new_email or "." not in new_email:
                    st.error("Please enter a valid email address.")
                    log_auth_event("register_fail", new_email, "Invalid email format")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters.")
                    log_auth_event("register_fail", new_email, "Password too short")
                elif new_password != new_password2:
                    st.error("Passwords do not match.")
                    log_auth_event("register_fail", new_email, "Passwords do not match")
                else:
                    ok, msg = create_user(new_email, new_password, new_display, None)
                    if ok:
                        log_auth_event("register_success", new_email, "Account created")
                        st.success(msg + " Please log in.")
                    else:
                        log_auth_event("register_fail", new_email, msg)
                        st.error(msg)


def show_sidebar():
    render_sidebar(st.session_state.user, logout)


# Dynamic page config to change sidebar label between Login and app
if not st.session_state.logged_in:
    st.set_page_config(
        page_title="Login",
        page_icon="🏏",
        layout="wide",
        initial_sidebar_state="expanded",
    )
else:
    st.set_page_config(
        page_title="IPL Fantasy 2026",
        page_icon="🏏",
        layout="wide",
        initial_sidebar_state="expanded",
    )

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
    st.markdown(HIDE_AUTO_NAV_CSS, unsafe_allow_html=True)
    st.info("👈 Use the sidebar to go to Dashboard, Predictions, or Leaderboard.")
