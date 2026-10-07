"""
app.py - Smart Reminder and Personal Protection System (Flask backend)

Sections:
  1. App setup & security helpers (sessions, CSRF, decorators)
  2. Validation helpers
  3. Auth routes
  4. Reminders (+ notifications API)
  5. Emergency contacts
  6. SOS + dispatch
  7. Location sharing
  8. History
  9. Admin
"""
import calendar
import math
import os
import re
import secrets
import sqlite3
from datetime import datetime, timedelta
from functools import wraps

from flask import (Flask, abort, flash, g, jsonify, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

import db
from db import DT_MIN, DT_SEC, now_str

# ===========================================================================
# 1. APP SETUP & SECURITY HELPERS
# ===========================================================================
app = Flask(__name__)


def load_secret_key():
    """Use SECRET_KEY from the environment, otherwise create one and keep it
    in instance/secret.key so sessions survive restarts."""
    env_key = os.environ.get("SECRET_KEY")
    if env_key:
        return env_key
    path = os.path.join(db.BASE_DIR, "instance", "secret.key")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(secrets.token_hex(32))
    with open(path) as f:
        return f.read().strip()


app.config.update(
    SECRET_KEY=load_secret_key(),
    SESSION_COOKIE_HTTPONLY=True,        # JavaScript cannot read the session cookie
    SESSION_COOKIE_SAMESITE="Lax",       # basic CSRF protection for cross-site requests
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
)
app.teardown_appcontext(db.close_db)

# Constants -----------------------------------------------------------------
REMINDER_TYPES = ("task", "event", "recurring")
RECURRENCE_RULES = ("daily", "weekly", "monthly")
HISTORY_TYPES = ("reminder", "notification", "contact", "sos", "location")
SNOOZE_CHOICES = (5, 10, 15, 30, 60, 120, 1440)
SOS_COUNTDOWN_SECONDS = 5  # used by the JS countdown (shown on the page)


def csrf_token():
    """Per-session CSRF token, embedded in every form / sent with every fetch()."""
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def load_user_and_check_csrf():
    """Runs before every request: load the logged-in user and verify CSRF on POST."""
    if request.endpoint == "static":
        return
    g.user = None
    user_id = session.get("user_id")
    if user_id:
        user = db.query_one(
            "SELECT user_id, full_name, email, phone, is_active FROM users WHERE user_id = ?",
            (user_id,),
        )
        # Deactivated users are logged out immediately.
        if user is None or not user["is_active"]:
            session.pop("user_id", None)
        else:
            g.user = user

    if request.method == "POST":
        sent = request.form.get("_csrf") or request.headers.get("X-CSRF-Token") or ""
        if not secrets.compare_digest(sent, session.get("_csrf", "")):
            if request.path.startswith("/api/"):
                return jsonify(ok=False, error="Invalid security token. Refresh the page."), 400
            return "Invalid or missing security token. Go back, refresh the page and try again.", 400


def login_required(view):
    """Redirect anonymous visitors to /login (JSON 401 for API calls)."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            if request.path.startswith("/api/"):
                return jsonify(ok=False, error="Authentication required."), 401
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    """Protect admin pages. Admin sessions are separate from user sessions."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        admin_id = session.get("admin_id")
        admin = db.query_one("SELECT admin_id, username FROM admins WHERE admin_id = ?",
                             (admin_id,)) if admin_id else None
        if admin is None:
            flash("Admin login required.", "error")
            return redirect(url_for("admin_login"))
        g.admin = admin
        return view(*args, **kwargs)
    return wrapped


# Template filters ------------------------------------------------------------
@app.template_filter("pretty_dt")
def pretty_dt(value):
    """'2026-10-07 14:30' -> 'Wed 07 Oct, 02:30 PM'."""
    if not value:
        return ""
    for fmt in (DT_MIN, DT_SEC):
        try:
            return datetime.strptime(value, fmt).strftime("%a %d %b, %I:%M %p")
        except ValueError:
            continue
    return value


@app.template_filter("snooze_label")
def snooze_label(minutes):
    """5 -> '5 min', 60 -> '1 hour', 120 -> '2 hours', 1440 -> '1 day'."""
    if minutes < 60:
        return f"{minutes} min"
    if minutes == 1440:
        return "1 day"
    hours = minutes // 60
    return f"{hours} hour" + ("s" if hours > 1 else "")


@app.template_filter("dt_input")
def dt_input(value):
    """'2026-10-07 14:30' -> '2026-10-07T14:30' (value for <input type=datetime-local>)."""
    return value.replace(" ", "T")[:16] if value else ""


# ===========================================================================
# 2. VALIDATION HELPERS
# ===========================================================================
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def valid_email(email):
    return bool(email) and len(email) <= 254 and EMAIL_RE.match(email) is not None


def normalize_phone(raw):
    """Return the phone as '+digits' / 'digits' if it has 7-15 digits, else None.
    Spaces, dashes, dots and parentheses are allowed in the input."""
    raw = (raw or "").strip()
    if not re.fullmatch(r"\+?[0-9\s\-().]+", raw):
        return None
    digits = re.sub(r"\D", "", raw)
    if not 7 <= len(digits) <= 15:
        return None
    return ("+" if raw.startswith("+") else "") + digits


def parse_due(raw):
    """Parse a datetime-local value ('2026-10-07T14:30') into our DT_MIN text."""
    try:
        return datetime.strptime((raw or "").replace("T", " ")[:16], DT_MIN).strftime(DT_MIN)
    except ValueError:
        return None


def parse_coords(data):
    """Validate latitude/longitude(/accuracy) from a JSON body.
    Returns (lat, lng, accuracy) or None if invalid / missing."""
    try:
        lat = float(data.get("latitude"))
        lng = float(data.get("longitude"))
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(lat) and math.isfinite(lng)):
        return None
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return None
    try:
        acc = float(data.get("accuracy"))
        acc = acc if math.isfinite(acc) and acc >= 0 else None
    except (TypeError, ValueError):
        acc = None
    return lat, lng, acc


