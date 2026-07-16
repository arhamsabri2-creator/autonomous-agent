import psycopg2
import os
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash

def get_db():
    conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            plan TEXT DEFAULT 'free',
            runs_today INTEGER DEFAULT 0,
            last_run_date DATE
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

def create_user(name, email, password):
    conn = get_db()
    cursor = conn.cursor()
    hashed = generate_password_hash(password)
    try:
        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
            (name, email, hashed)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True, "User created"
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            return False, "Email already exists"
        return False, str(e)

def get_user_by_email(email):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

def get_user_by_id(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

def verify_password(email, password):
    user = get_user_by_email(email)
    if not user:
        return False, None
    if check_password_hash(user[3], password):
        return True, user
    return False, None

def check_and_update_usage(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT plan, runs_today, last_run_date FROM users WHERE id = %s", (user_id,))
    row = cursor.fetchone()
    plan, runs_today, last_run_date = row
    today = date.today()
    if last_run_date != today:
        runs_today = 0
    if plan == 'free' and runs_today >= 3:
        cursor.close()
        conn.close()
        return False, f"You have used all 3 free runs for today. Upgrade to Pro for unlimited access."
    cursor.execute(
        "UPDATE users SET runs_today = %s, last_run_date = %s WHERE id = %s",
        (runs_today + 1, today, user_id)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return True, "Run allowed"

def upgrade_to_pro(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET plan = 'pro' WHERE id = %s", (user_id,)
    )
    conn.commit()
    cursor.close()
    conn.close()

init_db()