#!/usr/bin/env bash
# Rebuilds the visitor dashboard at https://data-mechanics.com/stats/ from Caddy's access logs, with GoAccess.
# The datamechanics-stats timer runs it every 10 minutes.
# Only page views count: static files, the JSON and other data requests, the admin, and scripts are left out.
# GoAccess leaves out the bots it knows, and shortens every IP address in the report.
set -euo pipefail

OUT=/srv/stats
mkdir -p "$OUT"

# Countries come from DB-IP's free country database (CC BY 4.0, https://db-ip.com), fetched again once a month.
# A failed download keeps the copy there is; without any copy, the dashboard has no countries.
GEO=/var/lib/goaccess/dbip-country-lite.mmdb
mkdir -p "$(dirname "$GEO")"
if [ ! -f "$GEO" ] || [ -n "$(find "$GEO" -mtime +30)" ]; then
	curl -sf "https://download.db-ip.com/free/dbip-country-lite-$(date +%Y-%m).mmdb.gz" | gunzip > "$GEO.tmp" \
		&& mv "$GEO.tmp" "$GEO" || rm -f "$GEO.tmp"
fi
geo=()
[ -f "$GEO" ] && geo=(--geoip-database="$GEO")

# The current log and the ones Caddy has rolled (Caddyfile, log), compressed or not.
# grep finds nothing to keep in an empty log; `|| true` keeps that from failing the pipeline.
zcat -f /var/log/caddy/data-mechanics*.log* \
	| { grep -v -E '"uri":"[^"]*(/static/|/media/|/jsi18n/|/admin/|\.(json|geojson|xml|txt|ico)[?"])' || true; } \
	| { grep -v -E '"User-Agent":\["[^"]*(curl|Wget|python|HeadlessChrome|Go-http-client)' || true; } \
	| goaccess - --log-format=CADDY --ignore-crawlers --anonymize-ip --no-progress --tz=Europe/Vienna "${geo[@]}" \
		--html-report-title="Data Mechanics visitors · countries by DB-IP" -o "$OUT/index.tmp.html"

# Swapped in whole, so the page is never read half written.
mv "$OUT/index.tmp.html" "$OUT/index.html"
chmod 644 "$OUT/index.html"
