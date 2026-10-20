# Data mechanics website

Im migrating an old wordpress website, its export is here: old_word_press_export/datamechanics.WordPress.2026-10-18.xml
We are going to completly recriate the site, the only thigs we are keeping from the old one are the blog posts and the logo.

Use the the skills in this repo for makign a better design: Emil Kowalski and Impecable.
This will be hosted in a VPS in Hostinger with Ubuntu 26.04 LTS.

What will the website be:
A open source version of Statista: I will fetch data from multiple sources and provide it for free to people with beatiful charts and the possibility of exporting the data. We also will have blogposts, focus on data, insights, charts, data science, AI and python.


Website style: Cyberpunk
Database: PostgreSQL

### Comments and docstrings

- **Never start a docstring line with `#*`, `#!` or `#?`.** Pylance shows the docstring as the hover tooltip, and a
  marker at the start of a line breaks it. Put a warning in a `#!` comment in the body, under the docstring.
- **Break a line only where a sentence ends**, never in the middle of one. This holds for comments and docstrings.
- **Use simple language.** Short sentences, one idea each. No long paragraphs that are hard to follow: split them or
  cut them.


## Never commit

Claude never commits, under any circumstance, in any repo, even when asked. That covers every command that writes a
commit: `git commit` (`--amend` too), `git merge`, `git rebase`, `git cherry-pick` and `git revert`. Leave every
change uncommitted in the working tree: the user reviews it and commits it.

## Principles

### Use SOLID principles
• Single Responsibility Principle (SRP): A class should have only one reason to change, meaning it should perform only one clear job.
• Open/Closed Principle (OCP): Software entities should be open for extension but closed for modification. You add new features by writing new code rather than changing old code.
• Liskov Substitution Principle (LSP): Child classes must be able to replace their parent classes without breaking the program.
• Interface Segregation Principle (ISP): Clients should not be forced to depend on methods they do not use. Break large interfaces into smaller, specific ones.
• Dependency Inversion Principle (DIP): High-level modules should depend on abstractions, not on concrete implementations

### Use the YAGNI principle (You are no gonna need it)
• Delay implementation: Never write code or build abstractions today based only on a guess that you might need them in the future.
• Fight over-engineering: Prevent wasted time and bloated code by focusing strictly on present, verified requirements.
• Iterate instead: Build the simplest working solution now and rely on refactoring to add features later when real needs emerge.

### Use the DRY Principle (Dont repeat yourself)
• Single Source of Truth: Business rules, validation checks, and data definitions should live in one place. If the rule changes, you only update it in that single location.
• Knowledge vs. Code: Repeating identical lines of code is fine if they represent different domain concepts. The violation happens when the same business logic is copied across multiple files or modules.
• Origin: Introduced as part of clean code philosophy and applied broadly to source code, database schemas, test plans, and documentation

### Use the KISS principle (Keep it simple, Stupid)
• Readability: Another developer should understand what your code does without tracing through endless layers of abstraction.
• Maintainability: Simpler code has fewer bugs, is easier to test, and is safer to change when requirements shift.
• No over-engineering: You avoid writing complex, multi-layered frameworks or adding "just-in-case" features for problems you do not have yet
## Evidence before claims

Every claim about how something behaves rests on evidence checked in the current session. That covers Power BI and
Fabric file formats, Microsoft APIs, Power BI Desktop, the service, and the code in every Measure Killer repo.

- **Check, then state.** Read the code path, run it, or open a real file or captured payload. A script that runs the
  real classes on real data is stronger than reading the code. Sample files: the `measurekiller_testing_files` repo,
  and core's `tests/power_bi_files/` and `tests/report_files/`.
- **Trust nothing unchecked.** Comments, docstrings, commit messages, tests, earlier answers and memory can all be
  wrong. Verify them like any other claim. `git log -S` and `git log --all -G` often show why code looks the way it
  does.
- **Keep verified and inferred apart.** Label an inference as one. Give counts and sources (file, commit, URL) rather
  than "usually" or "always".
- **When in doubt, ask or research.** Ask the user, or look it up: Microsoft Learn, and the Fabric item schemas in
  `github.com/microsoft/json-schemas`. Quote what you find with its date. If the docs are silent, say so.
