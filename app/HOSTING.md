# Hosting the lead app on an external URL

The app itself is ready for public exposure (login-gated everywhere, CSRF,
hashed passwords, login throttling 6 tries/15 min, proxy-aware, waitress
production server). Three hosting options, in order of effort:

## Option A — Cloudflare quick tunnel (today, free, 5 minutes)
Runs from this PC; no account, no port-forwarding. URL is random and changes
whenever the tunnel restarts — fine for the demo phase.

One-time setup (run these two yourself):
```bash
pip install waitress
```
```bash
winget install --id Cloudflare.cloudflared --accept-source-agreements --accept-package-agreements
```
Then every time:
```bash
powershell -ExecutionPolicy Bypass -File app\start_public.ps1
```
The window prints `https://<random>.trycloudflare.com` — share that with the
team. Caveats: PC must stay on; URL changes on restart (re-share it).

## Option B — Named Cloudflare tunnel (stable URL, ~1 hr setup, ~Rs 800/yr)
Buy a domain (e.g. caspar-intel.in), add it to a free Cloudflare account, then:
`cloudflared tunnel login` -> `cloudflared tunnel create caspar` ->
route DNS `leads.caspar-intel.in` -> run as a Windows service
(`cloudflared service install`). Stable URL, auto-starts with the PC,
still free. Optional: put Cloudflare Access (email OTP allow-list) in front
for a second auth layer.

## Option C — Cloud VPS (permanent, PC-independent, ~Rs 400–800/mo)
When the team actually depends on it: a small VPS (Hetzner/DigitalOcean/
Lightsail), copy the repo, `pip install -r` + waitress behind Caddy (auto
HTTPS), rsync db/leads.db. Fits the "hosting" line in the monthly budget.
Keep leads.db backed up either way: it holds users + statuses + notes.

## Security notes (already enforced in code)
- All routes require login; admin routes require admin role.
- Login throttle: 6 failed tries per username+IP per 15 min.
- CSRF token on every POST; open-redirect guard on login `next`.
- Before sharing the URL: change every default/weak password
  (`python app/manage.py` — reset-password), especially the admin account.
- The tunnel gives HTTPS; never share the raw `http://<lan-ip>:8765` outside
  the LAN.
- leads.db is separate from caspar.db — the team's app never exposes the
  unreleased cities' data (city-release gating), and the repo/DB stay private.
