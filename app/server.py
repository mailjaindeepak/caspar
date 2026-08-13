"""Caspar lead-management web app.

Run:  python app/server.py            (listens on 0.0.0.0:8765 for LAN access)

Members see only released cities; admins additionally get /admin for user
management, city release, and lead sync.
"""
import functools
import json
import secrets
import sqlite3
from datetime import date, datetime
from pathlib import Path

from flask import (Flask, abort, flash, g, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

import sync_leads

ROOT = Path(__file__).resolve().parent.parent
LEADS_DB = ROOT / "db" / "leads.db"

STATUSES = ["new", "contacted", "replied", "meeting_set", "handed_off",
            "deal", "on_hold", "dropped"]
STATUS_LABELS = {
    "new": "New", "contacted": "Contacted", "replied": "Replied",
    "meeting_set": "Meeting set", "handed_off": "Handed to Varun/Taran",
    "deal": "Deal", "on_hold": "On hold", "dropped": "Dropped",
}
KIND_LABELS = {
    "target_parcel": "Target parcel", "ripe_parcel": "Ripe parcel",
    "hospitality": "Hospitality", "developer": "Developer",
}

app = Flask(__name__)


def _secret_key():
    cx = sync_leads.connect()
    row = cx.execute("SELECT value FROM meta WHERE key='secret_key'").fetchone()
    if row:
        key = row["value"]
    else:
        key = secrets.token_hex(32)
        cx.execute("INSERT INTO meta(key, value) VALUES ('secret_key', ?)", (key,))
        cx.commit()
    cx.close()
    return key


app.secret_key = _secret_key()


def db():
    if "db" not in g:
        g.db = sqlite3.connect(LEADS_DB)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    cx = g.pop("db", None)
    if cx is not None:
        cx.close()


def current_user():
    if "user_id" not in session:
        return None
    return db().execute("SELECT * FROM users WHERE id=? AND active=1",
                        (session["user_id"],)).fetchone()


def login_required(admin=False):
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*a, **kw):
            user = current_user()
            if user is None:
                return redirect(url_for("login", next=request.path))
            if admin and user["role"] != "admin":
                abort(403)
            g.user = user
            return fn(*a, **kw)
        return wrapper
    return deco


def check_csrf():
    if request.form.get("_csrf") != session.get("_csrf"):
        abort(400, "bad csrf token")


@app.context_processor
def inject_globals():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return dict(csrf=session["_csrf"], user=getattr(g, "user", None),
                STATUSES=STATUSES, STATUS_LABELS=STATUS_LABELS,
                KIND_LABELS=KIND_LABELS)


def visible_cities(user):
    q = "SELECT * FROM cities {} ORDER BY city"
    if user["role"] == "admin":
        return db().execute(q.format("")).fetchall()
    return db().execute(q.format("WHERE released=1")).fetchall()


def city_or_403(user, city):
    row = db().execute("SELECT * FROM cities WHERE city=?", (city,)).fetchone()
    if row is None:
        abort(404)
    if not row["released"] and user["role"] != "admin":
        abort(403)
    return row


