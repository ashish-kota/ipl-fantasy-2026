import streamlit as st

# Hide Streamlit's auto-generated sidebar nav (we render our own below)
HIDE_AUTO_NAV_CSS = """
<style>
    [data-testid="stSidebarNav"] { display: none !important; }
</style>
"""


def render_sidebar(user, logout_fn):
    """Single sidebar: user info + navigation + logout."""
    st.markdown(HIDE_AUTO_NAV_CSS, unsafe_allow_html=True)
    with st.sidebar:
        # User info
        st.markdown(f"### 👤 {user['display_name']}")
        st.markdown(f"🏏 **Team:** {user.get('team_name', '—')}")
        st.markdown(f"📧 {user.get('email', '')}")
        if user.get("role") == "admin":
            st.markdown("🔑 **Role:** Admin")

        with st.expander("❓ Help / Admin Contacts", expanded=False):
            st.markdown(
                """
**For any issues (login, predictions, scoring), contact:**

- Shourya Kothiyal  
- Vishwa S  
- Mehul Agarwal  
- Priyawart Rana  
- Sai Kiran Kanduri  
- Ashish Kota
                """.strip()
            )

        st.divider()

        # Navigation
        st.markdown("**Navigate**")
        st.page_link("pages/1_Home.py", label="📊 Dashboard", icon=None)
        st.page_link("pages/2_Predictions.py", label="🎯 Predictions", icon=None)
        st.page_link("pages/3_Leaderboard.py", label="🏆 Leaderboard", icon=None)
        if user.get("role") == "admin":
            st.page_link("pages/4_Admin.py", label="⚙️ Admin Panel", icon=None)
        st.divider()

        # Logout
        if st.button("🚪 Logout", use_container_width=True):
            logout_fn()
