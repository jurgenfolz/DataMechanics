#!/usr/bin/env bash
# One-time setup of the VPS (Ubuntu 26.04), run as root. Running it again is safe.
# It installs the packages, creates the app user and directory, and writes a production .env with new secrets.
set -euo pipefail

APP=/srv/datamechanics
DOMAIN=data-mechanics.com

apt-get update
apt-get install -y python3 python3-venv rsync curl gpg

# Docker: keep an existing install (Hostinger's images ship Docker CE); otherwise use Ubuntu's packages.
command -v docker >/dev/null || apt-get install -y docker.io docker-compose-v2

# Caddy from its official repository: Ubuntu's package is years behind.
if [ ! -f /etc/apt/sources.list.d/caddy-stable.list ]; then
	curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/gpg.key | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
	curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt -o /etc/apt/sources.list.d/caddy-stable.list
	chmod o+r /usr/share/keyrings/caddy-stable-archive-keyring.gpg /etc/apt/sources.list.d/caddy-stable.list
	apt-get update
fi
apt-get install -y caddy

# The site runs as its own user, without a login shell.
id datamechanics >/dev/null 2>&1 || useradd --system --home-dir "$APP" --shell /usr/sbin/nologin datamechanics
# Caddy reaches Gunicorn's socket through the app user's group.
usermod -aG datamechanics caddy

mkdir -p "$APP" /var/log/caddy
chown datamechanics:datamechanics "$APP"
chown caddy:caddy /var/log/caddy

# A production .env, written once. New secrets; nothing is copied from the development machine.
if [ ! -f "$APP/.env" ]; then
	secret() { python3 -c "import secrets; print(secrets.token_urlsafe($1))"; }
	cat > "$APP/.env" <<EOF
DJANGO_SECRET_KEY=$(secret 50)
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=$DOMAIN,www.$DOMAIN
DJANGO_CSRF_TRUSTED_ORIGINS=https://$DOMAIN
GITHUB_URL=
POSTGRES_DB=datamechanics
POSTGRES_USER=datamechanics
POSTGRES_PASSWORD=$(secret 24)
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
EOF
	chown datamechanics:datamechanics "$APP/.env"
	chmod 600 "$APP/.env"
	echo "Wrote $APP/.env with new secrets."
fi

systemctl enable --now docker caddy
echo "Server ready. Next: run deploy/deploy.sh from your machine."
