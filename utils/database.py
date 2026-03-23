import sqlite3
import os
import bcrypt
import pandas as pd
from datetime import datetime

DB_PATH = "data/ipl_fantasy.db"


def get_connection():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()

    # Users table — email is the login identifier (unique)
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT NOT NULL,
            team_name TEXT,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Predictions table
    c.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            match_id INTEGER NOT NULL,
            predicted_winner TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, match_id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Match results table
    c.execute("""
        CREATE TABLE IF NOT EXISTS match_results (
            match_id INTEGER PRIMARY KEY,
            winner TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()

    # Create default admin if not exists
    admin_exists = c.execute(
        "SELECT id FROM users WHERE email = 'admin@iplf.com'"
    ).fetchone()
    if not admin_exists:
        pw_hash = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
        c.execute(
            """INSERT INTO users (email, password_hash, display_name, team_name, role)
               VALUES (?, ?, ?, ?, ?)""",
            ("admin@iplf.com", pw_hash, "Administrator", "Admin Team", "admin"),
        )
        conn.commit()

    conn.close()


# ── Auth ──────────────────────────────────────────────────────────────────────

def create_user(email, password, display_name, team_name):
    conn = get_connection()
    c = conn.cursor()
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        c.execute(
            """INSERT INTO users (email, password_hash, display_name, team_name)
               VALUES (?, ?, ?, ?)""",
            (email.strip().lower(), pw_hash, display_name, team_name),
        )
        conn.commit()
        return True, "Account created successfully!"
    except sqlite3.IntegrityError:
        return False, "An account with this email already exists."
    finally:
        conn.close()


def verify_user(email, password):
    conn = get_connection()
    c = conn.cursor()
    row = c.execute(
        "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
    ).fetchone()
    conn.close()
    if row and bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
        return dict(row)
    return None


def get_user_by_id(user_id):
    conn = get_connection()
    c = conn.cursor()
    row = c.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_users():
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT id, email, display_name, team_name, role, created_at FROM users",
        conn,
    )
    conn.close()
    return df


def update_user_profile(user_id, display_name, email, team_name):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE users SET display_name=?, email=?, team_name=? WHERE id=?",
        (display_name, email.strip().lower(), team_name, user_id),
    )
    conn.commit()
    conn.close()


def change_password(user_id, new_password):
    conn = get_connection()
    c = conn.cursor()
    pw_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    c.execute("UPDATE users SET password_hash=? WHERE id=?", (pw_hash, user_id))
    conn.commit()
    conn.close()


# ── Matches ───────────────────────────────────────────────────────────────────

def load_matches():
    df = pd.read_csv("data/matches.csv")
    df["match_date"] = pd.to_datetime(df["match_date"])
    return df


def get_match_result(match_id):
    conn = get_connection()
    c = conn.cursor()
    row = c.execute(
        "SELECT winner FROM match_results WHERE match_id = ?", (match_id,)
    ).fetchone()
    conn.close()
    return row["winner"] if row else None


def set_match_result(match_id, winner):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """INSERT INTO match_results (match_id, winner, updated_at)
           VALUES (?, ?, ?)
           ON CONFLICT(match_id) DO UPDATE SET winner=excluded.winner, updated_at=excluded.updated_at""",
        (match_id, winner, datetime.now()),
    )
    conn.commit()
    conn.close()


def get_all_results():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM match_results", conn)
    conn.close()
    return df


# ── Predictions ───────────────────────────────────────────────────────────────

def save_prediction(user_id, match_id, predicted_winner):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            """INSERT INTO predictions (user_id, match_id, predicted_winner)
               VALUES (?, ?, ?)
               ON CONFLICT(user_id, match_id) DO UPDATE SET
               predicted_winner=excluded.predicted_winner,
               created_at=CURRENT_TIMESTAMP""",
            (user_id, match_id, predicted_winner),
        )
        conn.commit()
        return True, "Prediction saved!"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def get_user_predictions(user_id):
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM predictions WHERE user_id = ?", conn, params=(user_id,)
    )
    conn.close()
    return df


def get_all_predictions():
    conn = get_connection()
    df = pd.read_sql_query(
        """SELECT p.*, u.display_name, u.team_name
           FROM predictions p
           JOIN users u ON p.user_id = u.id""",
        conn,
    )
    conn.close()
    return df


# ── Leaderboard ───────────────────────────────────────────────────────────────

def compute_leaderboard():
    conn = get_connection()
    df = pd.read_sql_query(
        """SELECT
               u.id,
               u.display_name,
               u.team_name,
               COUNT(p.id) AS total_predictions,
               SUM(CASE WHEN p.predicted_winner = mr.winner THEN 1 ELSE 0 END) AS correct_predictions
           FROM users u
           LEFT JOIN predictions p ON u.id = p.user_id
           LEFT JOIN match_results mr ON p.match_id = mr.match_id
           WHERE u.role = 'user'
           GROUP BY u.id, u.display_name, u.team_name
           ORDER BY correct_predictions DESC, total_predictions DESC""",
        conn,
    )
    conn.close()
    df["correct_predictions"] = df["correct_predictions"].fillna(0).astype(int)
    df["total_predictions"] = df["total_predictions"].fillna(0).astype(int)
    df["accuracy"] = df.apply(
        lambda r: f"{(r['correct_predictions'] / r['total_predictions'] * 100):.0f}%"
        if r["total_predictions"] > 0
        else "N/A",
        axis=1,
    )
    df.insert(0, "rank", range(1, len(df) + 1))
    return df
