# Data mechanics website

Im migrating an old wordpress website, its export is here: old_word_press_export/datamechanics.WordPress.2026-10-18.xml
We are going to completly recriate the site, the only thigs we are keeping from the old one are the blog posts and the logo.

Use the the skills in this repo for makign a better design: Emil Kowalski and Impecable.
It runs on a Linux server. The deployment scripts and notes (`deploy/`, `docs/deploy.md`, `docs/postgres-migration.md`) stay on the maintainer's machine: git ignores them, and the public repository says nothing about the server.

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
- **Run the ETL** with `python manage.py etl` (every metric module, in the order of `providers.MODULES`) or `python manage.py etl worldbank.gdp` (one module). The conflicts' modules (`providers.CONFLICT_MODULES`) never run in a plain `etl`: World War II is static, so the weekly refresh leaves it alone; they load only when named, as every deploy does.
- **The website reads only the database**, never a provider's API. Keep transformations on read small: reshaping and ranking (`metrics/queries.py`).
- **Table names**: country data starts with `geo_` and names its grain, e.g. GDP by country and year is `geo_gdp_country_year`. The models live in `geo/models.py`. Political data starts with `pol_` (`pol_party`, `pol_administration`); its models live in `politics/models.py`.
- **Country dimension**: `geo_country` (codes, names, shapes from Natural Earth, plus a World row with `is_aggregate`). Every fact table points at it. Map other sources' codes to it in `providers/load.py` (`_ALIASES`, e.g. IMF `UVK` → `XKX`).
- **One page per metric**: each metric (GDP, life expectancy, ...) has its own page with charts. Metrics are defined once, in `metrics/catalog.py`.
- **Database**: PostgreSQL 18 in Docker (`docker-compose.yml`).

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
  - a year slider under it (`templates/partials/year_slicer.html`, `static/js/lib/year-slicer.js`, shared with Politics mode). It limits the line chart, its table and its image, kept in the URL as `from` and `to`; the map keeps its own year.

Charts follow the dataviz skill: one axis, colours assigned to a country when it is added and kept while it stays, a legend for two or more series, a table view ("Show the numbers"), tooltips on hover.

Missing years: a gap of up to 25 years is drawn as the straight line between its ends, with a dot on each real value at the ends; a longer gap stays open, and a value alone between open gaps gets a dot (`BRIDGE` in `static/js/lib/gaps.js`, used by the line chart and the Politics chart). Tooltips show real values only.

Every chart has a quiet "Save as image" button in its well (`templates/partials/save_image.html`). It saves a 1080 × 1350 PNG for Instagram, with the source and a semi-transparent watermark: "Data Mechanics (Follow @datamechanics)" (`paintBrandName` in `static/js/lib/chart-image.js`, used by the reels too). Each chart module gives it a `*ImageParts` helper that draws the chart again off screen. The Politics timeline saves as several images when its rows do not fit one (`static/js/lib/timeline.js`); rows keep their size.

Politics images carry the country's round flag before the title; the page's note about terms without data stays off them.

Politics charts also make videos: MP4, 30 frames a second, as 1080 × 1920 Instagram reels or 1920 × 1080 for YouTube and LinkedIn.
The site draws every frame (`static/js/lib/reel.js`), so a video looks like the site's chart.
Both shapes tell the same story; `FORMATS` in `reel.js` holds what differs (sizes, zooms, safe areas, fonts).
`?reel=1` on a Politics page previews a reel, `?reel=1&format=wide` the wide video.
`.venv/bin/python tools/reel.py "<page address>"` records it with Playwright and ffmpeg; `--wide` records the wide one.
The page's metric, measure and years (`from`, `to`) choose what the reel shows.
The title carries the unit the values are in (`measured_in` on each series in `metrics/catalog.py`, translated in the context "measured in").
Only the first term opens with a start card, to show where the line begins; each term ends with a card that leads with its change, large, over the value it ended at.
Under the chart, the timeline row of the term the line is in counts along with it.
When the country's line ends, the comparison group's dashed line draws itself the same way, but quieter.
This pass compares values, not changes: a fast rise can still end below the group.
At each term's end on it, a card gives the country's value and the group's in that year, and the timeline row under the chart gives them too ("At end of term").
Once the card is up, a green outline draws itself around the better value for the metric, the value turns green, and a check pops onto the outline's corner (`paintWinner` in `reel.js`). Neither wins when the metric has no better direction or the two read the same.
A ranking by president, in the chart's place, closes the reel: by change per year, as on the page. With a group it ranks instead by how far ahead of the group each leader left the country at the end of their last term (`lead` from `at_the_end` in `politics/queries.py`), with the year and both values; the better value is green, with the cards' check.
Its pace is `TIME` in `reel.js`, and a reel's layout keeps clear of the bands Instagram covers (`safe` in its format).

