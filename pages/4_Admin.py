import streamlit as st
import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database import (
    init_db,
    load_matches,
    get_all_results,
    set_match_result,
    get_all_users,
    get_all_predictions,
    compute_leaderboard,
)
from utils.nav import render_sidebar

st.set_page_config(page_title="Admin Panel | IPL Fantasy 2026", page_icon="⚙️", layout="wide")
init_db()

# ── Auth guard ────────────────────────────────────────────────────────────────
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("🔒 Please log in first.")
    st.page_link("app.py", label="Go to Login", icon="🔐")
    st.stop()

user = st.session_state.user

if user.get("role") != "admin":
    st.error("🚫 Access denied. This page is for administrators only.")
    st.page_link("pages/1_Home.py", label="← Back to Dashboard")
    st.stop()


# ── Sidebar ───────────────────────────────────────────────────────────────────
def logout():
    st.session_state.logged_in = False
    st.session_state.user = None
    st.rerun()


render_sidebar(user, logout)


# ── Page header ───────────────────────────────────────────────────────────────
st.title("⚙️ Admin Panel")
st.markdown("Manage match results, view all predictions, and oversee users.")
st.divider()

# ── Load data ─────────────────────────────────────────────────────────────────
matches_df = load_matches()
results_df = get_all_results()
all_users = get_all_users()

# ── Quick stats ───────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("👥 Total Users", len(all_users[all_users["role"] == "user"]))
col2.metric("🏏 Total Matches", len(matches_df))
col3.metric("✅ Results Entered", len(results_df))
col4.metric("⏳ Pending Results", len(matches_df) - len(results_df))

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_results, tab_users, tab_predictions, tab_leaderboard, tab_upload = st.tabs(
    ["🏆 Enter Results", "👥 Users", "🎯 All Predictions", "📊 Leaderboard & Exports", "📤 Upload Schedule"]
)


# ── Enter Results tab ─────────────────────────────────────────────────────────
with tab_results:
    st.subheader("🏆 Enter / Update Match Results")
    st.markdown("Select a match and declare the winner. This will automatically update the leaderboard.")

    # Build completed set
    completed_ids = set(results_df["match_id"].tolist()) if not results_df.empty else set()

    # Merge existing results into matches
    if not results_df.empty:
        matches_with_results = matches_df.merge(
            results_df.rename(columns={"winner": "current_winner", "updated_at": "result_updated_at"}),
            on="match_id",
            how="left",
        )
    else:
        matches_with_results = matches_df.copy()
        matches_with_results["current_winner"] = None
        matches_with_results["result_updated_at"] = None

    matches_with_results = matches_with_results.sort_values("match_date")

    # Filter
    result_filter = st.radio(
        "Show matches:",
        ["All", "Pending Results", "Results Entered"],
        horizontal=True,
    )

    if result_filter == "Pending Results":
        filtered = matches_with_results[matches_with_results["current_winner"].isna()]
    elif result_filter == "Results Entered":
        filtered = matches_with_results[matches_with_results["current_winner"].notna()]
    else:
        filtered = matches_with_results

    st.markdown(f"Showing **{len(filtered)}** matches")
    st.divider()

    for _, row in filtered.iterrows():
        mid = int(row["match_id"])
        match_date_str = row["match_date"].strftime("%a, %d %b %Y")
        current_winner = row.get("current_winner")

        with st.container():
            col_info, col_form = st.columns([3, 2])

            with col_info:
                st.markdown(
                    f"**Match {mid}** — {match_date_str} {row['match_time']}"
                )
                st.markdown(f"⚔️ **{row['team1']}** vs **{row['team2']}**")
                st.markdown(f"🏟️ {row['venue']}, {row['city']}")
                if pd.notna(current_winner) and current_winner:
                    st.success(f"✅ Current result: **{current_winner}**")
                else:
                    st.warning("⏳ No result entered yet")

            with col_form:
                options = [row["team1"], row["team2"]]
                default_idx = 0
                if pd.notna(current_winner) and current_winner in options:
                    default_idx = options.index(current_winner)

                with st.form(key=f"result_form_{mid}"):
                    winner_choice = st.selectbox(
                        "Declare winner:",
                        options=options,
                        index=default_idx,
                        key=f"winner_sel_{mid}",
                    )
                    btn_text = "Update Result ✏️" if (pd.notna(current_winner) and current_winner) else "Save Result ✅"
                    if st.form_submit_button(btn_text, use_container_width=True):
                        set_match_result(mid, winner_choice)
                        st.success(f"✅ Result saved: Match {mid} → **{winner_choice}**")
                        st.rerun()

            st.divider()


