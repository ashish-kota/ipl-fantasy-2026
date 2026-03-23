import streamlit as st

# CSS to hide Streamlit's auto-generated sidebar page navigation
HIDE_SIDEBAR_NAV_CSS = """
<style>
    [data-testid="stSidebarNav"] { display: none !important; }
</style>
"""


def render_sidebar(user, logout_fn):
    """Render sidebar with only user info + logout. No nav links."""
    st.markdown(HIDE_SIDEBAR_NAV_CSS, unsafe_allow_html=True)
    with st.sidebar:
        st.markdown(f"### 👤 {user['display_name']}")
        st.markdown(f"🏏 **Team:** {user.get('team_name', '—')}")
        st.markdown(f"📧 {user.get('email', '')}")
        if user.get("role") == "admin":
            st.markdown("🔑 **Role:** Admin")
        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            logout_fn()
