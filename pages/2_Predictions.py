import streamlit as st
import pandas as pd
from datetime import date
import sys
import os
import base64

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
from utils.qgenie import get_ai_prediction

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
now_ts = pd.Timestamp.now()

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

# ── Helper: encode image to base64 ───────────────────────────────────────────
def img_to_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


# ── Helper: render a team card with logo ──────────────────────────────────────
def team_card(team_name: str, is_selected: bool):
    logo_path = get_logo(team_name)
    short = get_short(team_name)
    border = "3px solid #2ecc71" if is_selected else "1px solid #444"
    bg = "#1a472a" if is_selected else "#1a1a2e"
    badge = "<div style='color:#2ecc71; font-size:0.75em; margin-bottom:6px;'>✅ Your Pick</div>" if is_selected else "<div style='height:20px;'></div>"

    if logo_path:
        b64 = img_to_b64(logo_path)
        img_tag = f"<img src='data:image/png;base64,{b64}' style='width:80px; height:80px; object-fit:contain; margin:8px auto; display:block;'/>"
    else:
        img_tag = f"<div style='width:80px; height:80px; margin:8px auto; display:flex; align-items:center; justify-content:center; color:#aaa;'>🏏</div>"

    html = f"""
    <div style='text-align:center; padding:12px 8px; background:{bg};
                border-radius:12px; border:{border}; min-height:160px;
                display:flex; flex-direction:column; align-items:center; justify-content:center;'>
        {badge}
        {img_tag}
        <div style='color:white; font-weight:bold; font-size:0.9em; margin-top:6px;'>{short}</div>
        <div style='color:#aaa; font-size:0.75em; margin-top:2px;'>{team_name}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# ── Upcoming matches ──────────────────────────────────────────────────────────
st.subheader("📅 Upcoming Matches — Make Your Picks")

if upcoming.empty:
    st.info("No upcoming matches to predict right now. Check back later!")
else:
    for _, row in upcoming.iterrows():
        mid = int(row["match_id"])
        match_date_str = row["match_date"].strftime("%a, %d %b %Y")
        existing_pred = pred_map.get(mid)
        match_start = pd.to_datetime(
            row["match_date"].strftime("%Y-%m-%d") + " " + row["match_time"],
            errors="coerce",
        )
        predictions_locked = pd.notna(match_start) and now_ts >= match_start

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
                        disabled=predictions_locked,
                    )
                    btn_label = "Update Pick ✏️" if existing_pred else "Submit Pick 🎯"
                    submitted = st.form_submit_button(
                        btn_label,
                        use_container_width=True,
                        disabled=predictions_locked,
                    )

                if predictions_locked:
                    st.warning("⏳ Predictions closed — match has started.")

                if submitted:
                    ok, msg = save_prediction(user["id"], mid, choice)
                    if ok:
                        pred_map[mid] = choice
                        st.success(f"✅ Saved: **{choice}** for Match {mid}")
                        st.rerun()
                    else:
                        st.error(f"Error: {msg}")

                # ── Ask QGenie button ──────────────────────────────────────
                st.markdown("---")
                if st.button("🤖 Ask AI", key=f"qgenie_btn_{mid}", use_container_width=True, help="Get a fresh QGenie powered prediction"):
                    with st.spinner("🤖 QGenie is analysing the match..."):
                        ai = get_ai_prediction(
                            team1=row["team1"],
                            team2=row["team2"],
                            venue=row["venue"],
                            city=row["city"],
                            match_date=row["match_date"].strftime("%d %b %Y"),
                            match_time=row["match_time"],
                        )

                    if "error" in ai:
                        st.error(f"QGenie error: {ai['error']}")
                    else:
                        winner = ai.get("predicted_winner", "")
                        prob = ai.get("win_probability", "")
                        headline = ai.get("headline", "")
                        factors = ai.get("factors", [])

                        st.markdown(
                            f"<div style='background:#0d2137; border:1px solid #1e88e5; "
                            f"border-radius:10px; padding:12px; margin-top:8px;'>"
                            f"<div style='color:#1e88e5; font-size:0.75em; font-weight:bold; "
                            f"margin-bottom:4px;'>🤖 QGENIE PREDICTION</div>"
                            f"<div style='color:#ffd700; font-weight:bold; font-size:0.95em;'>"
                            f"🏆 {winner} &nbsp;·&nbsp; {prob}</div>"
                            f"<div style='color:#e0e0e0; font-size:0.82em; margin-top:4px; "
                            f"font-style:italic;'>{headline}</div>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

                        with st.expander("📊 View Full Analysis", expanded=True):
                            icons = ["📈", "⚔️", "🏟️", "⭐", "🩺"]
                            for i, factor in enumerate(factors):
                                icon = icons[i] if i < len(icons) else "•"
                                st.markdown(
                                    f"**{icon} {factor.get('title', '')}**  \n"
                                    f"{factor.get('detail', '')}"
                                )
                                if i < len(factors) - 1:
                                    st.markdown("---")

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
                logo1 = get_logo(row["team1"])
                logo2 = get_logo(row["team2"])
                mini_imgs = ""
                if logo1:
                    b1 = img_to_b64(logo1)
                    mini_imgs += f"<img src='data:image/png;base64,{b1}' style='width:32px; height:32px; object-fit:contain; margin-right:6px;'/>"
                if logo2:
                    b2 = img_to_b64(logo2)
                    mini_imgs += f"<img src='data:image/png;base64,{b2}' style='width:32px; height:32px; object-fit:contain;'/>"
                if mini_imgs:
                    st.markdown(f"<div style='margin-top:4px;'>{mini_imgs}</div>", unsafe_allow_html=True)

            col_b.markdown(f"⚔️ {get_short(row['team1'])} vs {get_short(row['team2'])}")
            col_c.markdown(f"🎯 My Pick: **{my_pick}**")
            if pd.notna(actual) and actual != "":
                col_d.markdown(f"🏆 Winner: **{actual}** {result_icon}")
            else:
                col_d.markdown("⏳ Result pending")
            st.divider()
