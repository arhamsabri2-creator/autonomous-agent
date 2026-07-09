import os
import uuid
import threading
import stripe
from flask import Flask, request, render_template, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from dotenv import load_dotenv
from database import create_user, get_user_by_email, get_user_by_id, verify_password, check_and_update_usage, upgrade_to_pro
from agent import run_agent

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key-change-this")

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

jobs = {}

class User(UserMixin):
    def __init__(self, user_row):
        self.id = user_row["id"]
        self.name = user_row["name"]
        self.email = user_row["email"]
        self.plan = user_row["plan"]
        self.runs_today = user_row["runs_today"]

@login_manager.user_loader
def load_user(user_id):
    user_row = get_user_by_id(int(user_id))
    if user_row:
        return User(user_row)
    return None

@app.route("/")
@login_required
def index():
    return render_template("index.html", user=current_user)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        if not name or not email or not password:
            flash("Please fill in all fields", "error")
            return render_template("signup.html")
        success, message = create_user(name, email, password)
        if success:
            user_row = get_user_by_email(email)
            user = User(user_row)
            login_user(user)
            return redirect(url_for("index"))
        else:
            flash(message, "error")
            return render_template("signup.html")
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        success, user_row = verify_password(email, password)
        if success:
            user = User(user_row)
            login_user(user)
            return redirect(url_for("index"))
        else:
            flash("Invalid email or password", "error")
            return render_template("login.html")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/run", methods=["POST"])
@login_required
def run():
    goal = request.form.get("goal", "")
    if not goal:
        return jsonify({"error": "No goal provided"}), 400

    allowed, message = check_and_update_usage(current_user.id)
    if not allowed:
        return jsonify({"error": message}), 403

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "running", "lines": []}

    def run_in_background():
        try:
            print(f"Thread started for: {goal}")
            for update in run_agent(goal):
                jobs[job_id]["lines"].append(update)
            jobs[job_id]["status"] = "done"
            print("Thread finished")
        except Exception as e:
            print(f"Thread error: {e}")
            jobs[job_id]["lines"].append(f"Error: {str(e)}")
            jobs[job_id]["status"] = "done"

    t = threading.Thread(target=run_in_background)
    t.daemon = True
    t.start()
    print(f"Job started: {job_id}")

    return jsonify({"job_id": job_id})

@app.route("/poll/<job_id>")
@login_required
def poll(job_id):
    if job_id not in jobs:
        return jsonify({"lines": [], "status": "not_found"})

    job = jobs[job_id]
    cursor = int(request.args.get("cursor", 0))
    new_lines = job["lines"][cursor:]

    return jsonify({
        "lines": new_lines,
        "status": job["status"],
        "cursor": cursor + len(new_lines)
    })

@app.route("/upgrade")
@login_required
def upgrade():
    checkout_session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price": STRIPE_PRICE_ID,
            "quantity": 1,
        }],
        mode="subscription",
        success_url=url_for("payment_success", _external=True),
        cancel_url=url_for("index", _external=True),
        client_reference_id=str(current_user.id),
    )
    return redirect(checkout_session.url, code=303)

@app.route("/payment-success")
@login_required
def payment_success():
    flash("Payment received! Your account is being upgraded.", "success")
    return redirect(url_for("index"))

@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        return "Invalid signature", 400

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        try:
            user_id = session["client_reference_id"]
        except (KeyError, TypeError):
            user_id = None
        if user_id:
            upgrade_to_pro(int(user_id))
            print(f"User {user_id} upgraded to Pro via webhook")

    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860, threaded=True)
