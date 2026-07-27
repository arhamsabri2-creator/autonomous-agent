import sqlite3
import os
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash

# ============================================================
# THE STORY:
# This file is Raza's customer register — the notebook where
# every customer's details are written down permanently.
# Name, email, password, which plan they are on, how many
# chais they have had today. Everything in one place.
#
# THE TECH:
# This file creates and manages a SQLite database called
# users.db. It has one table called users that stores
# every person who has signed up for the agent.
# ============================================================

DATABASE = "users.db"


def get_db():
    # ============================================================
    # THE STORY:
    # Every time Raza needs to look something up in his register
    # he opens it. This function opens the register.
    # When he is done he closes it again.
    #
    # THE TECH:
    # Creates a connection to the SQLite database file.
    # row_factory lets us access columns by name instead of
    # position — so we can say row["email"] instead of row[0]
    # ============================================================
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    # ============================================================
    # THE STORY:
    # Before Raza opens his stall for the first time he sets up
    # his register. He draws the columns — Name, Email, Password,
    # Plan, Runs Today, Date. This only needs to happen once.
    # After that the register is ready forever.
    #
    # THE TECH:
    # Creates the users table in SQLite if it does not already
    # exist. Each column stores one piece of information about
    # each user. IF NOT EXISTS means — only create it if it is
    # not already there. Safe to run multiple times.
    # ============================================================
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            plan TEXT DEFAULT 'free',
            runs_today INTEGER DEFAULT 0,
            last_run_date TEXT DEFAULT ''
        )
    """)
    conn.commit()
    conn.close()


def create_user(name, email, password):
    # ============================================================
    # THE STORY:
    # A new customer walks up to Raza's stall for the first time.
    # Raza writes their name and email in the register.
    # But for the password — he does not write it directly.
    # He scrambles it into a secret code first.
    # So even if someone steals the register they cannot
    # read anyone's password.
    #
    # THE TECH:
    # generate_password_hash takes the plain text password
    # and converts it into a long scrambled string.
    # This is called hashing — it is one way, meaning you
    # cannot reverse it back to the original password.
    # We store the hash, never the real password.
    # ============================================================
    try:
        conn = get_db()
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        conn.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            (name, email, hashed_password)
        )
        conn.commit()
        conn.close()
        return True, "Account created successfully"

    except sqlite3.IntegrityError:
        # ============================================================
        # THE STORY:
        # Someone tries to sign up with an email that is already
        # in the register. Raza says — sorry, this email is taken.
        #
        # THE TECH:
        # SQLite raises IntegrityError when a UNIQUE constraint
        # is violated — in this case the email column is UNIQUE
        # so two users cannot have the same email.
        # ============================================================
        return False, "Email already exists"

    except Exception as e:
        return False, str(e)


def get_user_by_email(email):
    # ============================================================
    # THE STORY:
    # A customer comes back to the stall. Raza looks them up
    # in the register by their email. He finds their record
    # and hands it back — name, plan, everything.
    #
    # THE TECH:
    # Queries the database for a user with the given email.
    # Returns the full row if found, or None if not found.
    # ============================================================
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE email = ?", (email,)
    ).fetchone()
    conn.close()
    return user


def get_user_by_id(user_id):
    # ============================================================
    # THE STORY:
    # Same as above but Raza looks up the customer by their
    # unique customer number instead of their email.
    #
    # THE TECH:
    # Queries the database by the user's id column.
    # Used by Flask-Login to load the current logged in user.
    # ============================================================
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return user


def verify_password(email, password):
    # ============================================================
    # THE STORY:
    # A customer comes to the stall and says their name and
    # password. Raza looks them up in the register. He takes
    # their password, scrambles it the same way, and checks
    # if it matches what is in the register.
    # If it matches — welcome back. If not — wrong password.
    #
    # THE TECH:
    # check_password_hash takes the plain text password the
    # user typed and the stored hash from the database.
    # It hashes the typed password and compares the two hashes.
    # Returns True if they match, False if they do not.
    # ============================================================
    user = get_user_by_email(email)
    if not user:
        return False, None
    if check_password_hash(user["password"], password):
        return True, user
    return False, None


def check_and_update_usage(user_id):
    # ============================================================
    # THE STORY:
    # A customer wants another chai. Raza checks his notebook.
    # Is this a free customer? If yes — how many chais have
    # they had today? If they have had 3 already — sorry,
    # you have reached your free limit for today.
    # If they are a pro customer — serve them immediately,
    # no questions asked.
    # Either way — mark one more chai in the notebook.
    #
    # THE TECH:
    # Checks the user's plan and runs_today count.
    # Free users are limited to 3 runs per day.
    # The last_run_date column tracks which day the count
    # is for — if it is a new day, the count resets to 0.
    # Pro users always get through regardless of count.
    # Returns True if the user can run, False if they cannot.
    # ============================================================
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    ).fetchone()

    today = str(date.today())

    # If it is a new day reset the run count to zero
    # This is how the daily limit refreshes automatically
    if user["last_run_date"] != today:
        conn.execute(
            "UPDATE users SET runs_today = 0, last_run_date = ? WHERE id = ?",
            (today, user_id)
        )
        conn.commit()
        runs_today = 0
    else:
        runs_today = user["runs_today"]

    # Pro users have no limit — always allow
    if user["plan"] == "pro":
        conn.execute(
            "UPDATE users SET runs_today = runs_today + 1, last_run_date = ? WHERE id = ?",
            (today, user_id)
        )
        conn.commit()
        conn.close()
        return True, "Pro user — unlimited access"

    # Free users are limited to 3 runs per day
    FREE_LIMIT = 3
    if runs_today >= FREE_LIMIT:
        conn.close()
        return False, f"You have used all {FREE_LIMIT} free runs for today. Upgrade to Pro for unlimited access."

    # User is within limit — increment the count and allow
    conn.execute(
        "UPDATE users SET runs_today = runs_today + 1, last_run_date = ? WHERE id = ?",
        (today, user_id)
    )
    conn.commit()
    conn.close()
    return True, "Run allowed"


def upgrade_to_pro(user_id):
    # ============================================================
    # THE STORY:
    # A free customer decides to become a premium customer.
    # Raza opens the register and changes their plan from
    # free to pro. From now on they get unlimited chai.
    #
    # THE TECH:
    # Updates the plan column for this user from 'free' to 'pro'.
    # This is called after a successful Stripe payment.
    # ============================================================
    conn = get_db()
    conn.execute(
        "UPDATE users SET plan = 'pro' WHERE id = ?", (user_id,)
    )
    conn.commit()
    conn.close()


# Initialise the database when this file is imported
# This creates the users table if it does not exist yet
init_db()