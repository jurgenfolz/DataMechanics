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

- **One folder per data provider** in `providers/`: `worldbank/`, `imf/`, `undp/`, `owid/` (Our World in Data), `naturalearth/`.
- **One module per source** inside a provider folder (a `.py` file). The module calls the provider's API, transforms the data and writes it to PostgreSQL. The whole ETL for that source lives in the module.
- **Each module writes one table, and only one.** It replaces the table in one transaction through `providers/load.py`, which also logs the load in `etl_load`.
- **Run the ETL** with `python manage.py etl` (every module, in the order of `providers.MODULES`) or `python manage.py etl worldbank.gdp` (one module).
- **The website reads only the database**, never a provider's API. Keep transformations on read small: reshaping and ranking (`metrics/queries.py`).
- **Table names**: country data starts with `geo_` and names its grain, e.g. GDP by country and year is `geo_gdp_country_year`. The models live in `geo/models.py`.
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