## Conflicts

The Conflicts section (`/conflicts/`) gives each war its own page. World War II is the first (`/conflicts/world-war-ii/`), inspired by Neil Halloran's documentary "The Fallen of World War II". The page credits him.

- **Its own database.** The conflicts tables live in a second PostgreSQL database on the same server, `conflicts` (`POSTGRES_CONFLICTS_DB`), with one schema per conflict: World War II is `ww2`. `conflicts/routers.py` sends the `conflicts` app there. Nothing in it points at `geo_country`: the states, names and borders of 1937–1945 are not today's. A state lists its modern successors as ISO alpha-2 codes, without a link.
  Create it once (`docker exec datamechanics-db createdb -U <user> conflicts`), then `python manage.py migrate --database conflicts`.
- **Static data.** The World War II tables are not refreshed: the weekly `etl` skips `CONFLICT_MODULES`, the deaths loader is pinned to one Wikipedia revision, and the other sources are the repository's own CSVs and CShapes 2.0, which does not change. A deploy reloads them from those files; nothing else does.
- **Tables** (`conflicts/models.py`): `ww2.state` (the dimension: states, dominions, colonies, puppet states, with their flag), `ww2.state_side` (Allies or Axis, from when to when), `ww2.deaths_state`, `ww2.battle`, `ww2.event` and `ww2.border`. A model's `db_table` is `ww2"."<table>`; `etl_load` records it as `ww2.<table>`.
- **Sources**:
  - States, sides, battles and events are compiled by hand into `data/ww2/*.csv` and loaded by `providers/curated/ww2_*.py`. Each battle row names the Wikipedia revision its casualties come from: killed, wounded, missing and captured per side, from the lowest to the highest estimate in the infobox, civilians left out.
  - Deaths by state: Wikipedia's table "World War II casualties", pinned to one revision (`providers/wikipedia/ww2_deaths.py`).
  - Borders: CShapes 2.0 (`providers/cshapes/ww2_borders.py`), CC BY-NC-SA 4.0: free while the site stays non-commercial, never committed (the ETL downloads it). It draws borders as the law saw them, not wartime occupations. A colony without a state of its own names its ruler in `data/ww2/territories.csv`.
  - Never use sources whose terms forbid reuse: the Commonwealth War Graves Commission, Correlates of War (no redistribution without written permission), uboat.net, naval-history.net, or Halloran's own data.
