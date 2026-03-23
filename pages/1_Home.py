import streamlit as st
import pandas as pd
from datetime import date
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database import (
    init_db,
    load_matches,
    get_all_results,
    get_user_predictions,
    update_user_profile,
    change_password,
)

st.set_page_config(page_title="Dashboard | IPL Fantasy 2026", page_icon="📊", layout="wide")
init_db()

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("🔒 Please log in first.")
    st.page_link("app.py", label="Go to Login", icon="🔐")
    st.stop()

user = st.session_state.user


def logout():
    st.session_state.logged_in = False
    st.session_state.user = None
    st.rerun()


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

st.title("📊 Dashboard")
st.markdown(f"Welcome back, **{user['display_name']}**! Here's your IPL Fantasy overview.")
st.divider()

matches_df = load_matches()
results_df = get_all_results()
user_preds = get_user_predictions(user["id"])

total_matches = len(matches_df)
completed_matches = len(results_df)
upcoming_matches = total_matches - completed_matches
total_preds = len(user_preds)

correct_preds = 0
if not user_preds.empty and not results_df.empty:
    merged = user_preds.merge(results_df, on="match_id", how="inner")
    correct_preds = int((merged["predicted_winner"] == merged["winner"]).sum())

col1, col2, col3, col4 = st.columns(4)
col1.metric("🏏 Total Matches", total_matches)
col2.metric("✅ Completed", completed_matches)
col3.metric("⏳ Upcoming", upcoming_matches)
col4.metric("🎯 Your Correct Picks", f"{correct_preds} / {total_preds}" if total_preds else "0")

st.divider()

tab_schedule, tab_my_preds, tab_profile = st.tabs(
    ["📅 Match Schedule", "🎯 My Predictions", "👤 My Profile"]
)

with tab_schedule:
    st.subheader("📅 Full Match Schedule")

    if not results_df.empty:
        matches_df = matches_df.merge(
            results_df.rename(columns={"winner": "actual_winner"}),
            on="match_id",
            how="left",
        )
    else:
        matches_df["actual_winner"] = None

    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        filter_status = st.selectbox("Filter by status", ["All Matches", "Upcoming", "Completed"])
    with filter_col2:
        today = date.today()
        filter_date = st.date_input("Filter from date", value=None)

    display_df = matches_df.copy()
    if filter_status == "Upcoming":
        display_df = display_df[display_df["actual_winner"].isna()]
    elif filter_status == "Completed":
        display_df = display_df[display_df["actual_winner"].notna()]
    if filter_date:
        display_df = display_df[display_df["match_date"].dt.date >= filter_date]

    display_df = display_df.sort_values("match_date")

    for _, row in display_df.iterrows():
        match_date_str = row["match_date"].strftime("%a, %d %b %Y")
        is_done = pd.notna(row.get("actual_winner")) and row.get("actual_winner") != ""

        with st.container():
            c1, c2, c3 = st.columns([3, 1, 2])
            with c1:
                st.markdown(
                    f"**Match {int(row['match_id'])}** &nbsp;|&nbsp; "
                    f"📅 {match_date_str} &nbsp;|&nbsp; ⏰ {row['match_time']}"
                )
                st.markdown(f"🏟️ {row['venue']}, {row['city']}")
            with c2:
                st.markdown(
                    f"<div style='text-align:center; padding:8px; background:#1a1a2e; "
                    f"border-radius:8px; color:white;'>"
                    f"<b>{row['team1']}</b><br><span style='color:#ffd700;'>VS</span><br>"
                    f"<b>{row['team2']}</b></div>",
                    unsafe_allow_html=True,
                )
            with c3:
                if is_done:
                    st.success(f"✅ Winner: **{row['actual_winner']}**")
                else:
                    match_dt = row["match_date"].date()
                    if match_dt < today:
                        st.warning("⏳ Result pending")
                    else:
                        days_left = (match_dt - today).days
                        if days_left == 0:
                            st.info("🔴 Today!")
                        elif days_left == 1:
                            st.info("🟡 Tomorrow")
                        else:
                            st.info(f"🟢 In {days_left} days")
            st.divider()

with tab_my_preds:
    st.subheader("🎯 My Predictions")
    if user_preds.empty:
        st.info("You haven't made any predictions yet. Head to the **Predictions** page!")
        st.page_link("pages/2_Predictions.py", label="Go to Predictions →", icon="🎯")
    else:
        merged = user_preds.merge(
            matches_df[["match_id", "team1", "team2", "match_date", "match_time"]],
            on="match_id", how="left"
        )
        if not results_df.empty:
            merged = merged.merge(results_df, on="match_id", how="left")
            merged["result"] = merged.apply(
                lambda r: "✅ Correct" if pd.notna(r.get("winner")) and r["predicted_winner"] == r["winner"]
                else ("❌ Wrong" if pd.notna(r.get("winner")) else "⏳ Pending"),
                axis=1,
            )
        else:
            merged["winner"] = None
            merged["result"] = "⏳ Pending"

        merged = merged.sort_values("match_date")
        display_cols = {
            "match_id": "Match #", "match_date": "Date", "team1": "Team 1",
            "team2": "Team 2", "predicted_winner": "My Pick",
            "winner": "Actual Winner", "result": "Result",
        }
        out = merged[list(display_cols.keys())].rename(columns=display_cols)
        out["Date"] = out["Date"].dt.strftime("%d %b %Y")
        out["Actual Winner"] = out["Actual Winner"].fillna("—")
        st.dataframe(out, use_container_width=True, hide_index=True)

with tab_profile:
    st.subheader("👤 My Profile")
    col_p1, col_p2 = st.columns(2)

    with col_p1:
        st.markdown("**Update Profile**")
        with st.form("profile_form"):
            upd_name = st.text_input("Full Name", value=user.get("display_name", ""))
            upd_email = st.text_input("Email", value=user.get("email", "") or "")
            upd_team = st.text_input("Fantasy Team Name", value=user.get("team_name", "") or "")
            if st.form_submit_button("Save Changes", use_container_width=True):
                if upd_name and upd_team and upd_email:
                    if "@" not in upd_email or "." not in upd_email:
                        st.error("Please enter a valid email address.")
                    else:
                        update_user_profile(user["id"], upd_name, upd_email, upd_team)
                        st.session_state.user["display_name"] = upd_name
                        st.session_state.user["email"] = upd_email
                        st.session_state.user["team_name"] = upd_team
                        st.success("Profile updated!")
                        st.rerun()
                else:
                    st.error("Name, Email and Team Name are required.")

    with col_p2:
        st.markdown("**Change Password**")
        with st.form("password_form"):
            new_pw = st.text_input("New Password", type="password", placeholder="Min 6 characters")
            new_pw2 = st.text_input("Confirm New Password", type="password")
            if st.form_submit_button("Change Password", use_container_width=True):
                if len(new_pw) < 6:
                    st.error("Password must be at least 6 characters.")
                elif new_pw != new_pw2:
                    st.error("Passwords do not match.")
                else:
                    change_password(user["id"], new_pw)
                    st.success("Password changed successfully!")
