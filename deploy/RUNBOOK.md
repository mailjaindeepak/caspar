# Deploying br.investorguruji.com — runbook

Your DNS is on DigitalOcean and investorguruji.com already runs on droplet
167.71.225.148, so the app goes on that droplet. Three steps.

## 1. DNS (DigitalOcean dashboard, 1 minute)
Networking -> Domains -> investorguruji.com -> Create record:
- Type **A**, hostname **br**, value **167.71.225.148**, TTL default.

## 2. Copy the app to the droplet (from this PC)
```bash
ssh root@167.71.225.148 "mkdir -p /opt/caspar/db"
```
```bash
scp -r app deploy/br_setup.sh root@167.71.225.148:/opt/caspar/
```
```bash
scp db/leads.db root@167.71.225.148:/opt/caspar/db/
```
(If you log in as a non-root user or with a key file, add `-i <keyfile>` /
change `root@` accordingly.)

## 3. Run the setup script on the droplet
```bash
ssh root@167.71.225.148 "bash /opt/caspar/br_setup.sh"
```
It installs python venv + nginx vhost + systemd service + HTTPS cert, and
keeps port 8765 firewalled (only nginx reaches the app). The existing
investorguruji.com site is not touched — the vhost is a separate file, and
`nginx -t` runs before any reload.

Then open https://br.investorguruji.com — done.

## Afterwards
- **Passwords:** reset all users before sharing the URL
  (`ssh root@167.71.225.148 "cd /opt/caspar && venv/bin/python app/manage.py"`).
- **Weekly lead sync from this PC** (after each pipeline refresh):
  `scp db/leads.db root@167.71.225.148:/opt/caspar/db/` then
  `ssh root@167.71.225.148 "systemctl restart caspar-leads"`.
  (Better long-term: run app/sync_leads.py on the droplet against a pushed
  caspar.db, or rsync only; statuses/notes live in the droplet copy once the
  team starts using it — from that point, NEVER overwrite leads.db from the
  PC; pull it down instead before syncing new leads into it.)
- **Backups:** `scp root@167.71.225.148:/opt/caspar/db/leads.db backups/leads-$(date +%F).db`
  weekly — it holds all statuses/notes.
- **Caution:** the app checks the existing site's stack only for nginx. If the
  droplet serves investorguruji.com via Apache or Docker instead, stop and
  tell me what `systemctl status nginx apache2` shows before running step 3.
