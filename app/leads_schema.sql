-- Lead-management state (db/leads.db). Separate from caspar.db on purpose:
-- caspar.db is rebuilt by pipeline runs; this DB holds human work and must
-- never be clobbered. Referenced by natural keys (licence_no, clu_file_no).

CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY,
    username    TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    pw_hash     TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT 'member',   -- admin | member
    active      INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- A city only becomes visible to members when released=1.
CREATE TABLE IF NOT EXISTS cities (
    city        TEXT PRIMARY KEY,                 -- lowercase dir name under outputs/
    released    INTEGER NOT NULL DEFAULT 0,
    released_at TEXT
);

CREATE TABLE IF NOT EXISTS leads (
    id              INTEGER PRIMARY KEY,
    city            TEXT NOT NULL REFERENCES cities(city),
    kind            TEXT NOT NULL,                -- parcel | hospitality | developer
    source_key      TEXT NOT NULL,                -- licence_no / clu_file_no / dev:<name>
    title           TEXT NOT NULL,
    subtitle        TEXT,
    priority        REAL,                         -- need_score / luxury score, higher = hotter
    contact_emails  TEXT,
    contact_phones  TEXT,
    details_json    TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'new',  -- new|contacted|replied|meeting_set|handed_off|deal|on_hold|dropped
    assigned_to     INTEGER REFERENCES users(id),
    batch_tag       TEXT NOT NULL,                -- import date YYYY-MM-DD, "new this week" = latest batch
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (city, source_key)
);

-- Notes double as the activity/audit trail (status changes carry old/new).
CREATE TABLE IF NOT EXISTS lead_notes (
    id          INTEGER PRIMARY KEY,
    lead_id     INTEGER NOT NULL REFERENCES leads(id),
    user_id     INTEGER NOT NULL REFERENCES users(id),
    note        TEXT,
    old_status  TEXT,
    new_status  TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE INDEX IF NOT EXISTS idx_leads_city_status ON leads(city, status);
CREATE INDEX IF NOT EXISTS idx_notes_lead ON lead_notes(lead_id);
