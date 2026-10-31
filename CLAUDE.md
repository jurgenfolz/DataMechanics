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

- **One folder per data provider** in `providers/`: `worldbank/` (its `api.py` reads any World Bank database: WDI by default, the Worldwide Governance Indicators as database 3), `imf/`, `undp/`, `owid/` (Our World in Data), `ilo/` (ILOSTAT's SDMX API), `naturalearth/`, `camara/` and `senado/` (Brazil's Congress), `tse/` (Brazil's electoral court), `abgeordnetenwatch/` (Germany's Bundestag), `parlament_at/` (Austria's Parliament), and `curated/` for tables we compile by hand as CSV files in `data/`.
- **One module per source** inside a provider folder (a `.py` file). The module calls the provider's API, transforms the data and writes it to PostgreSQL. The whole ETL for that source lives in the module.
- **Each module writes one table, and only one.** It replaces the table in one transaction through `providers/load.py`, which also logs the load in `etl_load`. The parliament members' tables, `pol_deputy` and `pol_senator`, hold several countries: each of their modules replaces only its own country's rows.
- **Run the ETL** with `python manage.py etl` (every metric module, in the order of `providers.MODULES`) or `python manage.py etl worldbank.gdp` (one module). The conflicts' modules (`providers.CONFLICT_MODULES`) never run in a plain `etl`: World War II is static, so the weekly refresh leaves it alone; they load only when named, as every deploy does.
- **The website reads only the database**, never a provider's API. Keep transformations on read small: reshaping and ranking (`metrics/queries.py`).
- **Table names**: country data starts with `geo_` and names its grain, e.g. GDP by country and year is `geo_gdp_country_year`. The models live in `geo/models.py`. Political data starts with `pol_` (`pol_party`, `pol_administration`); its models live in `politics/models.py`.
- **Country dimension**: `geo_country` (codes, names, shapes from Natural Earth, plus a World row with `is_aggregate`). Every fact table points at it. Map other sources' codes to it in `providers/load.py` (`_ALIASES`, e.g. IMF `UVK` → `XKX`).
- **One page per metric**: each metric (GDP, life expectancy, ...) has its own page with charts. Metrics are defined once, in `metrics/catalog.py`.
- **Long-run series** come from Our World in Data where a source reaches further back than the World Bank's 1960: life expectancy (`owid.life_expectancy`, to the 1800s, with women and men from 1950), child mortality (`owid.child_mortality`, to 1751; OWID gives it per 100, the loader scales it to per 1,000), GDP per capita since 1820 (Maddison), years of schooling since 1870 (Lee and Lee), voter turnout (V-Dem, election years only), food supply, oil and coal production. `grapher.load_charts` takes a `scale` per field.
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

- **All countries ranked** (`static/js/lib/rank-table.js`): under the line chart, every country with a value in one year in a table, its rank in the world that year, its flag and name, and its value. A continent select (Natural Earth's continents, `?continent=`) hides the others, and every column sorts; the rank never changes with either. Its year select is its own (`?rank=`, left out when it is the latest).

Charts follow the dataviz skill: one axis, colours assigned to a country when it is added and kept while it stays, a legend for two or more series, a table view ("Show the numbers"), tooltips on hover.

Missing years: a gap of up to 25 years is drawn as the straight line between its ends, with a dot on each real value at the ends; a longer gap stays open, and a value alone between open gaps gets a dot (`BRIDGE` in `static/js/lib/gaps.js`, used by the line chart and the Politics chart). Tooltips show real values only.

Every chart has a quiet "Save as image" button in its well (`templates/partials/save_image.html`). It opens a menu of two shapes with their sizes (`SIZES` and `bindSaveButton` in `static/js/lib/chart-image.js`): portrait, 1080 × 1350 for Instagram, and wide, 1920 × 1080 for LinkedIn, X and slides. The chart's save function gets the shape, and a wide image's file name ends in `-wide`. It saves a PNG with the source. Images and videos carry no watermark over the chart: a line under their title (and a video's explanation) names the site, the gear logo then "Data Mechanics - @datamechanics", a little faded (`paintBrandLine` in `static/js/lib/chart-image.js`). Images keep the address in gold at the foot; videos, which have no such footer, end the line with "- data-mechanics.com". Each chart module gives it a `*ImageParts` helper that draws the chart again off screen. The Politics timeline saves as several images when its rows do not fit one (`static/js/lib/timeline.js`); rows keep their size.

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
What every video shares (its two shapes, its title and the site's line under it, its source, its card panel, its easing) is in `static/js/lib/reel-frame.js`.

## Bar chart race

Every metric page makes a video too (`static/js/lib/race-reel.js`): `?reel=1` plays it over the page and `tools/reel.py` records it, in the reels' two shapes.
Year by year the countries' bars grow and swap places, the highest value first; the bars slide between ranks, count their values and rise in from under the last row when a country enters.
`&top=20` ranks the twenty highest countries of each year (any number works; the World row is left out); without it, or with `top=0`, the race runs between the countries chosen on the page, each bar in its chart colour.
The year slider's years bound it (`from` and `to`), and a year's pace shrinks with the number of years (`TIME` in the module).
What every video shares, including the stage that plays it and hands frames to the recorder (`presentReel`), is in `static/js/lib/reel-frame.js`.

## Compare

The Compare section (`/compare/`) puts up to two metrics of one country on one line chart, the first on the left axis and the second on the right.

- **No data of its own.** It reads each metric's `data.json`, the same file the metric page uses, so a new metric in `metrics/catalog.py` appears in its selects by itself.
- **One measure per select**: a series of a metric, named `<slug>` for the first series and `<slug>:<field>` for the others. The URL keeps the state: `?country=BRA&left=gdp-per-capita:ppp&right=life-expectancy&from=&to=`, and `right=none` leaves one metric.
- **The country is single select**, with the World first where a source has it. Defaults are in `compare/views.py`.
- **Colours follow the side**: the left line is #3987e5 and the right #d95926. Each select starts with its line's colour, and each axis names what its values are in (`measured_in`), after the same colour.
- **Two axes mislead easily**, so the page says under the chart that where the lines cross means nothing.
- Each chosen metric's source line sits above the chart, its CSV under it, and its page in the rail. The chart, its table, its year slider and its image are in `static/js/compare-page.js` and `static/js/lib/compare-chart.js`.

## World events

Every line chart (metric pages, Politics, Compare) can mark world events: wars, crises, treaties, the pandemic.

- **The catalog** is `events/catalog.py`: about 55 events compiled by hand from Wikipedia, each with a date, a kind, a short title (at most 36 characters: it sits on the chart), a one-sentence summary and its Wikipedia article. A span (a war, a boom) has an `end`, or `ongoing=True` while it goes on. Titles and summaries are `gettext_lazy`, translated like the metric catalog. `/events.json` serves them in the page's language.
- **Kinds** (`KINDS`): conflict, treaty, economy, energy, politics, health, disaster, technology. Each has an icon and a colour from the series palette in `static/js/lib/events.js` (`ICONS`, `KIND_COLORS`).
- **On the chart** (`static/js/lib/events.js`): a dashed line on the event's date (a year is a fraction, `yearOf`: 11 September 2001 is 2001.69, placed between the years' points), a chip above the plot with the icon and the title, and a faint band over a span's years. Chips stack in rows so they never overlap; the lowest row is nearest the plot. Hovering a chip shows the date, the kind and the summary. Narrow charts show the icon alone. The chosen events are listed under the chart with their dates and links, each removable.
- **The picker** (`templates/partials/event_picker.html`, the pages' `createPicker` with `eventOptions`) sits beside the country picker, lists events by date with their year, and searches titles and years. The choice lives in the URL as `?events=slug,slug`; nothing is chosen by default.
- **Images and videos** draw them too: the saved images through the chart modules, and the Politics reel pops each event in as the line reaches its date (`paintEvents` in `events.js`, used by `reel.js`).

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
- **Party names are never translated.** Every page shows a party's own name, in its country's language (`name` in `parties.csv` and `party_profiles.csv`): Partido dos Trabalhadores, Sozialdemokratische Partei Österreichs.

## Politics mode

Politics mode shows one country at a time, leader by leader (`/politics/<country>/`).

- **Data**: leaders, parties and dates are compiled by hand from Wikipedia into `data/politics/<country>/administrations.csv` and `parties.csv`. Party logos go in `media/politics/<country>/`, with their licence and author in `parties.csv`. Credit every logo that is not in the public domain.
- **One row per stretch in office under one party.** A leader who changes party mid-term gets a row per party. A party that is only renamed stays one party, under its name at the end of the term (LREM, renamed Renaissance in 2022, is RE). A merger into a new party is a change: Chirac has a row for the RPR and one for the UMP. Consecutive rows of one leader make one presidency.
- **Add a country**: add its folder to `data/politics/` and to `COUNTRIES` in `providers/curated/__init__.py`, then run `python manage.py etl curated.parties curated.administrations`. Every deploy runs this too. The Politics index's last card, "Request a country", opens a GitHub issue form (`.github/ISSUE_TEMPLATE/country_request.yml`) on the repository `GITHUB_URL` points at.
- **Follow the office that governs**: the president in Brazil, France and the United States, the chancellor in Austria and Germany, the prime minister in Italy and the United Kingdom (their heads of state have little power). Germany starts with the Federal Republic in 1949, so the Nazi dictatorship is not in Politics mode. Austria starts with the Second Republic in April 1945, which leaves out Austrofascism and the Nazi annexation. France starts with the Fifth Republic in 1959: the Fourth Republic's presidents had little power, and Vichy is left out. Italy starts with the Republic on 2 June 1946 (De Gasperi was already prime minister), which leaves out the Kingdom and Fascism; its non-party prime ministers (Ciampi, Dini, Prodi, Amato, Monti, Conte, Draghi) have an empty party. The United Kingdom starts with Attlee in July 1945, after the wartime coalition. Each role in the CSV is in `ROLES` in `politics/offices.py`, which names its office. The current leader's office picks the page's words in `OFFICES` ("chancellor by chancellor", "By chancellor"). Text shared by every office says "term" or "leader", never "president".
- **Metrics**: `politics/metrics.py` lists the metrics Politics mode shows, grouped into tabs. Add a metric there once it has country data.
- **Party compass** (`politics/compass.py`, shown as "Party positions": a name anyone understands): where expert surveys place a country's parties on two axes. It is the first tab of the country's page (`?tab=compass`), before the metric tabs. Brazil, Germany, Austria, France, Italy and the United Kingdom; a country has it when a survey places its parties (`has_compass`), so the United States, whose profiles only name its seats, has none.
  The economic axis runs from 0, the left (an active state), to 10, the right (a smaller state); the social axis from 0, progressive, to 10, conservative.
  Each survey is shown on its own, never averaged or mixed on one chart; a country shows the surveys that place its parties, in the order of `SURVEYS`, and `?survey=` keeps the choice.
  Brazil has three: PREPPS Latam 2018–2019 (the default, 17 parties measured), CHES Latin America 2020 (11) and the Global Party Survey 2019 (10).
  Germany, Austria, France and the United Kingdom have two: CHES Europe 2024 (the default; 19, 12, 11 and 21 experts, its expert-level file) and the Global Party Survey 2019. Italy has CHES only: the Global Party Survey placed Italy's coalitions, not its parties. A survey's place needs at least five experts, so France's UDI (four in the Global Party Survey) is left out. They show every party a survey placed, in parliament or not (`EUROPE` in the tool): Freie Wähler (CHES only, without a free logo, so its abbreviation stands in) and JETZT – Liste Pilz (the Global Party Survey only, out of the Nationalrat since 2019); none is inferred. Brazil's surveys hold no party beyond those shown: PREPPS's codes 351–355 are unnamed, and CHES Latin America's JB is Jair Bolsonaro himself.
  What a country's page says of it alone (the notes to keep in mind beside the general ones, and its credits) is in `CONTEXT` in `politics/compass.py`.
  `tools/party_positions.py` downloads them and writes `data/politics/<country>/positions.csv`; its docstring says how each survey's answers become the two axes.
  **Inferred places** (Brazil): a relevant party (`RELEVANT` in the tool: two or more deputies, or a senator) that a survey left out gets an inferred place, marked `inferred` in the CSV.
  A party that merged into it gives the average of the old parties (`MERGERS`: União is DEM and PSL, PRD is PTB and Patriota).
  Any other is estimated from one 2018 left-right scale of 519 Brazilian political scientists (Bolognesi, Ribeiro and Codato), by a straight-line fit on the parties both cover; the fit's R² is stored with it.
  The page marks an inferred place with a gold asterisk at its logo's corner, says so in its tooltip, and lists every inferred party under the chart with the fit's R².
  `data/politics/<country>/party_profiles.csv` holds each party: its own name, logo and its licence, colour, Wikipedia's position and ideologies (keys of `POSITIONS` and `IDEOLOGIES` in `politics/compass.py`, which translate them), and its code in Congress.
  A logo whose ink is too dark for the dark chart gets a light-ink copy in `logo_on_dark`, used only on dark grounds (`darkLogo` in `static/js/lib/compass.js`).
  The ETL loads them with `curated.party_profiles` and `curated.party_positions`; every deploy runs both.
  `static/js/lib/compass.js` draws the compass for the page, its saved image and its video (`static/js/lib/compass-reel.js`); `static/js/lib/compass-view.js` wires the tab. Tiles that would overlap are pushed apart, with a line back to their point.
  The page explains, in simple words, how each survey placed the parties and what the chart cannot say.
- **Congress** (`politics/congress.py`): the seats of each house of a country's parliament, one tab (`?tab=congress`) with a pill per house (`?house=`). Brazil, the United States, Germany, Austria, France, Italy and the United Kingdom; `HOUSES` lists each country's houses, and `PARLIAMENTS` names the tab (Brazil's and the United States' "Congress", everyone else's "Parliament").
  The members in office are loaded with the other modules and refreshed each week:
  - Brazil: the Câmara's and the Senado's open-data APIs (`providers/camara/deputies.py`, `providers/senado/senators.py`).
  - Germany, the Bundestag only: abgeordnetenwatch.de's API (`providers/abgeordnetenwatch/bundestag.py`, CC0), each member with their party today. The Bundestag's own member file lags months behind and states no licence. Never fetch bundestag.de's per-member pages: a few hundred requests lock the site's IP out. The Bundesrat seats the states' governments, not party members, so it has no half circle.
  - Austria: the Parliament's list API (`providers/parlament_at/`, CC BY 4.0), the Nationalrat by club and the Bundesrat by the party a member was elected for (its groups need five members, so its Greens and NEOS sit in none).
  - United States: the @unitedstates project's congress-legislators file (`providers/unitedstates/`, CC0), each member with the party of their current term; the House's six non-voting members are left out. Independents have no profile, so they show by the source's code, not classified.
  - France: the Assemblée nationale's and the Sénat's open data (`providers/assemblee_nationale/`, `providers/senat/`, Licence Ouverte), by parliamentary group: the Sénat gives no party, and the Assemblée's party field puts Renaissance and MoDem under one label. Each group counts for its main party; groups of several small parties (LIOT, RDSE, UCI) have profiles of their own. The Assemblée's file address names the legislature (`LEGISLATURE`): change it after a dissolution.
  - Italy: the Camera's and the Senato's SPARQL endpoints (`providers/camera_it/`, CC BY-SA 4.0, so the page shares its seat counts under CC BY-SA too; `providers/senato_it/`, CC BY 3.0), by parliamentary group, and in the Camera's mixed group by the components it names.
  - United Kingdom: Parliament's Members API (`providers/uk_parliament/`, Open Parliament Licence v3.0, whose attribution sentence the credits carry), by each member's party today, which follows the whip; independents count as no party. The Lords has no fixed size: its members who can sit today (`IsEligible`).
  A house elected for a fixed term gives its term's first day and length in `HOUSES` (`term`); update it after each election. Brazil's terms come from its last election.
  A party's code in the data is matched to `congress` in `party_profiles.csv`, whatever its case (the court writes PCDOB, the Chamber PCdoB); where two houses code a party differently, `congress` holds both, `;`-separated (France's PS is `SOC;SER`). A member without a party counts as "No party". A group that is not a party (the Lords' crossbenchers, a Speaker, a mixed group) has a profile for its name and colour, with no position or ideology.
  Each house is a half circle of dots, one a seat (`static/js/lib/hemicycle.js`), beside a table of the parties with their logos, seats and share (`static/js/lib/congress-view.js`).
  **Next term**: after a general election, a "Seats" select (`?term=next`) shows the houses as they will sit from 1 February of the next year, until that day.
  The members elected come from the electoral court's candidate file (`providers/tse/elected.py`, CC BY): deputies elected by quotient or by average, senators elected.
  The next Senate adds the senators whose terms run on (`term_ends` on `pol_senator`, from the Senado's mandate data), with their party today.
  **Left, centre and right** (`politics/spectrum.py`, `?by=bloc`): the second view colours each seat by bloc, and the table lists each bloc with its parties.
  The scores, from 0, far left, to 10, far right, come from one survey per country (`SURVEYS` in `politics/spectrum.py`): for Brazil the 2022 wave of a survey of 571 Brazilian political scientists (Bolognesi, Codato, Ribeiro and Silva, Harvard Dataverse, CC0), for the European countries the general left-right question of CHES Europe 2024, and for the United States the 2019 Global Party Survey's economic left-right question (Q3.1), because it asked no general one; the US page says so. Italy's AVS, the joint list of Europa Verde and Sinistra Italiana, takes the average of the two (`JOINT` in `tools/party_left_right.py`).
  `tools/party_left_right.py` writes them to `data/politics/<country>/left_right.csv`; `curated.party_left_right` loads them, and every deploy runs it.
  Every country uses Bolognesi, Ribeiro and Codato's seven bands (Dados, 2023), joined into three blocs: left (far left, left: up to 3), centre (centre-left, centre, centre-right: up to 7), right (right, far right).
  A party founded after the survey takes the average of the parties that merged into it (PRD: PTB and Patriota); one founded later is "Not classified".
  In both views, the parties sit from left to right by that score; parties without one sit last.
  Each term carries its legislature's period (`LEGISLATURE` in `politics/congress.py`: four years from 1 February after an election); the card's title gives its years.
  **Video** (`static/js/lib/congress-reel.js`): `?reel=1` on the Congress tab plays the open house in the open term, and `tools/reel.py` records it like any other.
  The seats fill the half circle fast in their bloc's colour; a card goes through left, centre and right; the seats turn to their party's colour and a card goes through the ten largest parties (`PARTIES`), from the fewest seats to the most, so the largest comes last; the tables of blocs and parties close it.
  The title carries the period's years and the subtitle its first and last days. Its pace is `TIME` in the module.
- **Crime**, the last category, for the countries with crime data. `CRIME_TAB` in `config/settings.py` switches all of it off (False) and on (True).
  **Crime per year** (`politics/crime_series.py`, `?metric=crime-<key>`): each kind of crime is a metric of the Crime group, drawn leader by leader like any other, with no comparison group and no metric page.
  Its values are in `pol_crime_year` (country, year, crime, measure, value), which `curated.crime` loads from `data/politics/<country>/crime.csv`; every deploy runs it.
  Each line starts in the first year that compares with the years after it; the measure's note under the tabs says why it starts there.
  A source whose licence asks to be named gets it on the source line (`licence` on its `Source`).
  Germany: the BKA's PKS time series. `tools/germany_crime.py` downloads them with curl (bka.de stalls and resets) and writes the CSV.
  T01 gives each offence key's cases, cases per 100,000 people (the BKA's HZ) and clearance rate; T40 and T50 suspects per 100,000 residents aged 8 and over; T91 and T92 victims.
  Lines start in 1993, the first year of all of Germany, or later after a law or a counting change (`CRIMES` in the tool).
  The source line names the report year and the table's version, and the Datenlizenz Deutschland – Namensnennung 2.0, as the BKA asks.
  The census rebases (2011 census from 2013, 2022 census from 2024) are noted under the rates.
  Germany's Länder come from each edition's Länder table (T01 by Land; `LAENDER` in the tool), from 2014: there is no time series by Land. The 16 Länder add up exactly to the whole country, and the map cites the Länder tables (`states_source`).
  Brazil: two federal sources, free to reuse under Decreto 8.777/2016, art. 4. `tools/brazil_crime.py` fetches both and writes the CSV.
  Deaths come from the Ministry of Health's death certificates (SIM), through DATASUS's TabNet, from 1979: ICD-9 until 1995, ICD-10 from 1996; the newest year is preliminary.
  Homicides are assaults and legal interventions (X85–Y09, Y35–Y36; E960–E978); firearm homicides are X93–X95 (E965), without police shootings.
  Since 2019 many more violent deaths have no stated intent (Y10–Y34), which hides some homicides: they have a tab of their own, and the homicide notes say so.
  Police series come from the Ministry of Justice's Sinesp VDE, the states' own rows only, from 2015.
  Before a state took up a category it often sent zeros, so each series starts in its first year with every state (`first` in `SINESP`), and a year counts only when all 27 states sent all 12 months.
  Rates are ours, per 100,000 people, women or people aged 15 to 29, with the World Bank's population (UN World Population Prospects): one series with no splice, the one the Population page shows.
  By state: SIM's homicides, firearm homicides, women killed and deaths of unknown intent from 2000, and every Sinesp series (a state counts in a year when it sent all 12 months); state rates divide by IBGE's projections (Revisão 2024), which start in 2000.
  Prison population: people in prison cells and police cells at the end of each year, from 2000 (Senappen's reports to 2015, its Sisdepen files from 2016), compiled by hand into `data/politics/brazil/prison.csv` with each row's source; by state, each state's prison cells from 2016. SENAPPEN's own headlines also count people at home from 2016, so they are not used. The tool reads the file and adds the rates.
  France: the Interior Ministry's statistical service (SSMSI) on data.gouv.fr, Licence Ouverte 2.0: 16 kinds of crime for the 101 départements from 2016 (its base by département) and the whole country's own figures (its base of time series, homicides from 2008). Prisoners from the Ministry of Justice's yearly series (held on 1 January, counted under the year before), from 1989. Rates are ours, on INSEE's estimates on 1 January (the average of the year and the next). `tools/france_crime.py` resolves the files through data.gouv.fr's API.
  United States: the FBI's estimated crimes 1979 onward from its Crime Data Explorer (public domain), fetched through the explorer's signed-address route: nine kinds of crime for the nation, the 50 states and DC, with the FBI's population for the rates. Rape has two series, the definition of 2013 and the legacy one to 2016. The nation's missing 2017–2020 rows are the states' sums. `tools/united_states_crime.py`.
  Italy: Istat's SDMX API (CC BY 4.0), crimes reported by the police to the courts from 2006, for Italy and 106 provinces; rates are ours, on Istat's residents on 1 January (reconstructed 2001–2019, then the series after the 2021 census). Istat keeps Sardinia's four provinces at their 2001 borders, so `naturalearth.states` merges Natural Earth's eight into them (`MERGED`) and Cagliari's population adds Sud Sardegna's. Women killed from Istat's victims by sex (2007 onward, nation only). Prisoners from the Ministry of Justice's page of prisoners present on 31 December (1991 onward; reuse allowed for non-commercial ends). `tools/italy_crime.py`.
  United Kingdom: England and Wales only, no map: the ONS's appendix tables of police recorded crime by offence (Home Office data, year ending March 2003 onward), its knife offences table (2019 onward), the Home Office Homicide Index through the ONS (offences still recorded as homicide, 1967 onward) and the Ministry of Justice's annual average prison population (2015 onward), all OGL v3. Years run April to March and are written as their first calendar year. Rates are ours, on the ONS's mid-year estimate of England and Wales. `tools/united_kingdom_crime.py` resolves the newest files through the ONS's and gov.uk's JSON.
  Austria: the Bundeskriminalamt's yearly Kriminalitätsbericht PDFs 2010–2023 (reuse allowed with the source named, non-commercial), parsed with `pdftotext -layout`: cases, our rate and the clearance rate by offence (§ StGB) for Austria and each Bundesland; the PKS brochures add 2024 and 2025 for some kinds and the Länder totals. Convictions since 1947 from Statistik Austria (CC BY 4.0, `tools/ods.py` reads the .ods). Rates are ours, on Statistik Austria's population at the start of the year. `tools/austria_crime.py`.
  **By state**: a kind of crime that has figures by state gets a map under its chart, in the measure open above, with a year dropdown when there are several years and the states ranked beside it (`static/js/lib/states-view.js`, drawn by `createChoropleth` in `static/js/lib/world-map.js`).
  Its rows are `pol_crime_year` rows with a `state`, in the same CSV (`state` is the ISO 3166-2 code, empty for the whole country).
  The states and their borders are `geo_state`, from Natural Earth's 1:10m admin-1 units (`naturalearth.states`, only the countries in its `COUNTRIES`); the page loads them from `/politics/<country>/states.json`.
  **State flags**: `media/flags/states/<ISO 3166-2>.svg`, shown in the ranked list, the map's tooltip, the saved image and the video wherever the file exists (`state_flag` in `politics/crime_series.py`). Brazil's 27 come from Wikimedia Commons, all public domain, listed with their file, licence and author in `data/politics/brazil/state_flags.csv`; `tools/brazil_state_flags.py` downloads them again. Credit any flag that is not in the public domain.
  **Video** (`static/js/lib/states-reel.js`): `?reel=1&states=1` on a kind of crime counted by state plays the map's video, and `tools/reel.py` records it like any other. The map starts empty; the states fill in one by one, the best first (the lowest where lower is better), each with a gold glow and a card with its name, its value and its rank; the first three are held longer, the rest share about 13 seconds. The full map holds, then a ranking of every state takes the map's place, best first, with a bar in each state's colour; a long ranking scrolls, for at most 12 seconds. The reel paints the shapes itself from the states' GeoJSON (`fitShapes`), so it needs no ECharts.
  Far-off parts are drawn as insets beside the mainland, moved and scaled in the loader (`INSETS`: Alaska and Hawaii under the contiguous states, the French overseas départements in a column west of Brittany), and `NAME_FIXES` mends Natural Earth's names (`US-DC`, Italy's Genoa, South Tyrol). `geometry.dissolve` merges units that share their borders point for point, `geometry.moved` makes an inset.
  The map's title and note per country are `STATES_TITLE` and `STATES_NOTE` in `politics/crime_series.py`.
  **Suspects by nationality** (`politics/crime.py`, `?tab=crime`), the Crime group's last tab: Germany only.
  Each nationality's crime suspects in a year, from the BKA's police statistics (PKS table T62), beside its people in Germany on 31 December, from Destatis: foreigners from the Ausländerzentralregister (12521-0002), Germans from the population update.
  The chart shows one thing: the share of each nationality's people whom the police registered as suspects. Labels say "Population in Germany" (`population` in `CONTEXT`).
  **Kinds of offence**: a searchable tree picker (`static/js/lib/tree-picker.js`, `?offences=`) under Total, from the PKS's own groups (`OFFENCES`). A parent's box checks or clears everything inside it, and shows a dash when only some are checked.
  Total is every offence but those against residence and asylum law (T62 key 890000): only foreigners can break those laws, so they are no choice of their own. Offences under other laws (700000) take them in, so that group is the sum of its other laws' groups (`summed`).
  The police count a suspect once for each kind of offence. A whole kind uses the BKA's own count, where each person counts once; several kinds add up, and a note says a person may then count more than once.
  The country's citizens and the 20 foreign nationalities with the highest shares for the chosen offences open the chart, and the page, the image and the video say so. Once nationalities are picked by hand they stay (`?nationalities=`), until the Top 20 button (`HIGHEST`) brings back the highest shares for the chosen offences. Only nationalities with at least 10,000 people are listed (`MIN_PEOPLE`), as with fewer a handful of suspects moves the share a lot.
  The notes under the chart say what it cannot show: suspects are not convicts, the register and the population update count differently, the police also count people who do not live here, and neither table gives ages by nationality.
  **Video** (`static/js/lib/crime-reel.js`, `?reel=1` on the tab): the bars grow in, the largest share first; cards go through the country's citizens, every foreign national together and the four largest foreign nationalities; a last card says what the shares cannot show (`limits` in `CONTEXT`). It shows as many bars as a phone can read (`ROWS`): the citizens and the foreign nationalities with the highest shares, and its explanation says so.
  `tools/germany_suspects.py <T62.xlsx> <12521-0002.csv>` writes `data/politics/germany/population.csv` and `suspects.csv`. Both source files are downloaded by hand: bka.de drops Python's connections, and GENESIS needs a login. `curated.population_by_nationality` loads `pol_population_nationality`, and `curated.suspects` loads `pol_suspects_nationality_offence`; every deploy runs both.
  Columns: the country's citizens #c98500, foreign nationals #3987e5, the largest share first, each with its flag and name; where the columns are too narrow for a name under the flag, a second axis slants the names under the flags. On phones and in the saved image they turn into rows, so every name fits (`static/js/lib/suspects-chart.js`).
  The BKA allows reuse with the BKA named as the source; Destatis's data is under the Datenlizenz Deutschland – Namensnennung 2.0.
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
