# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Django (Python), server-rendered templates, PostgreSQL 18. Recommended by Claude and accepted by the user on 2026-10-18. The database runs in Docker (docker-compose.yml). Charts use ECharts, served from static/vendor.

## Users

- **Primary:** anyone who needs a trustworthy statistic and a chart quickly: students, journalists, curious people. This is the audience Statista serves behind a paywall.
- **Secondary:** data practitioners (analysts, Python and BI people) who want the raw data to export and read posts about technique.

## Product Purpose

An open-source alternative to Statista. Data Mechanics fetches data from multiple public sources and gives it away free, with good charts and the option to export the underlying data. A blog sits alongside it, covering data, insights, charts, data science, AI and Python.

Success means a visitor finds a number, sees it charted, knows exactly where it came from, and can take the data with them, without paying or signing up.

## Positioning

Free where Statista is paywalled, and open where it is closed: the site's code is public on GitHub, the data is free to download, and every figure cites its original source.

## Operating Context

- Data is fetched from public sources (for example the World Bank API) and republished with source and retrieval date.
- Visitors export data (CSV first) to use in their own work.
- The blog is written by Klaus Folz.

## Capabilities and Constraints

- Confirmed: free data, charts, data export (CSV per metric), search, blog.
- Data architecture (CLAUDE.md, Data design): ETL modules in providers/<provider>/<source>.py, one table each; the site reads only the database. Country tables are named geo_<metric>_country_year and point at the geo_country dimension.
- Metrics (49, 2026-10-22): GDP, GDP per capita (current US$ and PPP), GDP growth, productivity (output per hour worked), inflation, unemployment, government debt, interest on government debt, budget balance, primary balance, government spending, tax revenue, trade, women in the labour force; population (with births, deaths and net migration), fertility rate, median age; life expectancy, child mortality, obesity, health spending; years of schooling, literacy rate, government spending on education, scientific and technical articles; HDI, mean income or consumption, extreme poverty, income inequality (Gini), income share of the richest 1%; V-Dem democracy indices, human rights index, military spending; corruption: the V-Dem political, executive, public sector and judicial corruption measures and Transparency International's Corruption Perceptions Index; CO2 emissions, electricity mix, air pollution (PM2.5 exposure, share above the WHO guideline); life satisfaction, homicide rate, gender wage gap, V-Dem women's political empowerment index, share of women in parliament; food: undernourishment (share of people, World Bank and FAO, from 2026-10-25), people who cannot afford a healthy diet, meat production.
- Licence notes: WHO obesity data is CC BY-NC-SA 4.0 (non-commercial, share-alike); World Happiness Report data is free to download with a citation but has no formal open licence.
- Every metric page has a world map (year filter, good/mid/bad colours) and a line chart (country filter with flags and a World option).
- Languages (2026-10-18): English, German and Portuguese (Brazilian) on every page, with an EN · DE · PT switcher in the header. English at the root, the others under /de/ and /pt/. Blog posts stay in English.
- Politics mode (2026-10-18): one page per country with every metric coloured by the president in office, the party logo where each presidency starts, and the change during it (green good, red bad) where it ends. Brazil (presidents since 1956) and the United States (since 1953, added 2026-10-18); each starts with the president in office in 1960, the first year of most World Bank series. The metrics it shows are listed in politics/metrics.py. Since 2026-10-22 every chart also compares the country with the World, BRICS, the G7 or the G20 over each term (politics/comparison.py).
- Brazil's party compass and Congress (2026-10-25): two tabs before the metric tabs of Brazil's Politics page. The compass places up to 23 parties on the economy and on social values, from three expert surveys shown one at a time (PREPPS Latam, CHES Latin America, the Global Party Survey). Relevant parties a survey left out get an inferred place, drawn in a dashed frame and explained. Congress shows the Chamber of Deputies and the Senate as half circles of seats beside a table of the parties, from the two houses' open-data APIs.
- Congress after the 2026 election (2026-10-25): the houses as they sit from 1 February 2027 (TSE results), party names never translated, and a view that groups the parties into left, centre and right from a 2022 survey of 571 political scientists.
- Site title (2026-10-25): "Data Mechanics · The world in numbers". Congress videos: each house, by bloc and then by party, closing on the tables, with the term's period.
- Conflicts (2026-10-25): a section with one page per war, in its own database (`conflicts`, one schema per conflict). World War II first, inspired by Neil Halloran's "The Fallen of World War II": casualties by country as a column chart with a country picker and Soldiers/Civilians toggles; 67 battles on a zoomable map of 1937–1945 borders (CShapes, CC BY-NC-SA 4.0) sized by casualties, with a timeline that plays the war day by day; and the battles listed one by one in the Politics timeline's style. Germany's flag is the user's own drawing without the swastika.
- Undecided: the public GitHub URL for the site's code, data licence wording beyond the World Bank's CC BY 4.0.

## Brand Commitments

- Name: Data Mechanics.
- Logo: `logo/dataMechanicsBlueYellow.svg` (gold gear on a blue disc). Logo colours from `logo/colors.txt`: dark blue `#002F4F`, gold `#FFD700`, grey `#e6e6e6`.
- The user set the site's style as **cyberpunk** (binding): "a real dark cyberpunky feel, modern style".
- 2026-10-18: the user pinned Kalshi (kalshi.com) as the reference for layout, dark greys and general aesthetic. The bright green Kalshi uses for its title is excluded; the accent is the logo gold #FFD700.
- The logo spins slowly, as on the old site (`gearspin`: one turn every 7 s, linear).
- Every page ends with an About the author section with LinkedIn (linkedin.com/in/klausjfolz) and GitHub (github.com/jurgenfolz) links.
- From the old WordPress site, only the blog posts and the logo are kept.

## Evidence on Hand

- 3 blog posts in `old_word_press_export/datamechanics.WordPress.2026-10-18.xml` (Power BI / Power Query and Python topics, 2025), imported with their images.
- The author's bio and round portrait from the old site's About section (user approved the portrait on 2026-10-18).
- Real data from the World Bank, IMF, UNDP, V-Dem (via Our World in Data) and Natural Earth, loaded by `python manage.py etl`.
- Country flags as SVG in media/flags (4x3 and 1x1, ISO 3166-1 alpha-2 file names).
- No users, testimonials, traffic figures or press exist yet. Do not invent any.

## Product Principles

1. Every number cites its source and when it was fetched.
2. Free means free: no paywall, no sign-up to see or export data.
3. Show the data working (a real chart) instead of describing it.
4. Simple first: build what is needed now, add sources and features as real needs appear.
