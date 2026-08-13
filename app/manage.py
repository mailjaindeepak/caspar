"""Admin CLI for the lead system.

    python app/manage.py create-user <username> <full name> <password> [admin|member]
    python app/manage.py reset-password <username> <newpassword>
    python app/manage.py release <city>       # make city visible to the team + sync its leads
    python app/manage.py unrelease <city>
    python app/manage.py status               # cities, users, lead counts
"""
import sys
from datetime import datetime

from werkzeug.security import generate_password_hash

import sync_leads


def main():
    cx = sync_leads.connect()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "create-user":
        username, name, password = sys.argv[2], sys.argv[3], sys.argv[4]
        role = sys.argv[5] if len(sys.argv) > 5 else "member"
        assert role in ("admin", "member"), "role must be admin or member"
        cx.execute("INSERT INTO users(username, name, pw_hash, role) VALUES (?,?,?,?)",
                   (username.lower(), name, generate_password_hash(password), role))
        cx.commit()
        print(f"created {role} '{username}'")

    elif cmd == "reset-password":
        username, password = sys.argv[2], sys.argv[3]
        n = cx.execute("UPDATE users SET pw_hash=? WHERE username=?",
                       (generate_password_hash(password), username.lower())).rowcount
        cx.commit()
        print("password updated" if n else "no such user")

    elif cmd == "release":
        city = sys.argv[2].lower()
        cx.execute("UPDATE cities SET released=1, released_at=? WHERE city=?",
                   (datetime.now().isoformat(timespec="seconds"), city))
        cx.commit()
        n = sync_leads.sync_city(cx, city, sync_leads.date.today().isoformat())
        print(f"released {city}, imported {n} leads")

    elif cmd == "unrelease":
        city = sys.argv[2].lower()
        cx.execute("UPDATE cities SET released=0 WHERE city=?", (city,))
        cx.commit()
        print(f"unreleased {city} (its leads stay in the DB but are hidden)")

    elif cmd == "status":
        print("cities:")
        for r in cx.execute("""SELECT c.city, c.released,
                                      count(l.id) AS n,
                                      sum(CASE WHEN l.status='new' THEN 1 ELSE 0 END) AS fresh
                               FROM cities c LEFT JOIN leads l ON l.city=c.city
                               GROUP BY c.city ORDER BY c.city"""):
            flag = "RELEASED" if r["released"] else "hidden  "
            print(f"  {flag}  {r['city']:<14} {r['n']:>4} leads ({r['fresh'] or 0} new)")
        print("users:")
        for r in cx.execute("SELECT username, name, role, active FROM users ORDER BY id"):
            print(f"  {r['username']:<14} {r['role']:<7} {'' if r['active'] else '(disabled)'} {r['name']}")

    else:
        print(__doc__)
    cx.close()


if __name__ == "__main__":
    main()
