import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database import init_db, compute_leaderboard, get_user_predictions, get_all_results

st.set_page_config(page_title="Leaderboard | IPL Fantasy 2026", page_icon="🏆", layout="wide")
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
st.title("🏆 Leaderboard")
st.markdown("Rankings are based on correct match winner predictions.")
st.divider()

# ── Load leaderboard ──────────────────────────────────────────────────────────
lb = compute_leaderboard()
results_df = get_all_results()
completed_count = len(results_df)

if lb.empty:
    st.info("No data yet. Leaderboard will populate once users make predictions and results are entered.")
    st.stop()

# ── Find current user's rank ──────────────────────────────────────────────────
my_row = lb[lb["id"] == user["id"]]
my_rank = int(my_row["rank"].values[0]) if not my_row.empty else None
my_correct = int(my_row["correct_predictions"].values[0]) if not my_row.empty else 0
my_total = int(my_row["total_predictions"].values[0]) if not my_row.empty else 0

# ── Stats strip ───────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("👥 Total Players", len(lb))
col2.metric("✅ Matches Completed", completed_count)
col3.metric("🎯 Your Rank", f"#{my_rank}" if my_rank else "—")
col4.metric("✅ Your Correct Picks", f"{my_correct} / {my_total}" if my_total else "0")

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_table, tab_chart = st.tabs(["📋 Rankings Table", "📊 Chart"])

# ── Rankings table ────────────────────────────────────────────────────────────
with tab_table:
    st.subheader("📋 Full Rankings")

    # Top 3 podium
    if len(lb) >= 1:
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

    # Highlight current user
    def highlight_user(row):
        if row["Player"] == user["display_name"]:
            return ["background-color: #1a472a; color: white"] * len(row)
        return [""] * len(row)

    styled = display_lb.style.apply(highlight_user, axis=1)
    st.dataframe(styled, use_container_width=True, hide_index=True)

    if my_rank:
        st.caption(f"🟢 Your row is highlighted in green — You are ranked **#{my_rank}**")


# ── Chart tab ─────────────────────────────────────────────────────────────────
with tab_chart:
    st.subheader("📊 Correct Predictions — Top Players")

    chart_df = lb[lb["correct_predictions"] > 0].head(20).copy()

    if chart_df.empty:
        st.info("No correct predictions recorded yet. Check back after match results are entered.")
    else:
        chart_df["color"] = chart_df["id"].apply(
            lambda uid: "You" if uid == user["id"] else "Others"
        )

        fig = px.bar(
            chart_df,
            x="display_name",
            y="correct_predictions",
            color="color",
            color_discrete_map={"You": "#2ecc71", "Others": "#3498db"},
            labels={"display_name": "Player", "correct_predictions": "Correct Picks"},
            title="Correct Predictions per Player (Top 20)",
            text="correct_predictions",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            xaxis_tickangle=-30,
            showlegend=True,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="white",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Accuracy chart
        acc_df = lb[lb["total_predictions"] > 0].copy()
        acc_df["accuracy_num"] = acc_df["correct_predictions"] / acc_df["total_predictions"] * 100
        acc_df = acc_df.sort_values("accuracy_num", ascending=False).head(20)

        fig2 = px.bar(
            acc_df,
            x="display_name",
            y="accuracy_num",
            color=acc_df["id"].apply(lambda uid: "You" if uid == user["id"] else "Others"),
            color_discrete_map={"You": "#2ecc71", "Others": "#e74c3c"},
            labels={"display_name": "Player", "accuracy_num": "Accuracy (%)"},
            title="Prediction Accuracy % (Top 20)",
            text=acc_df["accuracy_num"].apply(lambda x: f"{x:.0f}%"),
        )
        fig2.update_traces(textposition="outside")
        fig2.update_layout(
            xaxis_tickangle=-30,
            showlegend=True,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            yaxis_range=[0, 110],
        )
        st.plotly_chart(fig2, use_container_width=True)
