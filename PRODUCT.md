# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Django (Python), server-rendered templates, PostgreSQL 18. Recommended by Claude and accepted by the user on 2026-10-18. Locally the database runs in Docker (docker-compose.yml); it will move to a Hostinger VPS running Ubuntu 26.04 LTS. Charts use ECharts, served from static/vendor.

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
- Metrics (27, 2026-10-18): GDP, GDP per capita (current US$ and PPP), GDP growth, inflation, unemployment, government debt, tax revenue, trade, women in the labour force; population (with births, deaths and net migration), fertility rate, median age; life expectancy, child mortality, obesity, health spending; years of schooling; HDI, extreme poverty, income inequality (Gini); V-Dem democracy indices, human rights index, military spending; CO2 emissions, electricity mix; life satisfaction, homicide rate.
- Licence notes: WHO obesity data is CC BY-NC-SA 4.0 (non-commercial, share-alike); World Happiness Report data is free to download with a citation but has no formal open licence.
- Every metric page has a world map (year filter, good/mid/bad colours) and a line chart (country filter with flags and a World option).
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
