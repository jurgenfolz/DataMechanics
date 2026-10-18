#!/usr/bin/env bash
# Runs on the VPS after each deploy, as root: installs dependencies, migrates, collects static files and restarts.
set -euo pipefail

APP=/srv/datamechanics
cd "$APP"
as_app() { sudo -u datamechanics "$@"; }

[ -d .venv ] || as_app python3 -m venv .venv
as_app .venv/bin/pip install --quiet --upgrade pip
as_app .venv/bin/pip install --quiet -r requirements.txt

# The database container reads .env for its name, user and password.
docker compose up -d --wait

as_app .venv/bin/python manage.py migrate --noinput
as_app .venv/bin/python manage.py collectstatic --noinput --clear >/dev/null
as_app .venv/bin/python manage.py check --deploy --fail-level WARNING

install -m 644 deploy/systemd/*.service deploy/systemd/*.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now datamechanics-etl.timer datamechanics-backup.timer
systemctl enable datamechanics
systemctl restart datamechanics

install -m 644 deploy/Caddyfile /etc/caddy/Caddyfile
systemctl reload caddy

echo "Deployed. Gunicorn: $(systemctl is-active datamechanics). Caddy: $(systemctl is-active caddy)."