- **Flags**: `media/conflicts/ww2/flags/<code>.svg` (4:3), with their Commons file, licence and author in `data/ww2/flags.csv`. Credit every flag that is not in the public domain. No flag with a fascist symbol: Germany's flag is the user's own drawing without the swastika (an iron cross in the white disc), Croatia's Ustaše state a plain "NDH" badge, Japan the Hinomaru (never the Rising Sun).
- **Sides**: a state takes the colour of the side it fought on that day (`ww2.state_side`, from Wikipedia's list of declarations of war); a state without sides of its own takes its ruler's. In the whole-war view it takes the side it fought on longest. Allies are #3987e5 and the Axis #d95926; soldiers are #3987e5 and civilians #c98500. Both pairs pass the dataviz palette script.
- **Casualties by country** (`static/js/lib/casualties-chart.js`): an ECharts column chart with the metrics pages' country picker (up to 12 countries; the main belligerents by default, `MAIN_COUNTRIES` in `static/js/ww2-page.js`) and two checkable pills, Soldiers and Civilians (both on by default, one always stays on). A column is the lowest estimate, with a faint segment up to the highest; with both parts shown, soldiers are the lowest military estimate and civilians the rest of the lowest total (`columnOf`). The state lives in the URL as `?countries=` and `?show=`.
- **Battle map** (`static/js/lib/war-map.js`, `war-timeline.js`): a dot per battle in the winner's colour, a little larger for a larger battle. Hover shows the battle's card; a press pins it, with the battle's picture and its Wikipedia link. The wheel zooms around the pointer (up to 10×), two fingers pinch, a drag pans, a double click or the "Whole map" button resets. The timeline under the map holds a lane per theatre; it plays the war from 7 July 1937 to 2 September 1945, and the map shows the borders and sides of the day.
- **Region tabs** (Whole war, Europe and Africa, Asia and the Pacific) filter everything: the map's view and dots, the timeline's lanes, and the lists. A battle's region comes from its theatre (`Battle.region`); an event's from `region` in `data/ww2/events.csv` (`world` shows under every tab).
- **Battle by battle** (`static/js/lib/battle-list.js`): two tabs. Battles: the Politics timeline's rows for the battles in the order they began, with the battle's picture (hover it for the battle's card), its name (a button that shows the battle on the map), the flags of both sides, each side's casualties, a pie of the two, the result and a Wikipedia link. On phones the row stacks its parts beside the rail, without picture or pie, and the map's card opens under the map inside its well. Other events: the dated events with their kind and link.
- **Battle pictures**: `media/conflicts/ww2/battles/<QID>.jpg` (640 px wide JPEGs from Wikimedia Commons), with the file, licence and author in `data/ww2/battle_images.csv`. Only public domain, CC0, CC BY and CC BY-SA pictures; a picture that is not public domain shows its credit on the card and the list says where the pictures come from.

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
- **Follow the office that governs**: the president in Brazil, France and the United States, the chancellor in Austria and Germany (their presidents have little power). Germany starts with the Federal Republic in 1949, so the Nazi dictatorship is not in Politics mode. Austria starts with the Second Republic in April 1945, which leaves out Austrofascism and the Nazi annexation. France starts with the Fifth Republic in 1959: the Fourth Republic's presidents had little power, and Vichy is left out. Each role in the CSV is in `ROLES` in `politics/offices.py`, which names its office. The current leader's office picks the page's words in `OFFICES` ("chancellor by chancellor", "By chancellor"). Text shared by every office says "term" or "leader", never "president".
- **Metrics**: `politics/metrics.py` lists the metrics Politics mode shows, grouped into tabs. Add a metric there once it has country data.
- **Comparison groups** (`politics/comparison.py`): a dashed line, and a small change under each term, measure the country against one group over the same years.
  The groups are World, BRICS (its five founding members), the G7 and the G20. The page shows one at a time, World by default, kept in the URL as `?compare=`.
  `?compare=none` compares with nothing: the page and the reel then look as they did before groups existed.
  The saved images and the reel name the group in their subtitle: "Brazil, president by president, compared with G7 countries" (`compared` in `GROUPS`, one text per group so each language can word it).
  World is the source's own World value; a source without one has no World comparison.
  A group's value is the average of its members. A year counts only when every member has data.
  The data view lists the groups with values for the series (`comparable`); the dropdown marks the others "(no data)". A chosen group without values stays chosen, and the series shows no comparison.
  A total (`total=True` on the series in `metrics/catalog.py`, like GDP) has no comparison, and the dropdown hides: a group's total would dwarf the country's line, and the two would not compare.
  The group's line may widen the value axis to 3 times the country's own range on each side (`GROUP_REACH` in `static/js/lib/term-chart.js`). Beyond that it runs off the chart.
- **A year belongs to the leader in office on 1 July.** On the chart, the stretch of line that ends at a year belongs to that leader. A presidency's change runs from the year before its first year to its last year with data.
- **One window of years** (the page's year slider, or a president pressed in the timeline) limits the chart's zoom, the timeline, the rankings and the table. The data view takes it as `?from=&to=`; a presidency that starts before the window is measured from the window's first year.
- **Rankings by party and by president** (`politics/queries.py`, `grouped_changes`): a presidency counts for the party it ended in, and a president's non-consecutive terms count together. Only years with data count. Growth that multiplies (series on a log scale, like GDP) compounds: the total multiplies the changes, and the average per year is the rate that gives the total. Other changes add up, and the average divides by the years. Best first; the highest first where no direction is better.
- **One colour per presidency: the party it ended in.** A leader who changed party in office (Bolsonaro: PSL, then none, then PL) is drawn and named in the tooltip in the final party's colour. The timeline lists every party they held, and "Show the numbers" gives the party of each year.
- **Colours**: each party's colour comes from Wikipedia's timeline of the country's presidents or chancellors, lightened where needed to reach 3:1 against the chart (the CDU's black becomes #6e6e6e). Green and red mean good and bad change for the metric. They appear only in Politics mode, always beside an arrow. A fall's change also starts with a minus sign (`change_summary` in `politics/queries.py`), so the direction never rests on the arrow and the colour alone.
