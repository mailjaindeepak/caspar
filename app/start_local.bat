@echo off
rem Start the Caspar lead app for LAN access (http://192.168.1.9:8765)
cd /d "%~dp0.."
echo Caspar Leads starting on http://localhost:8765 (team: http://192.168.1.9:8765)
python app\server.py
pause
