# <img src="static/brand/logo.svg" alt="" width="40" height="40" align="top"> Data Mechanics

Free public statistics on every country: world maps, charts over time and CSV downloads, with the source of every number. An open-source alternative to paywalled statistics portals, plus a blog on data, charts, Python and BI.

Live at https://data-mechanics.com.

## What is in it

- **Metrics**: 49 of them in 10 categories, from GDP, productivity and public finances to life expectancy, literacy, corruption, democracy, air pollution and food. Each one has its own page with a map, a line chart, a ranking and a download.
- **Politics mode**: one page per country with every metric coloured by the leader in office, and the change during each term, as a timeline and ranked by party and by leader. Brazil, France and the United States follow their presidents, Austria and Germany their chancellors. Brazil also has its party positions, where three expert surveys place its parties on the economy and on social values, and its seats in Congress, party by party or grouped into left, centre and right, in the Chamber of Deputies and the Senate, today and as the 2026 election left them.
- **Sources**: the World Bank, the IMF, the UNDP, Our World in Data (V-Dem, the FAO, the World Inequality Database, the Penn World Table, Transparency International and others), Natural Earth for country borders, the open-data APIs of Brazil's Chamber of Deputies and Senate for the members in office, the electoral court (TSE) for the members just elected, and a survey of Brazilian political scientists for left and right. Leaders and parties are compiled by hand from Wikipedia into `data/politics/`, with party logos from Wikimedia Commons.
- **Exports**: every chart saves as an image for Instagram, and Politics charts, the party positions and the seats in Congress also as videos for Instagram Reels, YouTube and LinkedIn (`tools/reel.py`).
- **Blog**: posts written by me (Klaus Jürgen Folz).
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

# Then fill in the secrets in .env.
cp .env.example .env

# PostgreSQL 18.
docker compose up -d
.venv/bin/python manage.py migrate

# Downloads every source, a few seconds each.
.venv/bin/python manage.py etl
.venv/bin/python manage.py runserver
```

Run the tests with `.venv/bin/python manage.py test`.

## Licence

The code is licensed under the [GNU Affero General Public License v3.0](LICENSE). The data belongs to its sources and keeps their terms: every page and download names its source.

## Note to self
.venv/bin/python tools/reel.py "https://data-mechanics.com/pt/politics/brazil/?metric=government-debt"