# ── Users tab ─────────────────────────────────────────────────────────────────
with tab_users:
    st.subheader("👥 Registered Users")

    regular_users = all_users[all_users["role"] == "user"].copy()
    st.markdown(f"**{len(regular_users)}** registered players")

    if regular_users.empty:
        st.info("No users registered yet.")
    else:
        display_users = regular_users[["id", "display_name", "email", "team_name", "created_at"]].copy()
        display_users.columns = ["ID", "Name", "Email", "Fantasy Team", "Joined"]
        display_users["Joined"] = pd.to_datetime(display_users["Joined"]).dt.strftime("%d %b %Y")
        st.dataframe(display_users, use_container_width=True, hide_index=True)

        # Download CSV
        csv = display_users.to_csv(index=False)
        st.download_button(
            "📥 Download Users CSV",
            data=csv,
            file_name="ipl_fantasy_users.csv",
            mime="text/csv",
        )


# ── All Predictions tab ───────────────────────────────────────────────────────
with tab_predictions:
    st.subheader("🎯 All Predictions")

    all_preds = get_all_predictions()

    if all_preds.empty:
        st.info("No predictions made yet.")
    else:
        # Enrich with match info
        enriched = all_preds.merge(
            matches_df[["match_id", "team1", "team2", "match_date"]],
            on="match_id",
            how="left",
        )
        if not results_df.empty:
            enriched = enriched.merge(results_df, on="match_id", how="left")
            enriched["correct"] = enriched.apply(
                lambda r: "✅" if pd.notna(r.get("winner")) and r["predicted_winner"] == r["winner"]
                else ("❌" if pd.notna(r.get("winner")) else "⏳"),
                axis=1,
            )
        else:
            enriched["winner"] = None
            enriched["correct"] = "⏳"

        enriched = enriched.sort_values(["match_id", "display_name"])

        # Filter by match
        match_options = ["All Matches"] + [
            f"Match {int(r['match_id'])}: {r['team1']} vs {r['team2']}"
            for _, r in matches_df.sort_values("match_id").iterrows()
        ]
        selected_match = st.selectbox("Filter by match:", match_options)

        if selected_match != "All Matches":
            mid_filter = int(selected_match.split(":")[0].replace("Match ", "").strip())
            enriched = enriched[enriched["match_id"] == mid_filter]

        display_preds = enriched[
            ["match_id", "display_name", "team_name", "predicted_winner", "winner", "correct", "created_at"]
        ].copy()
        display_preds.columns = ["Match #", "Player", "Fantasy Team", "Predicted Winner", "Actual Winner", "Result", "Predicted At"]
        display_preds["Actual Winner"] = display_preds["Actual Winner"].fillna("—")
        display_preds["Predicted At"] = pd.to_datetime(display_preds["Predicted At"]).dt.strftime("%d %b %Y %H:%M")

        st.dataframe(display_preds, use_container_width=True, hide_index=True)
        st.caption(f"Total predictions: **{len(display_preds)}**")

        # Download
        csv_preds = display_preds.to_csv(index=False)
        st.download_button(
            "📥 Download Predictions CSV",
            data=csv_preds,
            file_name="ipl_fantasy_predictions.csv",
            mime="text/csv",
        )