- **Ask for tests when evidence is missing.** The user can build reports, measures and models in Power BI Desktop or
  the service. Propose numbered steps on copies of existing files, and say what each step settles. Read the saved
  files yourself afterwards. Desktop's preview settings change what a save writes: with "Store PBIX reports using
  enhanced metadata format (PBIR)" on, a legacy `.pbix` becomes PBIR on save.
- **Correct yourself.** When new evidence contradicts an earlier claim, say so plainly and update the conclusion.


## Data design

### Architecture

- **One folder per data provider** in `providers/`: `worldbank/`, `imf/`, `undp/`, `owid/` (Our World in Data), `naturalearth/`, and `curated/` for tables we compile by hand as CSV files in `data/`.
- **One module per source** inside a provider folder (a `.py` file). The module calls the provider's API, transforms the data and writes it to PostgreSQL. The whole ETL for that source lives in the module.
- **Each module writes one table, and only one.** It replaces the table in one transaction through `providers/load.py`, which also logs the load in `etl_load`.
- **Run the ETL** with `python manage.py etl` (every module, in the order of `providers.MODULES`) or `python manage.py etl worldbank.gdp` (one module).
- **The website reads only the database**, never a provider's API. Keep transformations on read small: reshaping and ranking (`metrics/queries.py`).
- **Table names**: country data starts with `geo_` and names its grain, e.g. GDP by country and year is `geo_gdp_country_year`. The models live in `geo/models.py`. Political data starts with `pol_` (`pol_party`, `pol_administration`); its models live in `politics/models.py`.
- **Country dimension**: `geo_country` (codes, names, shapes from Natural Earth, plus a World row with `is_aggregate`). Every fact table points at it. Map other sources' codes to it in `providers/load.py` (`_ALIASES`, e.g. IMF `UVK` → `XKX`).
- **One page per metric**: each metric (GDP, life expectancy, ...) has its own page with charts. Metrics are defined once, in `metrics/catalog.py`.
- **Database**: PostgreSQL 18 in Docker for now (`docker-compose.yml`). Moving it to the VPS: `docs/postgres-migration.md`.

### Search tags

Every metric has these tags, from broad to narrow. Search matches them (`metrics/search.py`), and the metric page shows them.

| Tag | Required | Example: GDP |
|---|---|---|
| Category | yes | Economy |
| Subcategory 1 to 4 | Subcategory 1 yes, the rest when useful | GDP, National accounts |
| Granularity 1 to 3 | Granularity 1 yes | Country, Year |

In code: `Tags(category, subcategories=(...), granularity=(...))` in `metrics/catalog.py`.

## Plot and style guidelines for metric pages

Every metric page has, in this order:

1. **Title.**
2. **Description**: one paragraph in simple words. Say what the metric is, how it is measured and who measures it. This is what makes the data trustworthy.
3. **Source** at the top of every chart, as an accessible link, with the source's update date and our fetch date.

### Data by country

These guidelines are soft: a metric may need other charts or another layout.

Country data gets two families of charts:

- **Map**: whenever possible, a shape map with country borders (like a Power BI shape map). Colour it good / mid / bad when the metric has a better direction (red worse, grey the median country, blue better). Use one colour ramp when neither direction is better (GDP, population). When the data is yearly, add a year dropdown.
- **Any other chart that fits the data**, usually a line chart over time, with:
  - a country dropdown to choose the countries;
  - an "All world" option where the source has a world value, listed in the dropdown like a country;
  - each country's flag in the dropdown and as the line's data label (flags are SVGs in `media/flags/4x3` and `media/flags/1x1`, named by ISO 3166-1 alpha-2 code).

Charts follow the dataviz skill: one axis, colours assigned to a country when it is added and kept while it stays, a legend for two or more series, a table view ("Show the numbers"), tooltips on hover.

Missing years: a gap of up to 25 years is drawn as the straight line between its ends, with a dot on each real value at the ends; a longer gap stays open, and a value alone between open gaps gets a dot (`BRIDGE` in `static/js/lib/gaps.js`, used by the line chart and the Politics chart). Tooltips show real values only.

Every chart has a quiet "Save as image" button in its well (`templates/partials/save_image.html`). It saves a 1080 × 1350 PNG for Instagram, with the source and a semi-transparent watermark (`static/js/lib/chart-image.js`). Each chart module gives it a `*ImageParts` helper that draws the chart again off screen. The Politics timeline saves as several images when its rows do not fit one (`static/js/lib/timeline.js`); rows keep their size.

## Languages

The site speaks English, German and Portuguese (Brazilian). English lives at the root, German under `/de/`, Portuguese under `/pt/`.

