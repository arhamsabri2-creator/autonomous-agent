import os
import uuid
import threading
from flask import Flask, request, Response, render_template, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix
import stripe
from database import create_user, get_user_by_email, get_user_by_id, verify_password, check_and_update_usage, upgrade_to_pro
from agent import run_agent

load_dotenv()

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key-change-this")
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

jobs = {}

class User(UserMixin):
    def __init__(self, user_row):
        self.id = user_row[0]
        self.name = user_row[1]
        self.email = user_row[2]
        self.plan = user_row[4]
        self.runs_today = user_row[5]

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
        return jsonify({"error": message}), 200

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "running", "lines": []}

    def agent_thread():
        try:
            for update in run_agent(goal):
                jobs[job_id]["lines"].append(update)
            jobs[job_id]["status"] = "done"
        except Exception as e:
            jobs[job_id]["lines"].append(f"ERROR: {str(e)}")
            jobs[job_id]["status"] = "done"

    thread = threading.Thread(target=agent_thread)
    thread.daemon = True
    thread.start()

    return jsonify({"job_id": job_id})

@app.route("/poll/<job_id>")
@login_required
def poll(job_id):
    if job_id not in jobs:
        return jsonify({"lines": [], "status": "not_found", "cursor": 0})
    cursor = int(request.args.get("cursor", 0))
    job = jobs[job_id]
    new_lines = job["lines"][cursor:]
    return jsonify({
        "lines": new_lines,
        "status": job["status"],
        "cursor": cursor + len(new_lines)
    })

@app.route("/upgrade")
@login_required
def upgrade():
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            mode="subscription",
            success_url=url_for("payment_success", _external=True),
            cancel_url=url_for("index", _external=True),
            client_reference_id=str(current_user.id),
        )
        return redirect(checkout_session.url)
    except Exception as e:
        flash(f"Payment error: {str(e)}", "error")
        return redirect(url_for("index"))

@app.route("/payment-success")
@login_required
def payment_success():
    flash("Payment successful! Your account will be upgraded shortly.", "success")
    return redirect(url_for("index"))

@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.client_reference_id
        if user_id:
            try:
                upgrade_to_pro(int(user_id))
            except (KeyError, TypeError):
                user_id = None
    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860)