# ── Leaderboard & Exports tab ─────────────────────────────────────────────────
with tab_leaderboard:
    st.subheader("📊 Leaderboard")
    st.markdown("Full rankings based on correct predictions. Download as CSV to share with the team.")

    lb = compute_leaderboard()

    if lb.empty:
        st.info("No leaderboard data yet. Results need to be entered first.")
    else:
        results_df_lb = get_all_results()
        completed_count = len(results_df_lb)

        lc1, lc2, lc3 = st.columns(3)
        lc1.metric("👥 Players Ranked", len(lb))
        lc2.metric("✅ Matches Completed", completed_count)
        top_player = lb.iloc[0]["display_name"] if len(lb) > 0 else "—"
        lc3.metric("🥇 Current Leader", top_player)

        st.divider()

        # Top 3 podium
        podium_cols = st.columns(3)
        medals = ["🥇", "🥈", "🥉"]
        for i, (medal, col) in enumerate(zip(medals, podium_cols)):
            if i < len(lb):
                row = lb.iloc[i]
                with col:
                    st.markdown(
                        f"<div style='text-align:center; padding:16px; "
                        f"background:#1a1a2e; border-radius:12px; color:white;'>"
                        f"<div style='font-size:2em;'>{medal}</div>"
                        f"<b>{row['display_name']}</b><br>"
                        f"<span style='color:#aaa;'>{row['team_name']}</span><br>"
                        f"<span style='color:#ffd700; font-size:1.3em;'>"
                        f"{int(row['correct_predictions'])} pts</span><br>"
                        f"<span style='color:#aaa; font-size:0.85em;'>"
                        f"Accuracy: {row['accuracy']}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
        st.divider()

        # Full table
        display_lb = lb[["rank", "display_name", "team_name", "correct_predictions", "total_predictions", "accuracy"]].copy()
        display_lb.columns = ["Rank", "Player", "Fantasy Team", "Correct Picks", "Total Predictions", "Accuracy"]
        st.dataframe(display_lb, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("📥 Download Exports")

        dl1, dl2, dl3 = st.columns(3)

        # Leaderboard CSV
        lb_csv = display_lb.to_csv(index=False)
        dl1.download_button(
            "📊 Download Leaderboard CSV",
            data=lb_csv,
            file_name="ipl_fantasy_leaderboard.csv",
            mime="text/csv",
            use_container_width=True,
        )

        # All predictions CSV
        all_preds_export = get_all_predictions()
        if not all_preds_export.empty:
            enriched_export = all_preds_export.merge(
                matches_df[["match_id", "team1", "team2", "match_date"]],
                on="match_id", how="left"
            )
            if not results_df.empty:
                enriched_export = enriched_export.merge(results_df, on="match_id", how="left")
                enriched_export["correct"] = enriched_export.apply(
                    lambda r: "Yes" if pd.notna(r.get("winner")) and r["predicted_winner"] == r["winner"]
                    else ("No" if pd.notna(r.get("winner")) else "Pending"),
                    axis=1,
                )
            else:
                enriched_export["winner"] = None
                enriched_export["correct"] = "Pending"
            preds_csv = enriched_export[
                ["match_id", "display_name", "team_name", "predicted_winner", "winner", "correct", "created_at"]
            ].to_csv(index=False)
            dl2.download_button(
                "🎯 Download Predictions CSV",
                data=preds_csv,
                file_name="ipl_fantasy_all_predictions.csv",
                mime="text/csv",
                use_container_width=True,
            )

        # Users CSV
        users_export = all_users[all_users["role"] == "user"][
            ["id", "display_name", "email", "team_name", "created_at"]
        ].copy()
        users_export.columns = ["ID", "Name", "Email", "Fantasy Team", "Joined"]
        users_csv = users_export.to_csv(index=False)
        dl3.download_button(
            "👥 Download Users CSV",
            data=users_csv,
            file_name="ipl_fantasy_users.csv",
            mime="text/csv",
            use_container_width=True,
        )


# ── Upload Schedule tab ───────────────────────────────────────────────────────
with tab_upload:
    st.subheader("📤 Upload Match Schedule")
    st.markdown(
        "Upload a new `matches.csv` to update the match schedule. "
        "The file must have these columns: "
        "`match_id, match_date, match_time, team1, team2, venue, city`"
    )

    st.markdown("**Required CSV format:**")
    sample = pd.DataFrame({
        "match_id": [1, 2],
        "match_date": ["2026-03-22", "2026-03-23"],
        "match_time": ["19:30", "15:30"],
        "team1": ["Mumbai Indians", "Chennai Super Kings"],
        "team2": ["Chennai Super Kings", "Royal Challengers Bengaluru"],
        "venue": ["Wankhede Stadium", "MA Chidambaram Stadium"],
        "city": ["Mumbai", "Chennai"],
    })
    st.dataframe(sample, use_container_width=True, hide_index=True)

    uploaded = st.file_uploader("Choose matches.csv", type=["csv"])
    if uploaded:
        try:
            new_df = pd.read_csv(uploaded)
            required_cols = {"match_id", "match_date", "match_time", "team1", "team2", "venue", "city"}
            if not required_cols.issubset(set(new_df.columns)):
                missing = required_cols - set(new_df.columns)
                st.error(f"Missing columns: {missing}")
            else:
                st.success(f"✅ Valid file — {len(new_df)} matches found.")
                st.dataframe(new_df, use_container_width=True, hide_index=True)
                if st.button("💾 Save as new schedule", use_container_width=True):
                    new_df.to_csv("data/matches.csv", index=False)
                    st.success("Schedule updated! Refresh the app to see changes.")
        except Exception as e:
            st.error(f"Error reading file: {e}")

    st.divider()
    st.subheader("📋 Current Schedule")
    current = load_matches()
    st.dataframe(
        current[["match_id", "match_date", "match_time", "team1", "team2", "venue", "city"]],
        use_container_width=True,
        hide_index=True,
    )