- **English is the source.** Write every visible text in English and mark it: `{% translate %}` or `{% blocktranslate %}` in templates, `gettext_lazy` in module-level Python (the catalog), `gettext` in functions, and the global `gettext`, `ngettext` and `interpolate` in `static/js` (Django's catalog, loaded by `base.html`).
- **Keys stay English.** Slugs, fields, category keys, the CSV and the JSON keys do not change with the language. Category names on the page come from `CATEGORY_LABELS` in `metrics/catalog.py`.
- **Update the translations** after adding or changing a text:
  `python manage.py makemessages -l de -l pt --ignore='staticfiles/*' --ignore='static/vendor/*' --ignore='media/*' --ignore='old_word_press_export/*' --ignore='docs/*'`,
  the same with `-d djangojs` for `static/js`, then fill every new `msgstr` in `locale/de` and `locale/pt`, then `python manage.py compilemessages --ignore=.venv`.
  A test fails while any entry is empty or fuzzy. Every deploy compiles the `.po` files again on the server.
- **Numbers and dates** follow the language: `metrics/formatting.py` hands its unit rules, with the language's words and decimal marks, to the browser. Date formats are in `config/formats/<language>/formats.py`.
- **Country names** come from Natural Earth in all three languages (`name`, `name_de`, `name_pt` in `geo_country`). Fix a name in `NAME_FIXES` in `providers/naturalearth/countries.py`; Portuguese names use Brazilian spelling.
- **Blog posts stay in English.** Their pages mark them `lang="en"`.

## Politics mode

Politics mode shows one country at a time, leader by leader (`/politics/<country>/`).

- **Data**: leaders, parties and dates are compiled by hand from Wikipedia into `data/politics/<country>/administrations.csv` and `parties.csv`. Party logos go in `media/politics/<country>/`, with their licence and author in `parties.csv`. Credit every logo that is not in the public domain.
- **One row per stretch in office under one party.** A leader who changes party mid-term gets a row per party. A party that is only renamed stays one party, under its name at the end of the term (LREM, renamed Renaissance in 2022, is RE). A merger into a new party is a change: Chirac has a row for the RPR and one for the UMP. Consecutive rows of one leader make one presidency.
- **Add a country**: add its folder to `data/politics/` and to `COUNTRIES` in `providers/curated/__init__.py`, then run `python manage.py etl curated.parties curated.administrations`. Every deploy runs this too.
- **Follow the office that governs**: the president in Brazil, France and the United States, the chancellor in Germany (its president has little power). Germany starts with the Federal Republic in 1949, so the Nazi dictatorship is not in Politics mode. France starts with the Fifth Republic in 1959: the Fourth Republic's presidents had little power, and Vichy is left out. Each role in the CSV is in `ROLES` in `politics/offices.py`, which names its office. The current leader's office picks the page's words in `OFFICES` ("chancellor by chancellor", "By chancellor"). Text shared by every office says "term" or "leader", never "president".
- **Metrics**: `politics/metrics.py` lists the metrics Politics mode shows, grouped into tabs. Add a metric there once it has country data.
- **A year belongs to the leader in office on 1 July.** On the chart, the stretch of line that ends at a year belongs to that leader. A presidency's change runs from the year before its first year to its last year with data.
- **One window of years** (the page's year slider, or a president pressed in the timeline) limits the chart's zoom, the timeline, the rankings and the table. The data view takes it as `?from=&to=`; a presidency that starts before the window is measured from the window's first year.
- **Rankings by party and by president** (`politics/queries.py`, `grouped_changes`): a presidency counts for the party it ended in, and a president's non-consecutive terms count together. Only years with data count. Growth that multiplies (series on a log scale, like GDP) compounds: the total multiplies the changes, and the average per year is the rate that gives the total. Other changes add up, and the average divides by the years. Best first; the highest first where no direction is better.
- **One colour per presidency: the party it ended in.** A leader who changed party in office (Bolsonaro: PSL, then none, then PL) is drawn and named in the tooltip in the final party's colour. The timeline lists every party they held, and "Show the numbers" gives the party of each year.
- **Colours**: each party's colour comes from Wikipedia's timeline of the country's presidents or chancellors, lightened where needed to reach 3:1 against the chart (the CDU's black becomes #6e6e6e). Green and red mean good and bad change for the metric. They appear only in Politics mode, always beside an arrow.
