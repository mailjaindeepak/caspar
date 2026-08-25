"""Caspar lead-management web app.

Run:  python app/server.py            (listens on 0.0.0.0:8765 for LAN access)

Members see only released cities; admins additionally get /admin for user
management, city release, and lead sync.
"""
import functools
import json
import re
import secrets
import sqlite3
from datetime import date, datetime
from pathlib import Path

from flask import (Flask, abort, flash, g, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

import sync_leads

import os

ROOT = Path(__file__).resolve().parent.parent
LEADS_DB = Path(os.environ.get("CASPAR_LEADS_DB", ROOT / "db" / "leads.db"))

# Cloud bootstrap: if the persistent-volume DB doesn't exist yet, seed it from
# the copy shipped in the repo (deploy/leads_seed.db) so first boot has the
# released cities, users, and leads.
_SEED = ROOT / "deploy" / "leads_seed.db"
if not LEADS_DB.exists() and _SEED.exists():
    LEADS_DB.parent.mkdir(parents=True, exist_ok=True)
    import shutil
    shutil.copy(_SEED, LEADS_DB)

STATUSES = ["new", "contacted", "replied", "meeting_set", "handed_off",
            "deal", "on_hold", "dropped"]
STATUS_LABELS = {
    "new": "New", "contacted": "Contacted", "replied": "Replied",
    "meeting_set": "Meeting set", "handed_off": "Handed to Varun/Taran",
    "deal": "Deal", "on_hold": "On hold", "dropped": "Dropped",
}
KIND_LABELS = {
    "parcel": "Land parcel",
    "application": "Licence application",
    "hospitality": "Hospitality",
    "developer": "Developer",
}
SITE_STATUSES = ["unchecked", "vacant", "under_construction", "operating"]
SITE_LABELS = {
    "unchecked": "Unchecked", "vacant": "Vacant land",
    "under_construction": "Under construction", "operating": "Operating",
}

# Ordered keyword -> hospitality lead type; first match wins, so compound
# activities ("Motel cum Restaurant") classify by their primary use.
HOSP_TYPES = [
    ("hotel", "Hotel"), ("motel", "Motel"), ("resort", "Resort"),
    ("guest", "Guest house"), ("boarding", "Guest house"),
    ("marriage", "Marriage palace"), ("wedding", "Marriage palace"),
    ("amusement", "Amusement park"), ("banquet", "Banquet hall"),
    ("restaurant", "Restaurant"), ("dhaba", "Dhaba"),
    ("farm", "Farm house"), ("club", "Club"),
]


def hosp_type(activity):
    a = (activity or "").lower()
    for key, label in HOSP_TYPES:
        if key in a:
            return label
    return "Other"


# DTCP licence purpose codes, humanized for the team
PURPOSE_LABELS = {
    "RPL": "Residential plotted colony",
    "RGH": "Residential group housing",
    "DDJAY-APHP": "Affordable plotted (DDJAY)",
    "AHP": "Affordable group housing",
    "NILP": "Integrated township (NILP)",
    "CPL": "Commercial plotted",
    "CIR-CIC": "Commercial (CIR/CIC)",
    "IPA": "Industrial park",
}

app = Flask(__name__)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    # Secure cookies when served over the HTTPS tunnel; harmless on plain LAN
    # only if members use the tunnel URL — LAN http access will still work
    # because Flask only *marks* the cookie; browsers enforce per-scheme.
    SESSION_COOKIE_SECURE=False,
    MAX_CONTENT_LENGTH=1024 * 1024,
)

# Honour X-Forwarded-* headers set by the tunnel so url_for/redirects use https
from werkzeug.middleware.proxy_fix import ProxyFix  # noqa: E402
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# ---- simple brute-force throttle on login (per username+ip) ----
_ATTEMPTS: dict = {}
LOCKOUT_AFTER = 6          # failed tries
LOCKOUT_WINDOW = 900       # within 15 minutes -> lock for the window


def _throttled(key: str) -> bool:
    import time
    now = time.time()
    tries = [t for t in _ATTEMPTS.get(key, []) if now - t < LOCKOUT_WINDOW]
    _ATTEMPTS[key] = tries
    return len(tries) >= LOCKOUT_AFTER


