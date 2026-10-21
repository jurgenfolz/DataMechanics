#!/usr/bin/env bash
# Runs on the VPS after each deploy, as root: installs dependencies, migrates, loads the curated tables,
# compiles the translations, collects static files and restarts.
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
# The curated tables (presidents and parties) ship with the code in data/, so every deploy reloads them.
as_app .venv/bin/python manage.py etl curated.parties curated.administrations
# The translations in locale/ are compiled here, from the .po files, with gettext's msgfmt.
command -v msgfmt >/dev/null || apt-get install -y -qq gettext >/dev/null
as_app .venv/bin/python manage.py compilemessages --ignore=.venv >/dev/null
as_app .venv/bin/python manage.py collectstatic --noinput --clear >/dev/null
as_app .venv/bin/python manage.py check --deploy --fail-level WARNING

install -m 644 deploy/systemd/*.service deploy/systemd/*.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now datamechanics-etl.timer datamechanics-backup.timer datamechanics-stats.timer
systemctl enable datamechanics
systemctl restart datamechanics

# The visitor dashboard (/stats/): GoAccess builds it, and Caddy guards it with a login kept only on this server.
# The login is made once, here. Its password is kept for root in /root/stats-password.
command -v goaccess >/dev/null || apt-get install -y -qq goaccess >/dev/null
if [ ! -f /etc/caddy/stats-auth ]; then
	password=$(openssl rand -base64 18)
	printf 'basic_auth {\n\tklaus %s\n}\n' "$(caddy hash-password --plaintext "$password")" > /etc/caddy/stats-auth
	chown root:caddy /etc/caddy/stats-auth
	chmod 640 /etc/caddy/stats-auth
	install -m 600 /dev/null /root/stats-password
	printf '%s\n' "$password" > /root/stats-password
fi
systemctl start datamechanics-stats.service

install -m 644 deploy/Caddyfile /etc/caddy/Caddyfile
systemctl reload caddy

echo "Deployed. Gunicorn: $(systemctl is-active datamechanics). Caddy: $(systemctl is-active caddy)."
