# <img src="static/brand/logo.svg" alt="" width="40" height="40" align="top"> Data Mechanics

Free public statistics on every country: world maps, charts over time, rankings and CSV downloads, with the source of every number. An open-source alternative to paywalled statistics portals, plus a blog on data, charts, Python and BI.

Live at https://data-mechanics.com.

## What is in it

- **Metrics**: 125 of them in 10 categories, from GDP, productivity and public finances to life expectancy, literacy, corruption, democracy, air pollution and food. Each one has its own page with a map, a line chart with a year slider, a sortable ranking of every country (with a continent filter) and a download. Long-run series reach back to the 1800s where Our World in Data has them.
- **Compare**: any two metrics of one country on one chart, each on its own axis.
- **Politics mode**: one page per country with every metric coloured by the leader in office, and the change during each term, as a timeline and ranked by party and by leader, measured against the World, BRICS, the G7 or the G20. Brazil, France and the United States follow their presidents, Austria and Germany their chancellors, Italy and the United Kingdom their prime ministers. Each country also has its party positions (where expert surveys place its parties on the economy and on social values), its seats in parliament (party by party or grouped into left, centre and right; Brazil's also as the 2026 election left them) and its crime over time, by state where the country publishes it. Missing a country? The last card of the Politics page opens a request form.
- **World events**: about 55 wars, crises, treaties and other events, compiled from Wikipedia, that any line chart can mark.
- **Conflicts**: a page per war, starting with World War II: deaths by country, a map of the battles that plays through the war, and the battles one by one, with their casualties and sources.
- **Sources**: the World Bank, the IMF, the UNDP, the ILO, Our World in Data (V-Dem, the FAO, the World Inequality Database, the Penn World Table, Transparency International and others) and Natural Earth for borders. For parliaments, the open-data APIs of Brazil's Chamber of Deputies and Senate, abgeordnetenwatch.de for the Bundestag, the Austrian Parliament, the @unitedstates project, the Assemblée nationale and the Sénat, the Camera and the Senato, and the UK Parliament's Members API; the electoral court (TSE) for Brazil's members just elected; expert surveys (PREPPS, CHES, the Global Party Survey, Bolognesi and others) for party positions and left and right; each country's police or statistics office for crime. Leaders and parties are compiled by hand from Wikipedia into `data/politics/`, with party logos and flags from Wikimedia Commons. Every page names its source and its licence.
- **Exports**: every chart saves as an image for Instagram or for LinkedIn, X and slides. Every metric page makes a bar chart race, and Politics charts, the party positions, the seats in parliament and the crime maps make videos too, for Instagram Reels, YouTube and LinkedIn (`tools/reel.py`).
- **Blog**: posts written by me (Klaus Jürgen Folz).
- **Languages**: English, German and Portuguese. German lives under `/de/`, Portuguese under `/pt/`; the translations are in `locale/`.

## How it works

- `providers/` holds the ETL: one folder per data provider, one module per source, and each module writes one table.
- `geo/` defines the tables: the `geo_country` dimension, the states with their borders, and one `geo_<metric>_country_year` table per metric.
- `metrics/` holds the metric catalog (texts, tags and series), the queries and the pages. The site reads only the database.
- `politics/` holds Politics mode: the `pol_*` tables, the list of metrics it shows (`politics/metrics.py`), the party positions, the parliaments, the crime series and its pages.
- `compare/`, `events/` and `conflicts/` hold the Compare section, the world events and the war pages. The conflicts live in a second database with one schema per war.
- `tools/` holds the scripts that fetch and compile the hand-curated data (party positions, crime, state flags) and record the videos.
- `blog/` holds the posts; `pages/` holds the home page.
- Django and PostgreSQL on the server, ECharts in the browser.

## Run it locally

You need Python 3.13 or newer and Docker.

```
python -m venv .venv
.venv/bin/pip install -r requirements.txt

# Then fill in the secrets in .env.
cp .env.example .env

# PostgreSQL 18, and a second database for the conflicts.
docker compose up -d
docker exec datamechanics-db createdb -U datamechanics conflicts
.venv/bin/python manage.py migrate
.venv/bin/python manage.py migrate --database conflicts

# Downloads every source, a few seconds each. The conflicts load only when named.
.venv/bin/python manage.py etl
.venv/bin/python manage.py etl curated.ww2_states curated.ww2_sides wikipedia.ww2_deaths curated.ww2_battles curated.ww2_events cshapes.ww2_borders
.venv/bin/python manage.py runserver
```

Run the tests with `.venv/bin/python manage.py test`.

## Licence

The code is licensed under the [GNU Affero General Public License v3.0](LICENSE). The data belongs to its sources and keeps their terms: every page and download names its source.

## Note to self
.venv/bin/python tools/reel.py "https://data-mechanics.com/pt/politics/brazil/?metric=government-debt"
