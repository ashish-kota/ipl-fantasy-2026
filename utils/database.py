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

    # Registration / auth logs
    c.execute("""
        CREATE TABLE IF NOT EXISTS auth_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,        -- 'register_fail', 'register_success', 'login_fail', 'login_success'
            email TEXT,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Password reset requests
    c.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            note TEXT,
            status TEXT DEFAULT 'pending',   -- 'pending', 'done'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            handled_at TIMESTAMP
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


def change_password_by_email(email, new_password):
    """Helper for admin reset: change password by email."""
    conn = get_connection()
    c = conn.cursor()
    pw_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    c.execute(
        "UPDATE users SET password_hash=? WHERE email=?",
        (pw_hash, email.strip().lower()),
    )
    conn.commit()
    conn.close()


# ── Password reset requests ───────────────────────────────────────────────────

def create_password_reset_request(email, note):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO password_reset_requests (email, note) VALUES (?, ?)",
        (email.strip().lower(), note),
    )
    conn.commit()
    conn.close()


def get_pending_password_reset_requests():
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT id, email, note, status, created_at
        FROM password_reset_requests
        WHERE status = 'pending'
        ORDER BY created_at ASC
        """,
        conn,
    )
    conn.close()
    return df


def mark_password_reset_done(request_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        UPDATE password_reset_requests
        SET status = 'done', handled_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (request_id,),
    )
    conn.commit()
    conn.close()


# ── Logging ───────────────────────────────────────────────────────────────────

def log_auth_event(event_type, email, details):
    """Simple logger for auth/registration events."""
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO auth_logs (event_type, email, details) VALUES (?, ?, ?)",
        (event_type, (email or "").strip().lower(), details),
    )
    conn.commit()
    conn.close()


# ── Matches ───────────────────────────────────────────────────────────────────

def load_matches():
    xlsx_path = "data/matches.xlsx"
    csv_path = "data/matches.csv"

    if os.path.exists(xlsx_path):
        raw = pd.read_excel(xlsx_path, sheet_name="Schedule")
        df = pd.DataFrame(
            {
                "match_id": raw["MatchNo"],
                "match_date": pd.to_datetime(raw["MatchDate"]),
                "match_time": raw["StartTime"].astype(str),
                "team1": raw["HomeTeam"],
                "team2": raw["AwayTeam"],
                "venue": raw["HomeTeam"],
                "city": raw["City"],
            }
        )

        if "StartDateTime" in raw.columns:
            df["match_start"] = pd.to_datetime(raw["StartDateTime"], errors="coerce")
        else:
            df["match_start"] = pd.to_datetime(
                df["match_date"].dt.strftime("%Y-%m-%d") + " " + df["match_time"],
                errors="coerce",
            )

        return df

    df = pd.read_csv(csv_path)
    df["match_date"] = pd.to_datetime(df["match_date"])
    df["match_start"] = pd.to_datetime(
        df["match_date"].dt.strftime("%Y-%m-%d") + " " + df["match_time"],
        errors="coerce",
    )
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
    matches = load_matches()
    row = matches[matches["match_id"] == match_id]

    if row.empty:
        return False, "Match not found."

    match_start = row.iloc[0]["match_start"]
    if pd.isna(match_start):
        return False, "Match start time is invalid."

    if pd.Timestamp.now() >= match_start:
        return False, "Predictions are closed for this match."

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
    # Completed matches (results entered)
    total_completed = pd.read_sql_query(
        "SELECT COUNT(*) AS cnt FROM match_results", conn
    )["cnt"].iloc[0]

    df = pd.read_sql_query(
        """SELECT
               u.id,
               u.display_name,
               u.team_name,
               COUNT(p.id) AS total_predictions,
               SUM(CASE WHEN mr.winner IS NOT NULL
                        AND mr.winner != 'No Result'
                        AND p.predicted_winner = mr.winner
                        THEN 1 ELSE 0 END) AS correct_predictions,
               SUM(
                   CASE
                       WHEN mr.winner IS NULL THEN 0
                       WHEN mr.winner = 'No Result' AND p.id IS NOT NULL THEN 5
                       WHEN mr.winner != 'No Result' AND p.predicted_winner = mr.winner THEN 10
                       ELSE 0
                   END
               ) AS points
           FROM users u
           LEFT JOIN predictions p ON u.id = p.user_id
           LEFT JOIN match_results mr ON p.match_id = mr.match_id
           WHERE u.role = 'user'
           GROUP BY u.id, u.display_name, u.team_name""",
        conn,
    )
    conn.close()

    df["correct_predictions"] = df["correct_predictions"].fillna(0).astype(int)
    df["total_predictions"] = df["total_predictions"].fillna(0).astype(int)
    df["points"] = df["points"].fillna(0).astype(int)

    completed_predictions = pd.read_sql_query(
        """SELECT
               p.user_id,
               COUNT(*) AS completed_predictions
           FROM predictions p
           JOIN match_results mr ON p.match_id = mr.match_id
           GROUP BY p.user_id""",
        get_connection(),
    )

    if not completed_predictions.empty:
        df = df.merge(
            completed_predictions,
            left_on="id",
            right_on="user_id",
            how="left",
        )
        df = df.drop(columns=["user_id"])
    else:
        df["completed_predictions"] = 0

    df["completed_predictions"] = df["completed_predictions"].fillna(0).astype(int)

    df["accuracy_value"] = df.apply(
        lambda r: (r["correct_predictions"] / r["completed_predictions"])
        if r["completed_predictions"] > 0
        else -1,
        axis=1,
    )

    df["accuracy"] = df["accuracy_value"].apply(
        lambda v: f"{v * 100:.0f}%" if v >= 0 else "N/A"
    )

    # Prediction % = completed predictions / matches with results updated
    def compute_pred_pct(row):
        if total_completed <= 0:
            return "0%"
        return f"{(row['completed_predictions'] / total_completed * 100):.0f}%"

    df["prediction_percentage"] = df.apply(compute_pred_pct, axis=1)

    df = df.sort_values(
        ["points", "accuracy_value", "completed_predictions", "total_predictions"],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)

    df.insert(0, "rank", range(1, len(df) + 1))
    return df
