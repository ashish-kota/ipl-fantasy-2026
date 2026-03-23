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


with st.sidebar:
    st.markdown(f"### 👤 {user['display_name']}")
    st.markdown(f"🏏 **Team:** {user.get('team_name', '—')}")
    st.markdown(f"📧 {user.get('email', '')}")
    st.divider()
    st.page_link("app.py", label="🏠 Home")
    st.page_link("pages/1_Home.py", label="📊 Dashboard")
    st.page_link("pages/2_Predictions.py", label="🎯 Predictions")
    st.page_link("pages/3_Leaderboard.py", label="🏆 Leaderboard")
    st.page_link("pages/4_Admin.py", label="⚙️ Admin Panel")
    st.divider()
    if st.button("🚪 Logout", use_container_width=True):
        logout()


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
tab_results, tab_users, tab_predictions, tab_upload = st.tabs(
    ["🏆 Enter Results", "👥 Users", "🎯 All Predictions", "📤 Upload Schedule"]
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
