"""
Utility script to delete a user by email from data/ipl_fantasy.db.

Usage (local or VM, from project root with venv if you want):

  .\ipl\Scripts\python delete_user.py

Then type the email when prompted.
"""

import sqlite3


def main():
    email = input("Enter email to delete from users table: ").strip().lower()
    if not email:
        print("No email provided. Aborting.")
        return

    conn = sqlite3.connect("data/ipl_fantasy.db")
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE email = ?", (email,))
    conn.commit()
    print(f"Deleted rows: {cur.rowcount}")
    conn.close()


if __name__ == "__main__":
    main()