# ---------------- auth ----------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        row = db().execute("SELECT * FROM users WHERE username=? AND active=1",
                           (request.form.get("username", "").strip().lower(),)).fetchone()
        if row and check_password_hash(row["pw_hash"], request.form.get("password", "")):
            session.clear()
            session["user_id"] = row["id"]
            return redirect(request.args.get("next") or url_for("dashboard"))
        flash("Wrong username or password.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------- team pages ----------------

@app.route("/")
@login_required()
def dashboard():
    cities = []
    for c in visible_cities(g.user):
        stats = db().execute(
            """SELECT count(*) AS total,
                      sum(CASE WHEN status='new' THEN 1 ELSE 0 END) AS fresh,
                      sum(CASE WHEN status IN ('meeting_set','handed_off','deal')
                          THEN 1 ELSE 0 END) AS wins,
                      max(batch_tag) AS last_batch
               FROM leads WHERE city=?""", (c["city"],)).fetchone()
        cities.append((c, stats))
    mine = db().execute(
        """SELECT l.* FROM leads l JOIN cities c ON c.city=l.city
           WHERE l.assigned_to=? AND l.status NOT IN ('deal','dropped')
                 AND (c.released=1 OR ?='admin')
           ORDER BY l.updated_at DESC LIMIT 25""",
        (g.user["id"], g.user["role"])).fetchall()
    return render_template("dashboard.html", cities=cities, mine=mine)


@app.route("/city/<city>")
@login_required()
def city_page(city):
    c = city_or_403(g.user, city)
    kind = request.args.get("kind") or None
    status = request.args.get("status") or None
    assignee = request.args.get("assignee") or None
    sql = """SELECT l.*, u.name AS assignee_name FROM leads l
             LEFT JOIN users u ON u.id=l.assigned_to WHERE l.city=?"""
    params = [city]
    if kind:
        sql += " AND l.kind=?"; params.append(kind)
    if status:
        sql += " AND l.status=?"; params.append(status)
    if assignee == "me":
        sql += " AND l.assigned_to=?"; params.append(g.user["id"])
    elif assignee == "none":
        sql += " AND l.assigned_to IS NULL"
    sql += """ ORDER BY CASE WHEN l.status='new' THEN 0 ELSE 1 END,
               l.priority IS NULL, l.priority DESC, l.updated_at DESC"""
    leads = db().execute(sql, params).fetchall()
    latest_batch = db().execute("SELECT max(batch_tag) FROM leads WHERE city=?",
                                (city,)).fetchone()[0]
    return render_template("city.html", c=c, leads=leads, kind=kind,
                           status=status, assignee=assignee,
                           latest_batch=latest_batch)


@app.route("/lead/<int:lead_id>", methods=["GET", "POST"])
@login_required()
def lead_page(lead_id):
    lead = db().execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
    if lead is None:
        abort(404)
    city_or_403(g.user, lead["city"])

    if request.method == "POST":
        check_csrf()
        note = (request.form.get("note") or "").strip()
        new_status = request.form.get("status")
        assign = request.form.get("assigned_to")
        old_status = lead["status"]
        sets, params = [], []
        if new_status and new_status in STATUSES and new_status != old_status:
            sets.append("status=?"); params.append(new_status)
        else:
            new_status = None
        if assign is not None:
            assigned = int(assign) if assign else None
            sets.append("assigned_to=?"); params.append(assigned)
        if sets:
            sets.append("updated_at=?")
            params.append(datetime.now().isoformat(timespec="seconds"))
            db().execute(f"UPDATE leads SET {', '.join(sets)} WHERE id=?",
                         (*params, lead_id))
        if note or new_status:
            db().execute(
                """INSERT INTO lead_notes(lead_id, user_id, note, old_status, new_status)
                   VALUES (?,?,?,?,?)""",
                (lead_id, g.user["id"], note or None,
                 old_status if new_status else None, new_status))
        db().commit()
        return redirect(url_for("lead_page", lead_id=lead_id))

    notes = db().execute(
        """SELECT n.*, u.name AS user_name FROM lead_notes n
           JOIN users u ON u.id=n.user_id WHERE n.lead_id=?
           ORDER BY n.created_at DESC""", (lead_id,)).fetchall()
    members = db().execute(
        "SELECT id, name FROM users WHERE active=1 ORDER BY name").fetchall()
    details = json.loads(lead["details_json"])
    return render_template("lead.html", lead=lead, notes=notes,
                           members=members, details=details)


@app.route("/city/<city>/directory/<which>")
@login_required()
def directory(city, which):
    c = city_or_403(g.user, city)
    fname = {"gatekeepers": "gatekeepers.csv",
             "contacts": "promoter_contacts.csv"}.get(which)
    if not fname:
        abort(404)
    rows = sync_leads.read_csv(ROOT / "outputs" / city / fname)
    cols = list(rows[0].keys()) if rows else []
    return render_template("directory.html", c=c, which=which, rows=rows, cols=cols)


# ---------------- admin ----------------

@app.route("/admin", methods=["GET", "POST"])
@login_required(admin=True)
def admin():
    cx = db()
    if request.method == "POST":
        check_csrf()
        action = request.form.get("action")
        if action == "release":
            city = request.form["city"]
            cx.execute("UPDATE cities SET released=1, released_at=? WHERE city=?",
                       (datetime.now().isoformat(timespec="seconds"), city))
            cx.commit()
            n = sync_leads.sync_city(cx, city, date.today().isoformat())
            flash(f"Released {city} — {n} leads imported.")
        elif action == "unrelease":
            cx.execute("UPDATE cities SET released=0 WHERE city=?",
                       (request.form["city"],))
            cx.commit()
            flash(f"Hid {request.form['city']} from the team.")
        elif action == "sync":
            batch = date.today().isoformat()
            msgs = []
            for r in cx.execute("SELECT city FROM cities WHERE released=1"):
                n = sync_leads.sync_city(cx, r["city"], batch)
                msgs.append(f"{r['city']} +{n}")
            flash("Synced: " + (", ".join(msgs) or "no released cities"))
        elif action == "add_user":
            uname = request.form["username"].strip().lower()
            try:
                cx.execute(
                    "INSERT INTO users(username, name, pw_hash, role) VALUES (?,?,?,?)",
                    (uname, request.form["name"].strip(),
                     generate_password_hash(request.form["password"]),
                     "admin" if request.form.get("role") == "admin" else "member"))
                cx.commit()
                flash(f"User '{uname}' created.")
            except sqlite3.IntegrityError:
                flash(f"Username '{uname}' already exists.")
        elif action == "toggle_user":
            cx.execute("UPDATE users SET active=1-active WHERE id=? AND id<>?",
                       (int(request.form["user_id"]), g.user["id"]))
            cx.commit()
        return redirect(url_for("admin"))

    cities = cx.execute(
        """SELECT c.*, count(l.id) AS n FROM cities c
           LEFT JOIN leads l ON l.city=c.city GROUP BY c.city ORDER BY c.city""").fetchall()
    users = cx.execute("SELECT * FROM users ORDER BY id").fetchall()
    return render_template("admin.html", cities=cities, users=users)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8765, debug=False)