def _record_failure(key: str) -> None:
    import time
    _ATTEMPTS.setdefault(key, []).append(time.time())


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
                KIND_LABELS=KIND_LABELS, SITE_STATUSES=SITE_STATUSES,
                SITE_LABELS=SITE_LABELS)


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
        uname = request.form.get("username", "").strip().lower()
        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "?")
        key = f"{uname}|{ip.split(',')[0].strip()}"
        if _throttled(key):
            flash("Too many attempts — try again in 15 minutes.")
            return render_template("login.html"), 429
        row = db().execute("SELECT * FROM users WHERE username=? AND active=1",
                           (uname,)).fetchone()
        if row and check_password_hash(row["pw_hash"], request.form.get("password", "")):
            session.clear()
            session["user_id"] = row["id"]
            nxt = request.args.get("next") or ""
            # only allow same-site relative redirects
            return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//")
                            else url_for("dashboard"))
        _record_failure(key)
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
    min_acre = request.args.get("min_acre", type=float)
    site = request.args.get("site") or None
    sql = """SELECT l.*, u.name AS assignee_name FROM leads l
             LEFT JOIN users u ON u.id=l.assigned_to WHERE l.city=?"""
    params = [city]
    if kind:
        sql += " AND l.kind=?"; params.append(kind)
    # Dropped leads are hidden by default: a parcel excluded for a known,
    # recorded reason (already RERA-registered, etc.) otherwise reads as a live
    # opportunity and gets re-litigated every time someone opens the list. The
    # rows and their notes are kept — pick "Dropped" or "All incl. dropped" to
    # see them, which is where the reason for the exclusion lives.
    if status == "all":
        pass
    elif status:
        sql += " AND l.status=?"; params.append(status)
    else:
        sql += " AND l.status<>'dropped'"
    if assignee == "me":
        sql += " AND l.assigned_to=?"; params.append(g.user["id"])
    elif assignee == "none":
        sql += " AND l.assigned_to IS NULL"
    if site in SITE_STATUSES and kind == "hospitality":
        sql += " AND l.site_status=?"; params.append(site)
    sql += """ ORDER BY CASE WHEN l.status='new' THEN 0 ELSE 1 END,
               l.priority IS NULL, l.priority DESC, l.updated_at DESC"""
    leads = [dict(l) for l in db().execute(sql, params).fetchall()]
    for l in leads:
        l["d"] = json.loads(l["details_json"])
        try:
            l["area_fmt"] = f"{float(l['d'].get('area_acre')):.2f}"
        except (TypeError, ValueError):
            l["area_fmt"] = "?"
    if min_acre and kind in ("parcel", "hospitality", "application"):
        def _area(l):
            try:
                return float(l["d"].get("area_acre") or 0)
            except ValueError:
                return 0.0
        leads = [l for l in leads if _area(l) >= min_acre]
    if kind == "parcel":
        # surface the as-printed licence-holder name when it isn't just a
        # spelling variant of the resolved group (SPV / landowner licences)
        for l in leads:
            raw = l["d"].get("developer_raw") or ""
            l["holder_differs"] = bool(
                raw and sync_leads.norm_name(raw) != sync_leads.norm_name(l["title"]))
    if kind == "hospitality":
        for l in leads:
            l["hosp_type"] = hosp_type(l["d"].get("activity"))
        # unworked leads first, then biggest plots first
        leads.sort(key=lambda l: (l["status"] != "new",
                                  -(float(l["d"].get("area_acre") or 0))))
    latest_batch = db().execute("SELECT max(batch_tag) FROM leads WHERE city=?",
                                (city,)).fetchone()[0]
    # counts must match what the tabs actually show, or "Land parcels 9" over a
    # list of 5 looks like missing leads
    count_sql = "SELECT kind, count(*) FROM leads WHERE city=?"
    if status != "all":
        count_sql += " AND status<>'dropped'" if not status else " AND status=?"
    count_params = [city] + ([status] if status and status != "all" else [])
    kind_counts = dict(db().execute(count_sql + " GROUP BY kind",
                                    count_params).fetchall())
    n_dropped = db().execute(
        "SELECT count(*) FROM leads WHERE city=? AND status='dropped'",
        (city,)).fetchone()[0]
    return render_template("city.html", c=c, leads=leads, kind=kind,
                           status=status, assignee=assignee, min_acre=min_acre,
                           site=site, latest_batch=latest_batch,
                           kind_counts=kind_counts, n_dropped=n_dropped,
                           PURPOSE_LABELS=PURPOSE_LABELS)


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
        site = request.form.get("site_status")
        if (lead["kind"] == "hospitality" and site in SITE_STATUSES
                and site != lead["site_status"]):
            sets.append("site_status=?"); params.append(site)
            note = (note + "\n" if note else "") + f"Site check: {SITE_LABELS[site]}"
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


@app.route("/lead/<int:lead_id>/map")
@login_required()
def lead_map(lead_id):
    lead = db().execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
    if lead is None:
        abort(404)
    city_or_403(g.user, lead["city"])
    d = json.loads(lead["details_json"])
    polys = d.get("polygon_latlng") or []
    center = None
    if polys:
        pts = [p for ring in polys for p in ring]
        center = [sum(p[0] for p in pts) / len(pts),
                  sum(p[1] for p in pts) / len(pts)]
    elif d.get("map_link"):
        m = re.search(r"q=(-?[\d.]+),(-?[\d.]+)", d["map_link"])
        if m:
            center = [float(m.group(1)), float(m.group(2))]
    if center is None:
        abort(404)
    return render_template("map.html", lead=lead, polys=polys, center=center,
                           gmaps_link=d.get("map_link"))


@app.route("/city/<city>/directory/<which>")
@login_required()
def directory(city, which):
    c = city_or_403(g.user, city)
    fname = {"gatekeepers": "gatekeepers.csv",
             "contacts": "promoter_contacts.csv",
             "people": "people.csv"}.get(which)
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
    port = int(os.environ.get("PORT", 8765))
    try:
        from waitress import serve
        print(f"Serving on 0.0.0.0:{port} (waitress)")
        serve(app, host="0.0.0.0", port=port, threads=8)
    except ImportError:
        app.run(host="0.0.0.0", port=port, debug=False)
