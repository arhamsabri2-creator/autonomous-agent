import os
import uuid
import threading
import logging
import json
import redis
import time
import base64
import datetime
import requests
from openai import OpenAI
from flask import Flask, request, render_template, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO, emit, join_room
from dotenv import load_dotenv
from aws_secrets import get_secret
from werkzeug.middleware.proxy_fix import ProxyFix
import stripe
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from database import create_user, get_user_by_email, get_user_by_id, verify_password, check_and_update_usage, upgrade_to_pro, get_db, get_all_users, log_agent_run
from agent import run_agent
from authlib.integrations.flask_client import OAuth

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key-change-this")

app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = '/tmp/flask_sessions'
app.config['SESSION_PERMANENT'] = True
from flask_session import Session
Session(app)
app.config['SESSION_COOKIE_HTTPONLY'] = True

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per minute"],
    storage_uri="memory://"
)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = redis.from_url(REDIS_URL)
local_redis = redis.from_url("redis://localhost:6379")

# socketio disabled



login_manager = LoginManager()

def role_required(*roles):
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("login"))
            user = get_user_by_id(current_user.id)
            if not user:
                return redirect(url_for("login"))
            user_plan = user[4] if isinstance(user, tuple) else user.get("plan", "free")
            if "admin" in roles and user_plan != "admin":
                flash("Admin access required", "error")
                return redirect(url_for("index"))
            if user_plan not in roles:
                flash("Access denied - upgrade your plan", "error")
                return redirect(url_for("index"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
login_manager.init_app(app)
login_manager.login_view = "login"

vision_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


class User(UserMixin):
    def __init__(self, user_row):
        self.id = user_row[0]
        self.name = user_row[1]
        self.email = user_row[2]
        self.plan = user_row[4]
        self.runs_today = user_row[5]
        self.referral_code = user_row[7] if len(user_row) > 7 else None
        self.referrals_count = user_row[8] if len(user_row) > 8 else 0

@login_manager.user_loader
def load_user(user_id):
    user_row = get_user_by_id(int(user_id))
    if user_row:
        logger.info(f"User loaded: id={user_id}")
        return User(user_row)
    logger.warning(f"User not found in DB: id={user_id}")
    return None


def send_telegram_approval(action_type, action_details, pending_id):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False
    try:
        message = f"Agent wants to take an action — your approval is needed:\n\nAction: {action_type}\nDetails: {action_details}\n\nPending ID: {pending_id}"
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "reply_markup": {
                "inline_keyboard": [[
                    {"text": "Approve", "callback_data": f"approve|{pending_id}|{action_type}"},
                    {"text": "Reject", "callback_data": f"reject|{pending_id}|{action_type}"}
                ]]
            }
        }
        response = requests.post(url, json=payload, timeout=10)
        logger.info(f"Telegram approval sent: pending_id={pending_id} action={action_type}")
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Telegram approval send error: {e}")
        return False


def answer_telegram_callback(callback_query_id):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        return
    try:
        url = f"https://api.telegram.org/bot{token}/answerCallbackQuery"
        requests.post(url, json={"callback_query_id": callback_query_id}, timeout=5)
    except Exception as e:
        logger.error(f"Telegram callback answer error: {e}")


def execute_pending_action(action_type, action_details):
    try:
        if action_type == "job_apply":
            from tools import TOOLS
            if "apply" in TOOLS:
                result = TOOLS["apply"](action_details)
                logger.info(f"Job applied after approval: {action_details} result={result}")
        elif action_type == "calendar_event":
            from tools import TOOLS
            if "create_event" in TOOLS:
                result = TOOLS["create_event"](action_details)
                logger.info(f"Calendar event created after approval: {action_details}")
        elif action_type == "memory_save":
            from memory import save_to_memory
            save_to_memory(action_details, action_details, topic="general")
            logger.info(f"Memory saved after approval: {action_details[:100]}")
        else:
            logger.warning(f"Unknown action_type in execute_pending_action: {action_type}")
    except Exception as e:
        logger.error(f"execute_pending_action error: action_type={action_type} error={e}")


def process_job(job_id, goal, user_id=None):
    try:
        logger.info(f"Processing job: {job_id}")
        for update in run_agent(goal, user_id=user_id):
            if isinstance(update, str):
                current_data = json.loads(redis_client.get(job_id))
                current_data["lines"].append(update)
                redis_client.setex(job_id, 3600, json.dumps(current_data))

        final_data = json.loads(redis_client.get(job_id))
        final_data["status"] = "done"
        redis_client.setex(job_id, 3600, json.dumps(final_data))
        logger.info(f"Job completed: {job_id}")
    except Exception as e:
        logger.error(f"Job error: {job_id} error={str(e)}")
        try:
            error_data = json.loads(redis_client.get(job_id))
            error_data["lines"].append(f"ERROR: {str(e)}")
            error_data["status"] = "done"
            redis_client.setex(job_id, 3600, json.dumps(error_data))
        except:
            pass

def queue_worker():
    logger.info("Queue worker started")
    while True:
        try:
            item = local_redis.blpop("job_queue", timeout=30)
            if item:
                _, data = item
                job = json.loads(data)
                process_job(job["job_id"], job["goal"], user_id=job.get("user_id"))
        except Exception as e:
            logger.debug(f"Queue worker idle: {e}")
            time.sleep(1)

worker_thread = threading.Thread(target=queue_worker)
worker_thread.daemon = True
worker_thread.start()


def clean_lines(text):
    skip_prefixes = (
        "---", "===", "Thought:", "Action:", "Action Input:",
        "OBSERVATION:", "[Context", "[Self-reflection", "[Coordinator",
        "Saving", "News goal", "ALL AGENTS", "Total run",
        "Tokens used", "Estimated cost", "Job queued",
        "ARHAM'S", "Your personal AI", "GOAL:", "[Coordinator:",
        "Checking memory", "Research Agent", "News/current",
        "FOUND RELEVANT", "RELEVANT MEMORIES", "Memory 1:", "Memory 2:", "Memory 3:",
        "Goal:", "Findings:", "--- Research", "--- Job", "--- Calendar",
        ">>> ", "Rewritten", "Detected topic", "Short goal",
        "Search failed", "RESEARCH AGENT ERROR", "Final Output:",
        "pile the", "Arranging", "succinct", "compile",
    )
    lines = text.split("\n")
    clean = []
    for line in lines:
        stripped = line.strip()
        if any(stripped.startswith(p) for p in skip_prefixes):
            continue
        if stripped == "None":
            continue
        if stripped:
            clean.append(stripped)
    return "\n".join(clean).strip()


def extract_clean_answer(result):
    raw = None
    if "RESEARCH RESULT:" in result:
        raw = result.split("RESEARCH RESULT:")[-1]
        for sep in ["=" * 10, "---"]:
            if sep in raw:
                raw = raw.split(sep)[0]
                break
    elif "ANSWER:" in result:
        raw = result.split("ANSWER:")[-1]
        for sep in ["=" * 10, "---"]:
            if sep in raw:
                raw = raw.split(sep)[0]
                break
    elif "FINAL ANSWER:" in result:
        raw = result.split("FINAL ANSWER:")[-1]
        for sep in ["=" * 10, "---"]:
            if sep in raw:
                raw = raw.split(sep)[0]
                break
    if raw:
        cleaned = clean_lines(raw)
        if cleaned and len(cleaned) > 50:
            return cleaned
    cleaned = clean_lines(result)
    if cleaned and len(cleaned) > 50:
        return cleaned[-2000:] if len(cleaned) > 2000 else cleaned
    return None


def run_daily_digest():
    logger.info("Daily digest starting...")
    try:
        users = get_all_users()
        pro_users = [u for u in users if u[4] in ('pro', 'admin')]
        logger.info(f"Daily digest: found {len(pro_users)} pro users out of {len(users)} total")

        for user in pro_users:
            user_id = user[0]
            user_name = user[1]
            user_email = user[2]

            try:
                user_interests = user[9] if len(user) > 9 and user[9] else "AI, technology, world news"
                digest_goal = f"latest news and developments today about: {user_interests}"
                result_lines = []
                for update in run_agent(digest_goal):
                    if isinstance(update, str):
                        result_lines.append(update)

                result = "".join(result_lines)
                final_result = extract_clean_answer(result)

                if not final_result or len(final_result) < 50:
                    final_result = "Today's AI briefing could not be generated. Please log in to run your own research."

                try:
                    from gmail_tool import send_email
                    subject = f"Your Daily AI Briefing — {time.strftime('%B %d, %Y')}"
                    body = f"""Hi {user_name},

Here is your daily AI briefing:

{final_result}

---
This briefing was generated automatically by your AI agent.
Log in to run your own goals: https://arhamsabri-autonomous-agent.hf.space

Arham's Autonomous Agent
"""
                    send_email(user_email, subject, body)
                    logger.info(f"Daily digest sent to: {user_email}")
                except Exception as email_error:
                    logger.error(f"Daily digest email failed for {user_email}: {email_error}")

            except Exception as user_error:
                logger.error(f"Daily digest failed for user {user_id}: {user_error}")
                continue

    except Exception as e:
        logger.error(f"Daily digest error: {e}")
    logger.info("Daily digest completed")


scheduler = BackgroundScheduler()
scheduler.add_job(
    func=run_daily_digest,
    trigger=CronTrigger(hour=12, minute=30),
    id="daily_digest",
    name="Daily AI Digest",
    replace_existing=True
)
scheduler.start()
logger.info("APScheduler started — daily digest scheduled at 6pm IST")


@app.route("/")
def landing():
    return render_template("landing.html")

@app.route("/dashboard")
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
        referred_by = request.form.get("ref", None) or request.args.get("ref", None)
        success, message = create_user(name, email, password, referred_by=referred_by)
        if success:
            user_row = get_user_by_email(email)
            user = User(user_row)
            login_user(user, remember=True)
            logger.info(f"New user signed up: id={user.id}")
            try:
                from gmail_tool import send_email
                welcome_subject = "Welcome to Arham's Autonomous Agent"
                welcome_body = f"""Hi {name},

Welcome to Arham's Autonomous Agent — your personal AI assistant that gets things done automatically.

Here are 3 goals to try right now:

1. Research the latest developments in artificial intelligence
2. Find me python internships on Internshala
3. What are today's top business news stories

Just paste any of these into the goal box and hit RUN.

Your account is on the FREE plan — you get 3 runs per day.

Welcome aboard,
Arham's Autonomous Agent
"""
                send_email(email, welcome_subject, welcome_body)
                logger.info(f"Welcome email sent to: {email}")
            except Exception as e:
                logger.error(f"Welcome email failed: {e}")
            return redirect(url_for("index"))
        else:
            flash(message, "error")
            return render_template("signup.html")
    return render_template("signup.html")

@app.route("/auth/google")
def google_login():
    redirect_uri = url_for("google_callback", _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route("/auth/google/callback")
def google_callback():
    try:
        token = google.authorize_access_token()
        user_info = token.get("userinfo")
        if not user_info:
            flash("Google login failed", "error")
            return redirect(url_for("login"))
        email = user_info["email"]
        name = user_info.get("name", email.split("@")[0])
        user = get_user_by_email(email)
        if not user:
            create_user(name, email, uuid.uuid4().hex)
            user = get_user_by_email(email)
        if not user:
            flash("Google login failed - could not create account", "error")
            return redirect(url_for("login"))
        login_user(User(user))
        logger.info(f"Google login: {email}")
        return redirect(url_for("index"))
    except Exception as e:
        logger.error(f"Google callback error: {e}")
        flash("Google login failed", "error")
        return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        success, user_row = verify_password(email, password)
        if success:
            user = User(user_row)
            login_user(user, remember=True)
            logger.info(f"User logged in: id={user.id}")
            return redirect(url_for("index"))
        else:
            logger.warning(f"Failed login attempt for email: {email}")
            flash("Invalid email or password", "error")
            return render_template("login.html")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logger.info(f"User logged out: id={current_user.id}")
    logout_user()
    return redirect(url_for("login"))

@app.route("/run", methods=["POST"])
@login_required
@limiter.limit("10 per minute")
def run():
    goal = request.form.get("goal", "")
    if not goal:
        return jsonify({"error": "No goal provided"}), 400

    allowed, message = check_and_update_usage(current_user.id)
    if not allowed:
        return jsonify({"error": message}), 200

    job_id = str(uuid.uuid4())
    job_data = {"status": "queued", "lines": ["Job queued — waiting for worker...\n"]}
    redis_client.setex(job_id, 3600, json.dumps(job_data))
    local_redis.rpush("job_queue", json.dumps({"job_id": job_id, "goal": goal, "user_id": current_user.id}))
    logger.info(f"Job queued: user_id={current_user.id} job_id={job_id}")

    return jsonify({"job_id": job_id})

@app.route("/poll/<job_id>")
@login_required
def poll(job_id):
    raw = redis_client.get(job_id)
    if not raw:
        return jsonify({"lines": [], "status": "not_found", "cursor": 0})
    job = json.loads(raw)
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
        logger.error(f"Stripe checkout error: {str(e)}")
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
        logger.error(f"Webhook signature error: {str(e)}")
        return jsonify({"error": str(e)}), 400
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.client_reference_id
        if user_id:
            try:
                upgrade_to_pro(int(user_id))
                logger.info(f"User upgraded to pro: user_id={user_id}")
            except (KeyError, TypeError):
                user_id = None
    return jsonify({"status": "success"}), 200

@app.route("/admin")
@login_required
@role_required("admin")
def admin():
    from database import get_all_users
    users = get_all_users()
    total_users = len(users)
    pro_users = sum(1 for u in users if u[4] == 'pro')
    free_users = total_users - pro_users
    total_runs_today = sum(u[4] for u in users)

    # Fetch recent agent runs
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, goal, agents_used, run_time_seconds,
                   input_tokens, output_tokens, cost_inr, status, error_message, created_at
            FROM agent_runs
            ORDER BY created_at DESC
            LIMIT 50
        """)
        recent_runs = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"Admin runs fetch error: {e}")
        recent_runs = []

    # Calculate summary stats
    total_runs_logged = len(recent_runs)
    success_runs = [r for r in recent_runs if r[8] == "success"]
    success_rate = round((len(success_runs) / total_runs_logged * 100) if total_runs_logged > 0 else 0)
    avg_run_time = round(sum(r[4] for r in recent_runs if r[4]) / total_runs_logged, 1) if total_runs_logged > 0 else 0
    total_cost_inr = round(sum(r[7] for r in recent_runs if r[7]), 2)

    return render_template("admin.html",
        users=users,
        total_users=total_users,
        pro_users=pro_users,
        free_users=free_users,
        total_runs_today=total_runs_today,
        recent_runs=recent_runs,
        total_runs_logged=total_runs_logged,
        success_rate=success_rate,
        avg_run_time=avg_run_time,
        total_cost_inr=total_cost_inr
    )

@app.route("/feedback", methods=["POST"])
@login_required
def feedback():
    try:
        rating = request.form.get("rating")
        goal = request.form.get("goal")
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO feedback (user_id, goal, rating) VALUES (%s, %s, %s)",
            (current_user.id, goal, rating)
        )
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"Feedback saved: user_id={current_user.id} rating={rating}")
        return jsonify({"status": "saved"})
    except Exception as e:
        logger.error(f"Feedback error: {e}")
        return jsonify({"status": "error"}), 500

@app.route("/approve/<job_id>", methods=["POST"])
@login_required
def approve_job(job_id):
    try:
        redis_client.setex(f"pending_job:{job_id}", 300, "approved")
        logger.info(f"Job approved: job_id={job_id} user_id={current_user.id}")
        return jsonify({"status": "approved"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/reject/<job_id>", methods=["POST"])
@login_required
def reject_job(job_id):
    try:
        redis_client.setex(f"pending_job:{job_id}", 300, "rejected")
        logger.info(f"Job rejected: job_id={job_id} user_id={current_user.id}")
        return jsonify({"status": "rejected"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "no data"}), 200
        callback_query = data.get("callback_query")
        if not callback_query:
            return jsonify({"status": "not a callback"}), 200
        callback_query_id = callback_query.get("id")
        callback_data = callback_query.get("data", "")
        parts = callback_data.split("|")
        if len(parts) != 3:
            answer_telegram_callback(callback_query_id)
            return jsonify({"status": "invalid callback data"}), 200
        decision = parts[0]
        pending_id = parts[1]
        action_type = parts[2]
        answer_telegram_callback(callback_query_id)
        if decision == "approve":
            raw = redis_client.get(f"pending_action:{pending_id}")
            if raw:
                action_details = raw.decode("utf-8")
                logger.info(f"Telegram approved: pending_id={pending_id} action={action_type}")
                threading.Thread(
                    target=execute_pending_action,
                    args=(action_type, action_details)
                ).start()
                redis_client.setex(f"pending_job:{pending_id}", 300, "approved")
            else:
                logger.warning(f"Pending action not found in Redis: pending_id={pending_id}")
        elif decision == "reject":
            logger.info(f"Telegram rejected: pending_id={pending_id} action={action_type}")
            redis_client.setex(f"pending_job:{pending_id}", 300, "rejected")
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error(f"Telegram webhook error: {e}")
        return jsonify({"status": "error"}), 200


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    from database import get_db
    user = get_user_by_id(current_user.id)
    if request.method == "POST":
        interests = request.form.get("interests", "AI, technology, world news").strip()
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET interests = %s WHERE id = %s", (interests, current_user.id))
            conn.commit()
            cursor.close()
            conn.close()
            flash("Interests updated successfully", "success")
            redis_client.delete(f"user:{current_user.id}")
        except Exception as e:
            flash(f"Error updating interests: {str(e)}", "error")
        return redirect(url_for("settings"))
    current_interests = user[9].strip() if user and len(user) > 9 and user[9] else "AI, technology, world news"
    return render_template("settings.html", interests=current_interests, user=user)

@app.route("/summarize-meeting", methods=["GET", "POST"])
@login_required
def summarize_meeting():
    if request.method == "GET":
        return render_template("meeting.html", user=get_user_by_id(current_user.id))
    try:
        audio_file = request.files.get("audio")
        if not audio_file:
            return jsonify({"error": "No audio file provided"}), 400
        audio_bytes = audio_file.read()
        file_ext = audio_file.filename.split(".")[-1].lower() if audio_file.filename else "mp3"
        mime_type = f"audio/{file_ext}"
        transcript = vision_client.audio.transcriptions.create(
            model="whisper-1",
            file=(audio_file.filename or "meeting.mp3", audio_bytes, mime_type),
        )
        transcript_text = transcript.text
        summary_response = vision_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a meeting summarizer. Extract key points, decisions, action items and next steps from meeting transcripts. Format clearly with sections."},
                {"role": "user", "content": "Summarize this meeting transcript:\n\n" + transcript_text},
            ],
            max_tokens=1000
        )
        summary = summary_response.choices[0].message.content
        return jsonify({"transcript": transcript_text, "summary": summary})
    except Exception as e:
        logger.error(f"Meeting summarizer error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/guide")
@login_required
def guide():
    return render_template("docs.html", user=get_user_by_id(current_user.id))

@app.route("/trigger-digest")
def trigger_digest():
    admin_password = os.getenv("ADMIN_PASSWORD", "arham123")
    provided = request.args.get("password", "")
    if provided != admin_password:
        return "Unauthorized", 401
    threading.Thread(target=run_daily_digest).start()
    return "Daily digest triggered — check logs and emails shortly.", 200

@app.route("/run-vision", methods=["POST"])
@login_required
@limiter.limit("10 per minute")
def run_vision():
    try:
        question = request.form.get("question", "What is in this image?")
        image_file = request.files.get("image")
        if not image_file:
            return jsonify({"error": "No image provided"}), 400
        image_data = base64.b64encode(image_file.read()).decode("utf-8")
        mime_type = image_file.content_type or "image/jpeg"
        response = vision_client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_data}"}}
                ]
            }],
            max_tokens=500
        )
        answer = response.choices[0].message.content
        logger.info(f"Vision run completed: user_id={current_user.id}")
        return jsonify({"answer": answer})
    except Exception as e:
        logger.error(f"Vision run error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/transcribe", methods=["POST"])
@login_required
def transcribe():
    try:
        audio_file = request.files.get("audio")
        if not audio_file:
            return jsonify({"error": "No audio provided"}), 400
        audio_bytes = audio_file.read()
        transcript = vision_client.audio.transcriptions.create(
            model="whisper-1",
            file=("audio.webm", audio_bytes, "audio/webm"),
        )
        logger.info(f"Transcription completed: user_id={current_user.id}")
        return jsonify({"text": transcript.text})
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/ping")
def ping():
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860)
