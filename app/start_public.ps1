# Start the Caspar lead app + Cloudflare quick tunnel (public HTTPS URL).
# Prereqs (one-time):  pip install waitress   and   winget install Cloudflare.cloudflared
# Usage:  powershell -ExecutionPolicy Bypass -File app\start_public.ps1

$root = Split-Path $PSScriptRoot -Parent

# 1) app server (waitress) in its own window
Start-Process -FilePath "python" -ArgumentList "$root\app\server.py" -WorkingDirectory $root
Start-Sleep -Seconds 3

# 2) Cloudflare quick tunnel -> prints a https://<random>.trycloudflare.com URL
#    (URL changes each time the tunnel restarts; see app/HOSTING.md for a stable URL)
cloudflared tunnel --url http://127.0.0.1:8765
