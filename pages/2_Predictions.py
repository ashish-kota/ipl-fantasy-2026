import streamlit as st
import pandas as pd
from datetime import datetime, date
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database import (
    init_db,
    load_matches,
    get_all_results,
    get_user_predictions,
    save_prediction,
)

st.set_page_config(page_title="Predictions | IPL Fantasy 2026", page_icon="🎯", layout="wide")
init_db()

# ── Auth guard ────────────────────────────────────────────────────────────────
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("🔒 Please log in first.")
    st.page_link("app.py", label="Go to Login", icon="🔐")
    st.stop()

user = st.session_state.user


# ── Sidebar ───────────────────────────────────────────────────────────────────
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


# ── Page header ───────────────────────────────────────────────────────────────
st.title("🎯 Match Predictions")
st.markdown(
    "Pick the winner for each upcoming match **before it starts**. "
    "You can change your prediction any time before the match begins."
)
st.divider()

# ── Load data ─────────────────────────────────────────────────────────────────
matches_df = load_matches()
results_df = get_all_results()
user_preds = get_user_predictions(user["id"])

# Build a dict: match_id -> predicted_winner
pred_map = {}
if not user_preds.empty:
    pred_map = dict(zip(user_preds["match_id"], user_preds["predicted_winner"]))

# Build a set of completed match IDs
completed_ids = set(results_df["match_id"].tolist()) if not results_df.empty else set()

today = date.today()

# Split into upcoming and past
upcoming = matches_df[
    matches_df.apply(
        lambda r: r["match_date"].date() >= today and r["match_id"] not in completed_ids,
        axis=1,
    )
].sort_values("match_date")

past = matches_df[
    matches_df.apply(
        lambda r: r["match_date"].date() < today or r["match_id"] in completed_ids,
        axis=1,
    )
].sort_values("match_date", ascending=False)

# ── Summary strip ─────────────────────────────────────────────────────────────
total_upcoming = len(upcoming)
predicted_upcoming = sum(1 for mid in upcoming["match_id"] if mid in pred_map)
pending_upcoming = total_upcoming - predicted_upcoming

c1, c2, c3 = st.columns(3)
c1.metric("📅 Upcoming Matches", total_upcoming)
c2.metric("✅ Predicted", predicted_upcoming)
c3.metric("⚠️ Yet to Predict", pending_upcoming)

if pending_upcoming > 0:
    st.warning(f"You still have **{pending_upcoming}** upcoming match(es) without a prediction!")

st.divider()

# ── Upcoming matches ──────────────────────────────────────────────────────────
st.subheader("📅 Upcoming Matches — Make Your Picks")

if upcoming.empty:
    st.info("No upcoming matches to predict right now. Check back later!")
else:
    for _, row in upcoming.iterrows():
        mid = int(row["match_id"])
        match_date_str = row["match_date"].strftime("%a, %d %b %Y")
        existing_pred = pred_map.get(mid)

        with st.container():
            st.markdown(
                f"**Match {mid}** &nbsp;|&nbsp; 📅 {match_date_str} &nbsp;|&nbsp; "
                f"⏰ {row['match_time']} &nbsp;|&nbsp; 🏟️ {row['venue']}, {row['city']}"
            )

            col_t1, col_vs, col_t2, col_pred = st.columns([2, 1, 2, 3])

            with col_t1:
                t1_selected = existing_pred == row["team1"]
                st.markdown(
                    f"<div style='text-align:center; padding:12px; "
                    f"background:{'#1a472a' if t1_selected else '#1a1a2e'}; "
                    f"border-radius:10px; color:white; border: {'2px solid #2ecc71' if t1_selected else 'none'};'>"
                    f"<b>{row['team1']}</b>"
                    f"{'<br>✅ Your Pick' if t1_selected else ''}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            with col_vs:
                st.markdown(
                    "<div style='text-align:center; padding:12px; color:#ffd700; font-size:1.2em;'>"
                    "<b>VS</b></div>",
                    unsafe_allow_html=True,
                )

            with col_t2:
                t2_selected = existing_pred == row["team2"]
                st.markdown(
                    f"<div style='text-align:center; padding:12px; "
                    f"background:{'#1a472a' if t2_selected else '#1a1a2e'}; "
                    f"border-radius:10px; color:white; border: {'2px solid #2ecc71' if t2_selected else 'none'};'>"
                    f"<b>{row['team2']}</b>"
                    f"{'<br>✅ Your Pick' if t2_selected else ''}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            with col_pred:
                options = [row["team1"], row["team2"]]
                default_idx = 0
                if existing_pred in options:
                    default_idx = options.index(existing_pred)

                with st.form(key=f"pred_form_{mid}"):
                    choice = st.radio(
                        "Pick the winner:",
                        options=options,
                        index=default_idx,
                        horizontal=True,
                        key=f"radio_{mid}",
                    )
                    btn_label = "Update Pick ✏️" if existing_pred else "Submit Pick 🎯"
                    submitted = st.form_submit_button(btn_label, use_container_width=True)

                if submitted:
                    ok, msg = save_prediction(user["id"], mid, choice)
                    if ok:
                        pred_map[mid] = choice
                        st.success(f"✅ Saved: **{choice}** for Match {mid}")
                        st.rerun()
                    else:
                        st.error(f"Error: {msg}")

            st.divider()


# ── Past matches ──────────────────────────────────────────────────────────────
with st.expander("📜 Past Matches & Your Predictions", expanded=False):
    if past.empty:
        st.info("No past matches yet.")
    else:
        # Merge results
        past_merged = past.merge(
            results_df.rename(columns={"winner": "actual_winner"}),
            on="match_id",
            how="left",
        )

        for _, row in past_merged.iterrows():
            mid = int(row["match_id"])
            match_date_str = row["match_date"].strftime("%a, %d %b %Y")
            my_pick = pred_map.get(mid, "—")
            actual = row.get("actual_winner", None)

            result_icon = ""
            if pd.notna(actual) and actual != "":
                if my_pick == actual:
                    result_icon = "✅"
                elif my_pick == "—":
                    result_icon = "⚠️ No pick"
                else:
                    result_icon = "❌"
            else:
                result_icon = "⏳"

            col_a, col_b, col_c, col_d = st.columns([2, 2, 2, 2])
            col_a.markdown(f"**Match {mid}** — {match_date_str}")
            col_b.markdown(f"⚔️ {row['team1']} vs {row['team2']}")
            col_c.markdown(f"🎯 My Pick: **{my_pick}**")
            if pd.notna(actual) and actual != "":
                col_d.markdown(f"🏆 Winner: **{actual}** {result_icon}")
            else:
                col_d.markdown(f"⏳ Result pending")
            st.divider()