def maps_link(lat, lng):
    return f"https://www.google.com/maps?q={lat:.6f},{lng:.6f}"


# ===========================================================================
# 3. AUTH ROUTES
# ===========================================================================
@app.route("/")
def index():
    return redirect(url_for("dashboard" if g.user else "login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for("dashboard"))
    form = {}
    if request.method == "POST":
        form = request.form
        full_name = form.get("full_name", "").strip()
        email = form.get("email", "").strip().lower()
        phone_raw = form.get("phone", "").strip()
        password = form.get("password", "")
        confirm = form.get("confirm_password", "")

        errors = []
        if not 2 <= len(full_name) <= 100:
            errors.append("Full name must be 2-100 characters.")
        if not valid_email(email):
            errors.append("Please enter a valid email address.")
        phone = None
        if phone_raw:
            phone = normalize_phone(phone_raw)
            if phone is None:
                errors.append("Phone number must contain 7-15 digits.")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")

        if not errors:
            try:
                db.execute(
                    "INSERT INTO users (full_name, email, password_hash, phone, is_active, created_at) "
                    "VALUES (?, ?, ?, ?, 1, ?)",
                    (full_name, email, generate_password_hash(password), phone, now_str()),
                )
                flash("Account created! You can now log in.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                errors.append("An account with this email already exists.")
        for e in errors:
            flash(e, "error")
    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = db.query_one("SELECT user_id, password_hash, is_active FROM users WHERE email = ?",
                            (email,))
        # One generic message for every failure (wrong email, wrong password, disabled account).
        if user and user["is_active"] and check_password_hash(user["password_hash"], password):
            session.clear()                     # prevents session fixation
            session["user_id"] = user["user_id"]
            session.permanent = True
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# ===========================================================================
# 4. REMINDERS + NOTIFICATIONS
# ===========================================================================
def add_months(dt, months):
    """Add calendar months, clamping the day (Jan 31 + 1 month -> Feb 28)."""
    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def next_occurrence(due, rule, now=None):
    """Next due datetime for a recurring reminder (first one that is in the future)."""
    now = now or datetime.now()
    while True:
        if rule == "daily":
            due += timedelta(days=1)
        elif rule == "weekly":
            due += timedelta(weeks=1)
        elif rule == "monthly":
            due = add_months(due, 1)
        else:
            return due
        if due > now:
            return due


def validate_reminder(form):
    """Validate the reminder form. Returns (clean_data, errors)."""
    title = form.get("title", "").strip()
    description = form.get("description", "").strip()
    rtype = form.get("reminder_type", "task")
    due_at = parse_due(form.get("due_at"))
    rule = form.get("recurrence_rule", "").strip() or None
    errors = []

    if not 1 <= len(title) <= 120:
        errors.append("Title is required (max 120 characters).")
    if len(description) > 1000:
        errors.append("Description is too long (max 1000 characters).")
    if rtype not in REMINDER_TYPES:
        errors.append("Invalid reminder type.")
    if due_at is None:
        errors.append("Please choose a valid due date and time.")
    if rtype == "recurring":
        if rule not in RECURRENCE_RULES:
            errors.append("Choose daily, weekly or monthly for a recurring reminder.")
    else:
        rule = None  # only 'recurring' reminders have a rule
    try:
        notify = int(form.get("notify_before_min", 0))
        if not 0 <= notify <= 10080:
            raise ValueError
    except (TypeError, ValueError):
        errors.append("'Notify before' must be between 0 and 10080 minutes.")
        notify = 0

    data = dict(title=title, description=description, reminder_type=rtype,
                due_at=due_at, recurrence_rule=rule, notify_before_min=notify)
    return data, errors


def get_own_reminder(reminder_id):
    """Fetch a reminder ONLY if it belongs to the logged-in user (else 404)."""
    row = db.query_one("SELECT * FROM reminders WHERE reminder_id = ? AND user_id = ?",
                       (reminder_id, g.user["user_id"]))
    if row is None:
        abort(404)
    return row


def decorate(rows):
    """Convert rows to dicts and flag overdue ones."""
    now_min = datetime.now().strftime(DT_MIN)
    return [dict(r, overdue=(r["status"] in ("pending", "snoozed") and r["due_at"] < now_min))
            for r in rows]


def render_reminders(flt="today", form=None, editing=None):
    """Shared renderer for the reminders page (also used to redisplay a failed form)."""
    uid = g.user["user_id"]
    end_of_today = datetime.now().strftime("%Y-%m-%d") + " 23:59"
    base = "SELECT * FROM reminders WHERE user_id = ? "
    if flt == "upcoming":
        rows = db.query_all(base + "AND status IN ('pending','snoozed') AND due_at > ? "
                            "ORDER BY due_at", (uid, end_of_today))
    elif flt == "completed":
        rows = db.query_all(base + "AND status = 'completed' ORDER BY due_at DESC", (uid,))
    elif flt == "all":
        rows = db.query_all(base + "ORDER BY due_at DESC", (uid,))
    else:  # today: due today or overdue, still active
        flt = "today"
        rows = db.query_all(base + "AND status IN ('pending','snoozed') AND due_at <= ? "
                            "ORDER BY due_at", (uid, end_of_today))
    return render_template("reminders.html", reminders=decorate(rows), flt=flt,
                           form=form or (dict(editing) if editing else {}),
                           editing=editing, snooze_choices=SNOOZE_CHOICES)


@app.route("/dashboard")
@login_required
def dashboard():
    uid = g.user["user_id"]
    now = datetime.now()
    end_of_today = now.strftime("%Y-%m-%d") + " 23:59"
    today = db.query_all(
        "SELECT * FROM reminders WHERE user_id = ? AND status IN ('pending','snoozed') "
        "AND due_at <= ? ORDER BY due_at LIMIT 8", (uid, end_of_today))
    upcoming = db.query_all(
        "SELECT * FROM reminders WHERE user_id = ? AND status IN ('pending','snoozed') "
        "AND due_at > ? ORDER BY due_at LIMIT 5", (uid, end_of_today))
    contacts = db.query_all(
        "SELECT * FROM emergency_contacts WHERE user_id = ? ORDER BY priority, contact_id LIMIT 3",
        (uid,))
    stats = db.query_one(
        "SELECT "
        "(SELECT COUNT(*) FROM reminders WHERE user_id = ?1 AND status IN ('pending','snoozed')) AS active, "
        "(SELECT COUNT(*) FROM reminders WHERE user_id = ?1 AND status = 'completed') AS done, "
        "(SELECT COUNT(*) FROM emergency_contacts WHERE user_id = ?1) AS contacts, "
        "(SELECT COUNT(*) FROM emergency_events WHERE user_id = ?1 AND status != 'cancelled') AS sos",
        (uid,))
    return render_template("dashboard.html", today=decorate(today), upcoming=decorate(upcoming),
                           contacts=contacts, stats=stats, snooze_choices=SNOOZE_CHOICES)


@app.route("/reminders")
@login_required
def reminders_page():
    flt = request.args.get("filter", "today")
    editing = None
    edit_id = request.args.get("edit", type=int)
    if edit_id:
        editing = get_own_reminder(edit_id)
    return render_reminders(flt, editing=editing)


@app.route("/reminders/save", methods=["POST"])
@login_required
def reminder_save():
    """Create a reminder, or update one when a reminder_id is submitted."""
    uid = g.user["user_id"]
    data, errors = validate_reminder(request.form)
    reminder_id = request.form.get("reminder_id", type=int)
    editing = get_own_reminder(reminder_id) if reminder_id else None

    if errors:
        for e in errors:
            flash(e, "error")
        return render_reminders(request.form.get("filter", "today"),
                                form=request.form, editing=editing), 400

    if editing:
        db.execute(
            "UPDATE reminders SET title=?, description=?, reminder_type=?, due_at=?, "
            "recurrence_rule=?, notify_before_min=?, status='pending' "
            "WHERE reminder_id=? AND user_id=?",
            (data["title"], data["description"], data["reminder_type"], data["due_at"],
             data["recurrence_rule"], data["notify_before_min"], reminder_id, uid))
        db.log_history(uid, "reminder", reminder_id, f"Edited reminder '{data['title']}'")
        flash("Reminder updated.", "success")
    else:
        cur = db.execute(
            "INSERT INTO reminders (user_id, title, description, reminder_type, due_at, "
            "recurrence_rule, notify_before_min, status) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')",
            (uid, data["title"], data["description"], data["reminder_type"], data["due_at"],
             data["recurrence_rule"], data["notify_before_min"]))
        db.log_history(uid, "reminder", cur.lastrowid, f"Created reminder '{data['title']}'")
        flash("Reminder created.", "success")
    return redirect(url_for("reminders_page", filter="all"))


@app.route("/reminders/<int:reminder_id>/complete", methods=["POST"])
@login_required
def reminder_complete(reminder_id):
    r = get_own_reminder(reminder_id)
    uid = g.user["user_id"]
    if r["status"] not in ("pending", "snoozed"):
        flash("This reminder is already closed.", "error")
    elif r["recurrence_rule"]:
        # Recurring: don't close it - roll it forward to the next occurrence.
        nxt = next_occurrence(datetime.strptime(r["due_at"], DT_MIN), r["recurrence_rule"])
        db.execute("UPDATE reminders SET due_at=?, status='pending' WHERE reminder_id=? AND user_id=?",
                   (nxt.strftime(DT_MIN), reminder_id, uid))
        db.log_history(uid, "reminder", reminder_id,
                       f"Completed '{r['title']}' - next occurrence {nxt.strftime(DT_MIN)}")
        flash(f"Done! Next occurrence: {pretty_dt(nxt.strftime(DT_MIN))}.", "success")
    else:
        db.execute("UPDATE reminders SET status='completed' WHERE reminder_id=? AND user_id=?",
                   (reminder_id, uid))
        db.log_history(uid, "reminder", reminder_id, f"Completed reminder '{r['title']}'")
        flash("Reminder marked as completed.", "success")
    return redirect(request.referrer or url_for("reminders_page"))


@app.route("/reminders/<int:reminder_id>/snooze", methods=["POST"])
@login_required
def reminder_snooze(reminder_id):
    r = get_own_reminder(reminder_id)
    uid = g.user["user_id"]
    minutes = request.form.get("minutes", type=int)
    if minutes not in SNOOZE_CHOICES:
        flash("Invalid snooze duration.", "error")
    elif r["status"] not in ("pending", "snoozed"):
        flash("Only active reminders can be snoozed.", "error")
    else:
        new_due = (datetime.now() + timedelta(minutes=minutes)).strftime(DT_MIN)
        db.execute("UPDATE reminders SET due_at=?, status='snoozed' WHERE reminder_id=? AND user_id=?",
                   (new_due, reminder_id, uid))
        db.log_history(uid, "reminder", reminder_id,
                       f"Snoozed '{r['title']}' for {minutes} min (now due {new_due})")
        flash(f"Snoozed for {minutes} minutes.", "success")
    return redirect(request.referrer or url_for("reminders_page"))


@app.route("/reminders/<int:reminder_id>/cancel", methods=["POST"])
@login_required
def reminder_cancel(reminder_id):
    r = get_own_reminder(reminder_id)
    uid = g.user["user_id"]
    db.execute("UPDATE reminders SET status='cancelled' WHERE reminder_id=? AND user_id=?",
               (reminder_id, uid))
    db.log_history(uid, "reminder", reminder_id, f"Cancelled reminder '{r['title']}'")
    flash("Reminder cancelled.", "success")
    return redirect(request.referrer or url_for("reminders_page"))


@app.route("/reminders/<int:reminder_id>/delete", methods=["POST"])
@login_required
def reminder_delete(reminder_id):
    r = get_own_reminder(reminder_id)
    uid = g.user["user_id"]
    db.execute("DELETE FROM reminders WHERE reminder_id=? AND user_id=?", (reminder_id, uid))
    db.log_history(uid, "reminder", reminder_id, f"Deleted reminder '{r['title']}'")
    flash("Reminder deleted.", "success")
    return redirect(request.referrer or url_for("reminders_page"))


# --- Notifications API ------------------------------------------------------
@app.route("/api/notifications")
@login_required
def api_notifications():
    """Polled by app.js every 5 s.

    1. Creates a notification row for every active reminder whose due time
       has arrived (alarm for completed reminder time) or whose advance notice has arrived.
    2. Returns the 15 most recent notifications for this user, with `is_due_alarm` flag.
    """
    uid = g.user["user_id"]
    now = datetime.now()
    active = db.query_all(
        "SELECT reminder_id, title, due_at, notify_before_min, status FROM reminders "
        "WHERE user_id = ? AND status IN ('pending', 'snoozed')", (uid,))

    for r in active:
        due = datetime.strptime(r["due_at"], DT_MIN)
        lead = 0 if r["status"] == "snoozed" else r["notify_before_min"]
        due_slot = due.strftime(DT_MIN)

        # 1. DUE ALARM: Reminder time has arrived/completed (now >= due)
        if due <= now <= due + timedelta(hours=24):
            exists_due = db.query_one(
                "SELECT 1 FROM notifications WHERE reminder_id=? AND channel='in_app' "
                "AND scheduled_at=?", (r["reminder_id"], due_slot))
            if not exists_due:
                try:
                    cur = db.execute(
                        "INSERT INTO notifications (reminder_id, channel, scheduled_at, status) "
                        "VALUES (?, 'in_app', ?, 'pending')", (r["reminder_id"], due_slot))
                    db.log_history(uid, "notification", cur.lastrowid,
                                   f"⏰ ALARM: Reminder '{r['title']}' time completed (due {r['due_at']})")
                except sqlite3.IntegrityError:
                    pass

        # 2. Advance notification (if lead > 0 and before due time)
        if lead > 0:
            scheduled = due - timedelta(minutes=lead)
            if scheduled <= now < due:
                advance_slot = scheduled.strftime(DT_MIN)
                exists_adv = db.query_one(
                    "SELECT 1 FROM notifications WHERE reminder_id=? AND channel='in_app' "
                    "AND scheduled_at=?", (r["reminder_id"], advance_slot))
                if not exists_adv:
                    try:
                        cur = db.execute(
                            "INSERT INTO notifications (reminder_id, channel, scheduled_at, status) "
                            "VALUES (?, 'in_app', ?, 'pending')", (r["reminder_id"], advance_slot))
                        db.log_history(uid, "notification", cur.lastrowid,
                                       f"Advance notice for '{r['title']}' ({lead} min before)")
                    except sqlite3.IntegrityError:
                        pass

    rows = db.query_all(
        "SELECT n.notification_id, n.reminder_id, n.scheduled_at, n.sent_at, n.status, "
        "r.title, r.due_at FROM notifications n "
        "JOIN reminders r ON r.reminder_id = n.reminder_id "
        "WHERE r.user_id = ? ORDER BY n.scheduled_at DESC, n.notification_id DESC LIMIT 15",
        (uid,))
    result = []
    for row in rows:
        item = dict(row)
        # Flag if this notification is for the completed/due time
        item["is_due_alarm"] = (item["scheduled_at"] >= item["due_at"])
        result.append(item)
    return jsonify(ok=True, notifications=result)


@app.route("/api/notifications/<int:notification_id>/ack", methods=["POST"])
@login_required
def api_notification_ack(notification_id):
    """Browser confirms it displayed the notification -> mark as sent (once)."""
    cur = db.execute(
        "UPDATE notifications SET status='sent', sent_at=? WHERE notification_id=? "
        "AND status='pending' AND reminder_id IN (SELECT reminder_id FROM reminders WHERE user_id=?)",
        (now_str(), notification_id, g.user["user_id"]))
    return jsonify(ok=True, updated=cur.rowcount)


# ===========================================================================
# 5. EMERGENCY CONTACTS
# ===========================================================================
def render_contacts(form=None, editing=None):
    contacts = db.query_all(
        "SELECT * FROM emergency_contacts WHERE user_id = ? ORDER BY priority, contact_id",
        (g.user["user_id"],))
    return render_template("contacts.html", contacts=contacts, editing=editing,
                           form=form or (dict(editing) if editing else {}))


def get_own_contact(contact_id):
    row = db.query_one("SELECT * FROM emergency_contacts WHERE contact_id = ? AND user_id = ?",
                       (contact_id, g.user["user_id"]))
    if row is None:
        abort(404)
    return row


@app.route("/contacts")
@login_required
def contacts_page():
    edit_id = request.args.get("edit", type=int)
    return render_contacts(editing=get_own_contact(edit_id) if edit_id else None)


@app.route("/contacts/save", methods=["POST"])
@login_required
def contact_save():
    uid = g.user["user_id"]
    f = request.form
    name = f.get("contact_name", "").strip()
    phone = normalize_phone(f.get("phone"))
    email = f.get("email", "").strip().lower()
    relationship = f.get("relationship", "").strip()
    contact_id = f.get("contact_id", type=int)
    editing = get_own_contact(contact_id) if contact_id else None

    errors = []
    if not 1 <= len(name) <= 100:
        errors.append("Contact name is required (max 100 characters).")
    if phone is None:
        errors.append("Phone number must contain 7-15 digits.")
    if email and not valid_email(email):
        errors.append("Please enter a valid email address (or leave it empty).")
    if len(relationship) > 50:
        errors.append("Relationship is too long (max 50 characters).")
    try:
        priority = int(f.get("priority") or 0)
        if not 1 <= priority <= 99:
            raise ValueError
    except ValueError:
        errors.append("Priority must be a number from 1 to 99 (1 = contacted first).")
        priority = 1

    if errors:
        for e in errors:
            flash(e, "error")
        return render_contacts(form=f, editing=editing), 400

    if editing:
        db.execute("UPDATE emergency_contacts SET contact_name=?, phone=?, email=?, relationship=?, "
                   "priority=? WHERE contact_id=? AND user_id=?",
                   (name, phone, email or None, relationship or None, priority, contact_id, uid))
        db.log_history(uid, "contact", contact_id, f"Updated emergency contact '{name}'")
        flash("Contact updated.", "success")
    else:
        cur = db.execute("INSERT INTO emergency_contacts (user_id, contact_name, phone, email, "
                         "relationship, priority) VALUES (?, ?, ?, ?, ?, ?)",
                         (uid, name, phone, email or None, relationship or None, priority))
        db.log_history(uid, "contact", cur.lastrowid, f"Added emergency contact '{name}'")
        flash("Contact added.", "success")
    return redirect(url_for("contacts_page"))


@app.route("/contacts/<int:contact_id>/delete", methods=["POST"])
@login_required
def contact_delete(contact_id):
    c = get_own_contact(contact_id)
    uid = g.user["user_id"]
    db.execute("DELETE FROM emergency_contacts WHERE contact_id=? AND user_id=?", (contact_id, uid))
    db.log_history(uid, "contact", contact_id, f"Deleted emergency contact '{c['contact_name']}'")
    flash("Contact deleted.", "success")
    return redirect(url_for("contacts_page"))


# ===========================================================================
# 6. SOS
# ===========================================================================
def build_sos_message(user, coords, triggered_at):
    """Compose the alert text sent to emergency contacts."""
    if coords:
        lat, lng, acc = coords
        where = f"Location: {maps_link(lat, lng)}"
        if acc is not None:
            where += f" (accuracy about {round(acc)} m)"
    else:
        where = "Location: not available (the user's device did not share it)."
    phone = f" Phone: {user['phone']}." if user["phone"] else ""
    return (f"EMERGENCY ALERT: {user['full_name']} has triggered an SOS and may need help "
            f"urgently. Time: {triggered_at}. {where}{phone}")


def dispatch_alert(contact, message):
    """Send the alert to ONE contact.

    DEMO IMPLEMENTATION: nothing is actually sent - we only log it. To go live,
    replace the body with an SMS call (e.g. Twilio) and/or smtplib email and
    return {"ok": False, ...} when sending fails. The rest of the app does not change.
    """
    app.logger.info("[SOS DISPATCH - demo] to %s (%s): %s",
                    contact["contact_name"], contact["phone"], message)
    return {
        "ok": True,
        "channel": "demo-log",
        "contact_name": contact["contact_name"],
        "phone": contact["phone"],
        "email": contact["email"],
        "relationship": contact["relationship"],
    }


@app.route("/sos")
@login_required
def sos_page():
    uid = g.user["user_id"]
    events = db.query_all(
        "SELECT e.*, l.latitude, l.longitude FROM emergency_events e "
        "LEFT JOIN locations l ON l.event_id = e.event_id "
        "WHERE e.user_id = ? ORDER BY e.triggered_at DESC, e.event_id DESC LIMIT 10", (uid,))
    contact_count = db.query_one("SELECT COUNT(*) AS n FROM emergency_contacts WHERE user_id = ?",
                                 (uid,))["n"]
    return render_template("sos.html", events=events, contact_count=contact_count,
                           maps_link=maps_link, countdown=SOS_COUNTDOWN_SECONDS)


@app.route("/api/sos/cancel", methods=["POST"])
@login_required
def api_sos_cancel():
    """User pressed CANCEL during the countdown -> record a 'cancelled' event."""
    uid = g.user["user_id"]
    now = now_str()
    cur = db.execute(
        "INSERT INTO emergency_events (user_id, triggered_at, status, message, resolved_at) "
        "VALUES (?, ?, 'cancelled', ?, ?)",
        (uid, now, "SOS cancelled by the user during the countdown.", now))
    db.log_history(uid, "sos", cur.lastrowid, "SOS cancelled during countdown")
    return jsonify(ok=True, event_id=cur.lastrowid)


@app.route("/api/sos", methods=["POST"])
@login_required
def api_sos():
    """Countdown finished: record the event, location, contacts, and dispatch."""
    uid = g.user["user_id"]
    data = request.get_json(silent=True) or {}
    coords = parse_coords(data)          # None if denied / invalid -> SOS still works
    triggered_at = now_str()

    # 1. Create the event.
    event_id = db.execute(
        "INSERT INTO emergency_events (user_id, triggered_at, status) VALUES (?, ?, 'triggered')",
        (uid, triggered_at)).lastrowid

    # 2. Store the location (only this once, only for this event).
    if coords:
        db.execute("INSERT INTO locations (event_id, latitude, longitude, accuracy_m, captured_at) "
                   "VALUES (?, ?, ?, ?, ?)", (event_id, coords[0], coords[1], coords[2], triggered_at))

    # 3. Fetch this user's contacts, highest priority first.
    contacts = db.query_all(
        "SELECT * FROM emergency_contacts WHERE user_id = ? ORDER BY priority, contact_id", (uid,))

    # 4. Build the message and dispatch it to each contact.
    message = build_sos_message(g.user, coords, triggered_at)
    results = [dispatch_alert(c, message) for c in contacts]
    sent = sum(1 for r in results if r["ok"])
    status = "dispatched" if sent > 0 else "failed"
    if not contacts:
        message += "\n[No emergency contacts are saved, so nobody could be alerted.]"

    # 5. Save the final state + message to the DB.
    db.execute("UPDATE emergency_events SET status=?, message=?, resolved_at=? "
               "WHERE event_id=? AND user_id=?", (status, message, now_str(), event_id, uid))
    db.log_history(uid, "sos", event_id,
                   f"SOS {status}: {sent}/{len(contacts)} contact(s) alerted; "
                   f"location {'captured' if coords else 'unavailable'}")
    if coords:
        db.log_history(uid, "location", event_id, "Location captured for SOS event")

    return jsonify(
        ok=True, event_id=event_id, status=status, message=message,
        map_link=maps_link(coords[0], coords[1]) if coords else None,
        steps={"location_captured": bool(coords), "contacts_found": len(contacts),
               "alerts_sent": sent, "recorded": True},
        recipients=results,
    )


# ===========================================================================
# 7. LOCATION SHARING
# ===========================================================================
@app.route("/location")
@login_required
def location_page():
    return render_template("location.html")


@app.route("/api/location", methods=["POST"])
@login_required
def api_location():
    """Validate coordinates sent by the browser and return a shareable map link.
    Coordinates are NOT stored - only a history entry is logged."""
    coords = parse_coords(request.get_json(silent=True) or {})
    if coords is None:
        return jsonify(ok=False, error="Invalid coordinates."), 400
    lat, lng, acc = coords
    link = maps_link(lat, lng)
    db.log_history(g.user["user_id"], "location", None,
                   f"Generated location share link ({link})")
    return jsonify(ok=True, link=link, latitude=lat, longitude=lng, accuracy=acc,
                   captured_at=now_str())


# ===========================================================================
# 8. HISTORY (read-only)
# ===========================================================================
@app.route("/history")
@login_required
def history_page():
    f_type = request.args.get("type", "")
    date_from = request.args.get("from", "")
    date_to = request.args.get("to", "")

    # Build the WHERE clause from fixed fragments; values always go in `params`.
    where, params = ["user_id = ?"], [g.user["user_id"]]
    if f_type in HISTORY_TYPES:
        where.append("activity_type = ?")
        params.append(f_type)
    else:
        f_type = ""
    for value, op, label in ((date_from, ">=", "from"), (date_to, "<=", "to")):
        try:
            datetime.strptime(value, "%Y-%m-%d")
            where.append(f"date(created_at) {op} ?")
            params.append(value)
        except ValueError:
            if label == "from":
                date_from = ""
            else:
                date_to = ""
    rows = db.query_all(
        "SELECT * FROM history WHERE " + " AND ".join(where) +
        " ORDER BY created_at DESC, history_id DESC LIMIT 300", params)
    return render_template("history.html", entries=rows, types=HISTORY_TYPES,
                           f_type=f_type, date_from=date_from, date_to=date_to)


# ===========================================================================
# 9. ADMIN (separate login; sees account info + counts only)
# ===========================================================================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        admin = db.query_one("SELECT admin_id, password_hash FROM admins WHERE username = ?",
                             (username,))
        if admin and check_password_hash(admin["password_hash"], password):
            session.clear()
            session["admin_id"] = admin["admin_id"]
            session.permanent = True
            return redirect(url_for("admin_dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("admin_login.html")


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.clear()
    flash("Admin logged out.", "success")
    return redirect(url_for("admin_login"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    # PRIVACY: only account fields and COUNTS are selected. Reminder titles/descriptions
    # and location data are never queried here.
    users = db.query_all(
        "SELECT u.user_id, u.full_name, u.email, u.is_active, u.created_at, "
        "(SELECT COUNT(*) FROM reminders r WHERE r.user_id = u.user_id) AS reminder_count, "
        "(SELECT COUNT(*) FROM emergency_contacts c WHERE c.user_id = u.user_id) AS contact_count, "
        "(SELECT COUNT(*) FROM emergency_events e WHERE e.user_id = u.user_id "
        "   AND e.status != 'cancelled') AS sos_count, "
        "(SELECT COUNT(*) FROM history h WHERE h.user_id = u.user_id) AS activity_count "
        "FROM users u ORDER BY u.created_at DESC")
    totals = {
        "users": len(users),
        "active": sum(1 for u in users if u["is_active"]),
        "reminders": sum(u["reminder_count"] for u in users),
        "sos": sum(u["sos_count"] for u in users),
    }
    return render_template("admin.html", users=users, totals=totals, admin=g.admin)


@app.route("/admin/users/<int:user_id>/toggle", methods=["POST"])
@admin_required
def admin_toggle_user(user_id):
    user = db.query_one("SELECT user_id, full_name, is_active FROM users WHERE user_id = ?",
                        (user_id,))
    if user is None:
        abort(404)
    new_state = 0 if user["is_active"] else 1
    db.execute("UPDATE users SET is_active = ? WHERE user_id = ?", (new_state, user_id))
    flash(f"{user['full_name']} was {'activated' if new_state else 'deactivated'}.", "success")
    return redirect(url_for("admin_dashboard"))


# ===========================================================================
# Error pages + startup
# ===========================================================================
@app.errorhandler(404)
def not_found(_):
    if request.path.startswith("/api/"):
        return jsonify(ok=False, error="Not found."), 404
    return render_template("error.html", code=404, message="That page or item was not found."), 404


db.init_db(app)  # create tables + seed demo data on startup

if __name__ == "__main__":
    # debug=True is handy for development; turn it off for any real deployment.
    app.run(host="127.0.0.1", port=5000, debug=True)
