# Data Mechanics

Free public statistics on every country: world maps, charts over time and CSV downloads, with the source of every number. An open-source alternative to paywalled statistics portals, plus a blog on data, charts, Python and BI.

Live at https://data-mechanics.com.

## What is in it

- **Metrics**: 27 of them, from GDP, unemployment and debt to life expectancy, the V-Dem democracy indices, CO2 emissions and the homicide rate. Each one has its own page with a map, a line chart, a ranking and a download.
- **Politics mode**: one page per country with every metric coloured by the president in office, and the change during each presidency. Brazil (presidents since 1956) and the United States (since 1953).
- **Sources**: the World Bank (World Development Indicators), the IMF (World Economic Outlook), the UNDP (Human Development Report), Our World in Data (V-Dem and others), and Natural Earth for country borders. Presidents and parties are compiled by hand from Wikipedia into `data/politics/`, with party logos from Wikimedia Commons.
- **Blog**: posts written by Klaus Jürgen Folz.
- **Languages**: English, German and Portuguese. German lives under `/de/`, Portuguese under `/pt/`; the translations are in `locale/`.

## How it works

- `providers/` holds the ETL: one folder per data provider, one module per source, and each module writes one table.
- `geo/` defines the tables: the `geo_country` dimension and one `geo_<metric>_country_year` table per metric.
- `metrics/` holds the metric catalog (texts, tags and series), the queries and the pages. The site reads only the database.
- `politics/` holds Politics mode: the `pol_party` and `pol_administration` tables, the list of metrics it shows (`politics/metrics.py`) and its pages.
- `blog/` holds the posts; `pages/` holds the home page.
- Django and PostgreSQL on the server, ECharts in the browser.

## Run it locally

You need Python 3.13 or newer and Docker.

```
python -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env              # then fill in the secrets
docker compose up -d              # PostgreSQL 18
.venv/bin/python manage.py migrate
.venv/bin/python manage.py etl    # downloads every source, a few seconds each
.venv/bin/python manage.py runserver
```

Run the tests with `.venv/bin/python manage.py test`.

## Deploy

See [docs/deploy.md](docs/deploy.md). Moving an existing database is covered in [docs/postgres-migration.md](docs/postgres-migration.md).

## Licence

The code is licensed under the [GNU Affero General Public License v3.0](LICENSE). The data belongs to its sources and keeps their terms: every page and download names its source.