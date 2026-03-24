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
    save_prediction,
)
from utils.nav import render_sidebar
from utils.teams import get_logo, get_short

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


render_sidebar(user, logout)


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

pred_map = {}
if not user_preds.empty:
    pred_map = dict(zip(user_preds["match_id"], user_preds["predicted_winner"]))

completed_ids = set(results_df["match_id"].tolist()) if not results_df.empty else set()
today = date.today()

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

# ── Helper: render a team card with logo ──────────────────────────────────────
def team_card(team_name: str, is_selected: bool):
    logo = get_logo(team_name)
    short = get_short(team_name)
    border = "2px solid #2ecc71" if is_selected else "1px solid #333"
    bg = "#1a472a" if is_selected else "#1a1a2e"
    badge = "<br><span style='color:#2ecc71; font-size:0.8em;'>✅ Your Pick</span>" if is_selected else ""

    if logo:
        st.markdown(
            f"<div style='text-align:center; padding:10px; background:{bg}; "
            f"border-radius:12px; border:{border};'>{badge}</div>",
            unsafe_allow_html=True,
        )
        st.image(logo, width=80, use_container_width=False)
        st.markdown(
            f"<div style='text-align:center; color:white; font-weight:bold; "
            f"font-size:0.85em; margin-top:4px;'>{short}<br>"
            f"<span style='font-size:0.75em; color:#aaa;'>{team_name}</span></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div style='text-align:center; padding:12px; background:{bg}; "
            f"border-radius:12px; color:white; border:{border};'>"
            f"<b>{team_name}</b>{badge}</div>",
            unsafe_allow_html=True,
        )


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
                f"⏰ {row['match_time']} &nbsp;|&nbsp; 📍 {row['city']}"
            )

            col_t1, col_vs, col_t2, col_pred = st.columns([2, 1, 2, 3])

            with col_t1:
                team_card(row["team1"], existing_pred == row["team1"])

            with col_vs:
                st.markdown(
                    "<div style='text-align:center; padding:30px 0; color:#ffd700; "
                    "font-size:1.4em; font-weight:bold;'>VS</div>",
                    unsafe_allow_html=True,
                )

            with col_t2:
                team_card(row["team2"], existing_pred == row["team2"])

            with col_pred:
                options = [row["team1"], row["team2"]]
                default_idx = 0
                if existing_pred in options:
                    default_idx = options.index(existing_pred)

                with st.form(key=f"pred_form_{mid}"):
                    choice = st.radio(
                        "Pick the winner:",
                        options=options,
                        format_func=lambda t: f"{get_short(t)} — {t}",
                        index=default_idx,
                        horizontal=False,
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
                result_icon = "✅" if my_pick == actual else ("⚠️ No pick" if my_pick == "—" else "❌")
            else:
                result_icon = "⏳"

            col_a, col_b, col_c, col_d = st.columns([2, 2, 2, 2])

            with col_a:
                st.markdown(f"**Match {mid}** — {match_date_str}")
                # Show mini logos
                logo1 = get_logo(row["team1"])
                logo2 = get_logo(row["team2"])
                lc1, lc2 = st.columns(2)
                if logo1:
                    lc1.image(logo1, width=40)
                if logo2:
                    lc2.image(logo2, width=40)

            col_b.markdown(f"⚔️ {get_short(row['team1'])} vs {get_short(row['team2'])}")
            col_c.markdown(f"🎯 My Pick: **{my_pick}**")
            if pd.notna(actual) and actual != "":
                col_d.markdown(f"🏆 Winner: **{actual}** {result_icon}")
            else:
                col_d.markdown("⏳ Result pending")
            st.divider()
