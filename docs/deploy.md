# Deploying to the VPS

The site runs on a Hostinger VPS with Ubuntu 26.04 LTS:

- **Caddy** serves HTTPS for data-mechanics.com (certificates from Let's Encrypt, renewed automatically), static files and media, and proxies everything else to Gunicorn.
- **Gunicorn** runs Django as the `datamechanics` user, on a Unix socket (systemd unit `datamechanics`).
- **PostgreSQL 18** runs in Docker with the same `docker-compose.yml` as on your machine. It listens only on 127.0.0.1.
- **Timers**: `datamechanics-etl.timer` refreshes the data every Monday at 04:00; `datamechanics-backup.timer` dumps the database every night at 03:00 into `/srv/datamechanics/backups` (the newest 14 are kept).

Everything lives in `/srv/datamechanics`. The production `.env` there is created on the server with new secrets and is never copied from your machine.

## First deploy

1. **Set up the server** (once, as root): copy `deploy/setup-server.sh` to the VPS and run it. It installs Python, Docker, Caddy and rsync, creates the `datamechanics` user and writes `/srv/datamechanics/.env`.
2. **Ship the code** from your machine: `deploy/deploy.sh root@<vps-address>`. It copies the code and media, installs the dependencies, starts the database, migrates, collects static files, installs the systemd units and the Caddyfile, and restarts the site.
3. **Move the data**: either copy your local database (posts included), or rebuild it.
   - Copy: dump locally with `docker exec datamechanics-db pg_dump -U datamechanics -d datamechanics --format=custom > datamechanics.dump`, then `scp` the file to the VPS. Restore it there with `docker exec -i datamechanics-db pg_restore -U datamechanics -d datamechanics --no-owner --clean --if-exists < datamechanics.dump`.
   - Rebuild: `sudo -u datamechanics .venv/bin/python manage.py etl` for the data. The posts come over with `dumpdata blog` and `loaddata`.
4. **Create an admin user**: `cd /srv/datamechanics && sudo -u datamechanics .venv/bin/python manage.py createsuperuser`.
5. **Point the domain at the VPS** in Hostinger's DNS settings: set the `A` records for `@` and `www` to the VPS address (and `AAAA` if the VPS has IPv6; remove any old `AAAA` that points elsewhere). Leave `MX` and other mail records alone. This takes the WordPress site offline; its old post links redirect to the new ones.
6. **Watch Caddy get the certificate**: `journalctl -u caddy -f`. Once DNS has spread, it gets the certificate within a minute. Then open https://data-mechanics.com.

## Later deploys

`deploy/deploy.sh root@<vps-address>`. Run the tests first: `python manage.py test`.

## Useful commands on the VPS

- Logs: `journalctl -u datamechanics -f` (Django and Gunicorn), `journalctl -u caddy -f`, `/var/log/caddy/data-mechanics.log` (requests).
- Run the ETL now: `systemctl start datamechanics-etl`, then `journalctl -u datamechanics-etl`.
- Back up now: `systemctl start datamechanics-backup`.
- Timers: `systemctl list-timers 'datamechanics-*'`.
- Database shell: `docker exec -it datamechanics-db psql -U datamechanics -d datamechanics`.

## Visitors

https://data-mechanics.com/stats/ shows who visits: visitors and page views per day, pages, referrers, countries, browsers.
GoAccess builds it every 10 minutes from Caddy's access log (`deploy/stats.sh`, `datamechanics-stats.timer`).

- **Login**: user `klaus`. The first deploy made the password; read it with `cat /root/stats-password`.
- **New password**: `caddy hash-password`, put the hash in `/etc/caddy/stats-auth`, then `systemctl reload caddy`.
- **What counts**: page views only. Static files, data requests, the admin, known bots and scripts are left out, and IP addresses are shortened.
- **How far back**: Caddy keeps 90 days of logs (`Caddyfile`, `log`), so the dashboard covers 90 days.
- **Rebuild now**: `systemctl start datamechanics-stats`.

## Once HTTPS has run without trouble for a while

Raise `DJANGO_HSTS_SECONDS` in `/srv/datamechanics/.env` to `31536000` (one year) and run `systemctl restart datamechanics`.
