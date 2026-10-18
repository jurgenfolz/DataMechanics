---
name: Data Mechanics
description: Free public statistics on every country, laid out like a dark market front page, with gold as the only accent.
colors:
  gold: "#ffd700"
  gold-hover: "#ffe24d"
  gold-wash: "rgb(255 215 0 / 0.1)"
  bg: "#121416"
  card: "#17191b"
  well: "#1d1f21"
  raised: "#222427"
  pill: "#2f3132"
  line: "#2c2e30"
  line-strong: "#3a3d41"
  ink: "#f2f3f4"
  ink-2: "#b6b9bd"
  ink-3: "#8b8f94"
  prose-ink: "#d9dbde"
  code-ground: "#0d0f10"
  no-data: "#2a2c2f"
  map-worse: "#e66767"
  map-better: "#5598e7"
  map-low: "#0d366b"
  map-high: "#cde2fb"
  series-1: "#3987e5"
  series-2: "#d95926"
  series-3: "#199e70"
  series-4: "#c98500"
  series-5: "#d55181"
  series-6: "#008300"
  series-7: "#9085e9"
  series-8: "#e66767"
  world-line: "#c9ccd0"
typography:
  display-xl:
    fontFamily: "Archivo, Helvetica Neue, Arial, sans-serif"
    fontSize: "clamp(2.75rem, 6.4vw, 5.75rem)"
    fontWeight: 700
    lineHeight: 0.94
    letterSpacing: "-0.02em"
    fontVariation: "'wdth' 75"
  display-lg:
    fontFamily: "Archivo, Helvetica Neue, Arial, sans-serif"
    fontSize: "clamp(2.5rem, 5vw, 3.5rem)"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "-0.02em"
    fontVariation: "'wdth' 75"
  display:
    fontFamily: "Archivo, Helvetica Neue, Arial, sans-serif"
    fontSize: "clamp(2.25rem, 4.4vw, 3.25rem)"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "-0.02em"
    fontVariation: "'wdth' 75"
  headline:
    fontFamily: "Archivo, Helvetica Neue, Arial, sans-serif"
    fontSize: "clamp(1.75rem, 2.6vw, 2.125rem)"
    fontWeight: 700
    lineHeight: 1.05
    letterSpacing: "-0.015em"
    fontVariation: "'wdth' 75"
  headline-sm:
    fontFamily: "Archivo, Helvetica Neue, Arial, sans-serif"
    fontSize: "1.75rem"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.01em"
    fontVariation: "'wdth' 75"
  prose-heading:
    fontFamily: "Archivo, Helvetica Neue, Arial, sans-serif"
    fontSize: "1.625rem"
    fontWeight: 700
    lineHeight: 1.2
    fontVariation: "'wdth' 85"
  title:
    fontFamily: "Archivo, Helvetica Neue, Arial, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 700
    lineHeight: 1.3
  title-sm:
    fontFamily: "Archivo, Helvetica Neue, Arial, sans-serif"
    fontSize: "1rem"
    fontWeight: 700
    lineHeight: 1.3
  wordmark:
    fontFamily: "Archivo, Helvetica Neue, Arial, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 800
    letterSpacing: "-0.01em"
  body-lead:
    fontFamily: "Archivo, Helvetica Neue, Arial, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 400
    lineHeight: 1.55
  body:
    fontFamily: "Archivo, Helvetica Neue, Arial, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.55
  prose:
    fontFamily: "Archivo, Helvetica Neue, Arial, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 400
    lineHeight: 1.75
  meta:
    fontFamily: "Archivo, Helvetica Neue, Arial, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 400
    lineHeight: 1.55
  label-nav:
    fontFamily: "Archivo, Helvetica Neue, Arial, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 800
    letterSpacing: "0.08em"
  button:
    fontFamily: "Archivo, Helvetica Neue, Arial, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 700
  value:
    fontFamily: "Archivo, Helvetica Neue, Arial, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 700
    fontFeature: "'tnum' 1"
  mono:
    fontFamily: "JetBrains Mono, ui-monospace, Menlo, Consolas, monospace"
    fontSize: "0.75rem"
    fontWeight: 400
    letterSpacing: "0.02em"
rounded:
  card: "12px"
  tooltip: "10px"
  well: "8px"
  control: "6px"
  check: "4px"
  flag: "3px"
  pill: "999px"
  round: "50%"
spacing:
  gutter: "clamp(16px, 4vw, 40px)"
  wide: "1272px"
  rail: "344px"
  layout-gap: "48px"
  section: "56px"
  spotlight: "24px"
  card: "20px"
  grid: "16px"
  row: "12px"
components:
  button-primary:
    backgroundColor: "{colors.gold}"
    textColor: "{colors.bg}"
    typography: "{typography.button}"
    rounded: "{rounded.pill}"
    padding: "0 18px"
    height: "40px"
  button-primary-hover:
    backgroundColor: "{colors.gold-hover}"
    textColor: "{colors.bg}"
  button-outline:
    backgroundColor: "transparent"
    textColor: "{colors.gold}"
    typography: "{typography.button}"
    rounded: "{rounded.pill}"
    padding: "0 18px"
    height: "40px"
  button-outline-hover:
    backgroundColor: "{colors.gold-wash}"
    textColor: "{colors.gold}"
  button-round:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.round}"
    size: "36px"
  button-round-hover:
    textColor: "{colors.gold}"
  value-pill:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.value}"
    rounded: "{rounded.pill}"
    padding: "0 14px"
    height: "36px"
  value-pill-hover:
    backgroundColor: "{colors.gold-wash}"
  search-field:
    backgroundColor: "{colors.pill}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "0 16px"
    height: "40px"
  chip:
    backgroundColor: "transparent"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.pill}"
    padding: "0 10px"
    height: "24px"
  chip-hover:
    textColor: "{colors.gold}"
  icon-tile:
    backgroundColor: "{colors.gold-wash}"
    textColor: "{colors.gold}"
    rounded: "{rounded.well}"
    size: "32px"
  icon-tile-lg:
    backgroundColor: "{colors.gold-wash}"
    textColor: "{colors.gold}"
    rounded: "{rounded.tooltip}"
    size: "40px"
  card:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.card}"
  card-market:
    backgroundColor: "{colors.card}"
    rounded: "{rounded.card}"
    padding: "20px"
  card-spotlight:
    backgroundColor: "{colors.card}"
    rounded: "{rounded.card}"
    padding: "24px"
  card-rail:
    backgroundColor: "{colors.card}"
    rounded: "{rounded.card}"
    padding: "20px"
  card-chart:
    backgroundColor: "{colors.card}"
    rounded: "{rounded.card}"
    padding: "20px 20px 18px"
  chart-well:
    backgroundColor: "{colors.well}"
    rounded: "{rounded.well}"
  select:
    backgroundColor: "{colors.well}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "0 34px 0 14px"
    height: "36px"
  picker-button:
    backgroundColor: "{colors.well}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "0 14px"
    height: "36px"
  picker-panel:
    backgroundColor: "{colors.card}"
    rounded: "{rounded.card}"
    padding: "8px"
    width: "340px"
  series-key:
    backgroundColor: "{colors.well}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "0 6px 0 10px"
    height: "32px"
  tooltip:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.tooltip}"
    padding: "10px 12px"
  nav-link:
    textColor: "{colors.ink}"
    typography: "{typography.label-nav}"
  nav-link-active:
    textColor: "{colors.gold}"
  category-tab:
    textColor: "{colors.ink-3}"
  category-tab-active:
    textColor: "{colors.ink}"
  series-tab:
    textColor: "{colors.ink-3}"
  series-tab-active:
    textColor: "{colors.ink}"
---

# Design System: Data Mechanics

## Overview

**Creative North Star: "The Open Data Exchange"**

Data Mechanics is a market front page where every listing is a public statistic. Each listing is headed by the metric's name with its question beneath as a smaller subtitle, its leading countries are quoted in gold value pills, and a world map sits beside them like a live chart. The home page opens with a large condensed statement of what the site is before the market begins. The floor is Kalshi's: quiet charcoal greys, rounded cards with hairline borders, condensed headlines, and pills for every control. Nothing is paywalled and nothing is hidden, so the page reads as an exchange whose prices are free.

The cyberpunk lives in the details rather than in costume. A faint 32 px grid is printed on the ground, chart wells carry gold HUD corner ticks, the gear logo turns, mono type marks codes, years and ranks, and focus and hover arrive as a gold glow. Colour discipline does the rest: one accent (the logo gold), greys for everything else in the interface, and data colours that keep strictly to the charts; the interface itself has no green or red. It is neither a white statistics portal nor a neon set piece, and Kalshi's bright green is not used anywhere, title included.

Density is high but calm. Cards sit in a regular grid, numbers are tabular and formatted the same way in every place they appear, values are quoted for their year alone with no change on the year before, and every chart names its source before it shows a single country.

**Key Characteristics:**
- Charcoal tonal stack (ground, card, well) separated by 1 px hairlines, never by resting shadows.
- Logo gold is the single interface accent; the interface has no green or red.
- Cards and the spotlight are headed by the metric's name, with its question as a smaller subtitle.
- Archivo at 75% width for headlines; Archivo at normal width for everything else; JetBrains Mono for codes, years and ranks.
- Pills for every control and value; 12 px corners for cards; 8 px for wells.
- Cyberpunk details: grid ground, HUD corner ticks, gold glow on focus and hover, spinning gear, mono for codes, years and ranks.
- Charts are first-class: an equal-area world map and country lines with flags, each under its source line.

## Colors

A near-monochrome charcoal floor with one hot gold accent and a separate, validated vocabulary for chart data.

### Primary
- **Gear Gold** (#ffd700): the logo gold and the only interface accent. It fills primary buttons, outlines value pills, colours the active main-nav link, underlines the active series tab, draws the focus glow, the HUD corner ticks, the map hover outline, links inside articles, icon glyphs in their tiles, text selection, the caret and the skip link.
- **Bright Gear Gold** (#ffe24d): the hover state of solid gold buttons only.
- **Gold Wash** (gold at 10%): the fill behind category icons and the hover fill of value pills and outline buttons. Gold never appears as a large area fill except on a button.

### Neutral
- **Exchange Floor** (#121416): the page ground under the 32 px grid, the map's country borders, and the text colour on gold.
- **Card Slate** (#17191b): every card, the search dropdown, the country picker panel, chart tooltips and sticky table headers.
- **Chart Well** (#1d1f21): the inset ground of every chart, plus selects, the picker button, series keys and inline code.
- **Raised Slate** (#222427): the highlighted row in search results and the picker, and hover behind small icon buttons.
- **Search Pill Grey** (#2f3132): the header search pill.
- **Hairline** (#2c2e30): card borders, list dividers, the header's bottom rule, chart gridlines.
- **Strong Rule** (#3a3d41): borders on controls (round buttons, selects, chips, picker), chart axis lines, the tab divider, and the neutral midpoint of the diverging map ramp.
- **Bright Ink** (#f2f3f4): headings, names, values and primary text.
- **Quiet Ink** (#b6b9bd): descriptions, the home introduction paragraph, the question under the spotlight's title, legends, chart end labels, footer links.
- **Muted Ink** (#8b8f94): meta lines, source lines, the question under a market card's title, axis labels, placeholders, ranks and inactive tabs.
- **Reading Ink** (#d9dbde): long-form article text, a step softer than Bright Ink for comfort.
- **Terminal Black** (#0d0f10): code blocks in articles, the only surface darker than the floor.

### Data Colours
- **Map, metrics with a better direction:** a seven-step diverging ramp from Setback Coral (#e66767) through Strong Rule grey to Progress Blue (#5598e7). The grey midpoint is the median country of that year.
- **Map, metrics without a better direction:** a seven-step single blue ramp from Deep Ramp Blue (#0d366b, low) to Pale Ramp Blue (#cde2fb, high).
- **No-Data Grey** (#2a2c2f): every country without a value, on the map and in the legend swatch.
- **Line series:** eight colours in a fixed order: Series Blue (#3987e5), Series Rust (#d95926), Series Teal (#199e70), Series Amber (#c98500), Series Rose (#d55181), Series Green (#008300), Series Violet (#9085e9), Series Coral (#e66767).
- **World Line Grey** (#c9ccd0): the World line, always dashed.

### Named Rules
**The One Gold Rule.** Gold is the only accent in the interface: primary buttons, value pills, the active nav link and series tab, focus glow, HUD corner ticks. A second accent colour is never introduced: the interface carries no green or red, and Kalshi's green is not used, for titles or anything else.

**The Data Stays In The Chart Rule.** Map ramps and line colours belong to the data. They never colour interface chrome, and gold never colours a chart mark, except as the hover outline of a country.

## Typography

**Display Font:** Archivo variable (width 62–125%, weight 100–900, self-hosted), with Helvetica Neue and Arial as fallbacks
**Body Font:** Archivo at normal width
**Label/Mono Font:** JetBrains Mono (self-hosted), with ui-monospace, Menlo and Consolas as fallbacks

**Character:** one grotesque in two widths. Condensed Archivo gives headlines the tight, quoted feel of a market board; normal-width Archivo keeps names, numbers and paragraphs plain and readable. JetBrains Mono is the terminal voice, used sparingly for codes, years and ranks.

### Hierarchy
- **Display Extra Large** (700, 75% width, clamp 2.75–5.75rem, line-height 0.94, -0.02em): the home introduction headline only; each of its two phrases holds together on one line on wide screens and wraps naturally on phones.
- **Display Large** (700, 75% width, clamp 2.5–3.5rem, line-height 1): the Posts index title.
- **Display** (700, 75% width, clamp 2.25–3.25rem, line-height 1, -0.02em): a metric's name, an article title, the search results heading.
- **Headline** (700, 75% width, clamp 1.75–2.125rem, line-height 1.05): the metric's name on the spotlight card; the question under it is 400 at 1.0625rem in Quiet Ink.
- **Headline Small** (700, 75% width, 1.75rem, line-height 1.1): home section titles, each followed by a gold chevron; the About the author title uses the same cut a step smaller.
- **Prose Heading** (700, 85% width, 1.625rem): subheadings inside articles.
- **Title** (700, 1.0625rem, line-height 1.3): market card titles (the metric's name). Chart card titles run a step larger (1.125rem) with the series name after a middle dot in Muted Ink.
- **Title Small** (700, 1rem): rail card titles, tile and post card titles.
- **Body Lead** (400, 1.125rem): the one-line summary under a metric's name, up to 60ch. The home introduction paragraph uses the same size at line-height 1.6 in Quiet Ink, up to 62ch.
- **Body** (400, 0.9375rem, line-height 1.55): all interface text; descriptions run to 72ch.
- **Prose** (400, 1.0625rem, line-height 1.75, Reading Ink): article bodies in a 760 px column.
- **Meta** (400, 0.8125rem, Muted Ink): source lines, card feet, notes, timestamps, and the question under a market card's title.
- **Nav Label** (800, 0.8125rem, 0.08em, uppercase): the three main header links only.
- **Value** (700, 0.9375rem, tabular figures): numbers in value pills and ranking lists.
- **Mono** (JetBrains Mono, 0.75rem, 0.02em): ranks, table year column, chart x-axis years. Tile year spans and search category tags run at 0.6875rem uppercase.

### Named Rules
**The Condensed Headline Rule.** Page titles, the home introduction headline, the spotlight title, section titles and the About title are Archivo at 75% width (font-stretch 75%). Card titles, body text and numbers stay at normal width.

**The Mono Ticker Rule.** JetBrains Mono is for codes, years and ranks. Values in pills, names and prose are never set in mono.

**The Same Number Rule.** A value is written the same way everywhere, by one set of unit rules shared by server and browser: money and people compact to three significant digits with a spaced suffix ($14.4 k, 1.43 bn); percentages to one decimal (8.5%); years to one decimal with " yrs"; rates with " per 1,000"; indices to three decimals (0.756). A missing value is an en dash (–). Every number uses tabular figures.

## Layout

Content sits in a centred column up to 1272 px wide with fluid side gutters (16–40 px). The header is sticky and has two rows: a 68 px bar (spinning logo and wordmark, three nav links, a search pill up to 400 px wide, LinkedIn outline and GitHub solid pills) and a 46 px row of category tabs.

On the home page an introduction comes first, straight on the floor with 24 px of its own padding above and 40 px below, before the two-column grid; the home rail holds only the Latest posts card. Main pages use a two-column grid: a flexible content column and a 344 px rail, 48 px apart. The rail follows the scroll (sticky at 140 px from the top) only when the window is at least 1101 px wide and 1040 px tall, so it never hides its own content. Pages start 24 px below the header and leave 64 px at the bottom; home sections are 56 px apart, with 18 px between a section title and its cards. Market cards fill an auto grid of columns at least 270 px wide with 16 px gaps; the Latest data strip is a horizontal scroll of 152 px tiles with 12 px gaps and snap points; the trust row and the home post cards use three equal columns. The About the author card sits 72 px below every page's content, and the footer 40 px below that.

Responsive behaviour:
- **At 1100 px and below,** the rail drops under the content as a two-column grid and the header's LinkedIn pill hides.
- **At 860 px and below,** the bar shrinks to 60 px, the nav links and both social pills hide (the About section carries the links), the category tabs fade at their right edge, the spotlight stacks its map under the country rows, and the trust row and post cards become one column.
- **At 640 px and below,** the search folds into a 44 px round button that opens across the whole bar when focused, the rail becomes one column, post rows stack their image above the text, and chart cards tighten to 16/14 px padding.

## Elevation & Depth

The system is flat and tonal. Depth comes from three steps of charcoal (Exchange Floor, Card Slate, Chart Well) and 1 px hairlines, not from shadow. The ground itself carries texture: a 32 px grid of white lines at 2.2% opacity, fixed to the viewport. The sticky header is the floor colour at 94% opacity with a 10 px backdrop blur. Shadows appear only on layers that float above the page, and light appears only as gold glow.

### Shadow Vocabulary
- **Dropdown** (`box-shadow: 0 18px 40px rgb(0 0 0 / 0.5)`): search suggestions; the country picker uses the same shadow at 55%.
- **Tooltip** (`box-shadow: 0 12px 30px rgb(0 0 0 / 0.5)`): chart tooltips.
- **Focus Glow** (`box-shadow: 0 0 0 1px #ffd700, 0 0 18px rgb(255 215 0 / 0.28)`): every keyboard focus.
- **Pill Glow** (`box-shadow: 0 0 16px rgb(255 215 0 / 0.3)`): hover on a value pill; the search pill takes a softer 18% glow while focused.
- **Tab Glow** (`box-shadow: 0 0 10px rgb(255 215 0 / 0.5)`): under the 2 px gold underline of the active series tab.
- **Country Glow** (gold border 1.4 px with a 14 px gold blur at 55%): a hovered country on the map.
- **Flag Hairline** (`box-shadow: 0 0 0 1px rgb(255 255 255 / 0.08)`): keeps light flags from melting into the dark.

### Named Rules
**The Tonal Stack Rule.** Cards rest flat on the floor with a hairline border. Hover changes the border (to gold on link cards), never the elevation.

**The Gold Light Rule.** The only light in the world is gold: focus, pill hover, the active tab and the hovered country glow. No other colour glows.

**The Grid Ground Rule.** The page ground is #121416 with its faint 32 px grid on every page; the grid never sits inside cards or wells.

## Shapes

Two shape families carry the whole system. Containers are softly rounded rectangles: cards at 12 px, chart wells, inner images and the results table at 8 px, tooltips, code blocks and the large icon tile at 10 px. Controls and values are full pills (999 px): buttons, the search field, selects, the country picker button, chips, tile tags, series keys, value pills and the skip link. Circles are reserved for round icon buttons, round flags in market rows, and the author's portrait.

Rectangular flags (4:3) keep 3 px corners and a hairline ring; round flags (1:1) are 30 px circles. The World is drawn as a flag of its own: a navy field with a pale grey globe, used wherever a country flag would be.

Chart wells carry HUD corner ticks: 12 px L-shaped brackets inset 6 px at the top-left and bottom-right, drawn in gold at 45%. Dashed lines are rare and meaningful: the divider under the spotlight's rows and the border of the "Explore every metric" card. Icons are one stroke set on a 24 px grid, 1.8 stroke, round caps and joins, coloured by the text around them.

## Components

### Buttons
Confident gold pills that press.
- **Shape:** full pill (999px), 40 px tall, 18 px side padding, 16 px icon with 8 px gap.
- **Primary:** Gear Gold fill, Exchange Floor text, 700 weight at 0.875rem. Used for GitHub, Search, Download CSV, the About links and Explore the metrics in the home introduction.
- **Hover / Focus:** fill shifts to Bright Gear Gold in 150 ms; focus shows the gold glow; pressing scales to 0.97 over 120 ms with the system's ease-out (cubic-bezier(0.23, 1, 0.32, 1)).
- **Outline:** transparent with a gold border and gold text (LinkedIn, Read the posts); hover adds Gold Wash.
- **Large:** in the home introduction, primary and outline pills grow to 44 px tall with 20 px side padding and a 0.9375rem label.
- **Round:** 36 px circle with a Strong Rule border and a 16 px chevron, used for carousel and strip arrows; hover turns border and icon gold, press scales to 0.94, disabled drops to 35% opacity.
- **Text link:** Quiet Ink, 600, underlined in Strong Rule; hover turns both gold (JSON download, inline links in notes).

### Value Pill
The market quote. A 36 px pill at least 88 px wide with a 1.5 px gold border, Bright Ink value in 700 tabular figures, no fill. Each one links to the metric page with that country selected. Hover adds Gold Wash and the pill glow.

### Chips
- **Style:** 24 px pill with a Strong Rule border, Quiet Ink text at 0.75rem 600, no fill.
- **State:** link chips (metric tags) turn border and text gold on hover; post category chips are static. Category tile tags are the larger sibling (5/12 px padding, 0.8125rem).

### Cards / Containers
- **Corner Style:** 12 px.
- **Background:** Card Slate, on the gridded floor.
- **Shadow Strategy:** none at rest (see Elevation & Depth).
- **Border:** 1 px Hairline; link cards (tiles, post cards, post rows, the explore card) turn it gold on hover, trust items only to Strong Rule.
- **Internal Padding:** 20 px for market and rail cards, 24 px for the spotlight, 28 px for About the author, 16–18 px for tiles and trust items.

**Market card.** The signature listing. A gold icon tile beside the metric's name (Title), the metric's question under it in Muted Ink (Meta), then two country rows (round flag, name, value pill), then a foot line with the World value and year on the left and the country count on the right.

**Spotlight card.** The home page's featured market: icon tile and a "1 of 9" pager with round arrows on top, the metric's name as a condensed headline (gold on hover) with its question beneath in Quiet Ink, then two columns: the top three countries with value pills, the World value and an Explore link above a dashed divider, a short data note; and a world map well on the right. Arrows or arrow keys swap slides with a 180 ms fade-up (6 px) while the one shared map recolours.

**Rail card.** A titled list: title row with a hairline under it (a chevron when the title links), rows divided by hairlines. Link rows (Latest posts on the home page, More metrics on a metric page) set a title over a Muted Ink sub line, and the title turns gold on hover. Ranking rows show a mono rank, a 4:3 flag, the country (a button that adds it to the line chart) and the value.

### Inputs / Fields
- **Search:** a 40 px Search Pill Grey pill with a Muted Ink magnifier and placeholder ("Search any metric"); the "/" key focuses it. Focus turns the border gold with a soft gold glow. Suggestions open in a Card Slate panel (12 px corners, Strong Rule border, dropdown shadow) whose rows show the metric name, a mono uppercase category on the right and the summary below; the active row takes Raised Slate.
- **Select:** a 36 px Chart Well pill with a Strong Rule border, bold tabular value and a drawn chevron; hover turns the border gold, focus shows the gold glow. Used for the map's year.
- **Country picker:** a pill button naming the first two selections and a "+N" count opens a 340 px Card Slate panel with a pop (160 ms scale from 0.97). Inside: a search field (8 px corners, gold border on focus), a hint line ("Pick up to 8 countries"), then rows of checkbox, flag and name. World is listed first, divided from the countries by a hairline. A chosen row fills its checkbox with gold and a dark tick; rows past the limit dim to 40%.

### Navigation
- **Main nav:** three uppercase links (Nav Label) in Bright Ink; hover and the current section turn gold.
- **Category tabs:** 600 at 0.9375rem in Muted Ink, scrolling without a scrollbar; hover lifts to Bright Ink, the current tab becomes Bright Ink at 800. A 16 px Strong Rule divider separates the categories from Posts.
- **Series tabs:** the measures of a metric (Electoral, Liberal, and so on) in the same Muted Ink style over a hairline; the active one turns Bright Ink at 800 with a 2 px gold underline and its glow. When tabs overflow, the strip fades at its right edge.
- **Breadcrumbs:** Meta size, Quiet Ink links separated by a slash, gold on hover.
- **Mobile:** below 860 px only the wordmark, the search and the tab row remain; below 640 px the search becomes a round button.

### Introduction
The home page's opening statement, set straight on the gridded floor with no card. A Display Extra Large headline in Bright Ink, written as two phrases that each hold together on one line on wide screens; a paragraph in Quiet Ink at 1.125rem (line-height 1.6, up to 62ch) 20 px below it; then, 26 px below that, a large primary pill with an arrow (Explore the metrics) and a large outline pill (Read the posts), 12 px apart and wrapping when narrow.

### Chart Card, Well and Source Line
Every chart lives in a card: a head with the title and its control (year select or country picker), then the source line, then the well. The source line (Meta, Muted Ink) names the source with a Quiet Ink link, the source's own update date and the date it was fetched. The well is Chart Well with 8 px corners and HUD corner ticks. While data loads the well dims to 55% and keeps its size.

### World Map
An equal-area Equal Earth projection without Antarctica, held at its own 2.31:1 proportions (up to 560 px tall; 2.05:1 on the home spotlight), never stretched. Countries are separated by thin borders in the floor colour. The colour scale clamps at the 5th and 95th percentiles; skewed metrics (GDP, GDP per capita, population) are coloured on a log scale. Hover outlines a country in gold with its glow and shows a tooltip with flag, value, year and rank; on the metric page a click adds the country to the line chart, and a fine pointer can zoom and pan. The legend under the map is a 10 px rounded colour bar labelled Worse/Better (or Lower/Higher) with the end values, the median under the middle of a diverging bar, and a No data swatch.

### Line Chart
One 2 px line per country with round caps, no point markers and no smoothing; hover thickens the line and dims the others. Each line ends in its 20×15 flag, with the country's name in Quiet Ink on wide charts (flag only below 560 px). Gridlines are Hairline, the x-axis line Strong Rule, axis labels Muted Ink, years in mono. Under the chart, series keys repeat each country as a pill (line swatch, flag, name, remove button), and "Show the numbers" opens a scrolling table with a mono year column and a sticky header.

### Tooltip
Card Slate with a Strong Rule border, 10 px corners and the tooltip shadow. A bold head with a flag, then the value in 800 at 1.125rem, then a Muted Ink line ("2024 · rank 3 of 215"). Line-chart tooltips list every country for the hovered year, sorted high to low, each with its colour swatch, flag and value.

### Logo
The gold-and-blue gear beside the wordmark (34 px) and in the footer (28 px) turns once every 7 s at a constant speed, and stops under reduced motion.

### About the Author
The closing card on every page: a 96 px round portrait ringed in gold at 55% over a floor-coloured gap, the condensed title, the bio in Quiet Ink up to 68ch, and stacked LinkedIn (outline) and GitHub (solid) pills. A hairline of gold, fading out at both ends, runs along its top edge.

### Named Rules
**The Source Above Rule.** Every chart carries its source line above it, between the chart's title and its well: who published the data, when they updated it, and when it was fetched.

**The Name First Rule.** Cards and the spotlight lead with the metric's name; its question sits under it as a smaller subtitle (Muted Ink on cards, Quiet Ink in the spotlight). No eyebrow or kicker label is ever placed above a heading.

**The Diverging Median Rule.** A metric with a better direction is mapped red to grey to blue, from worse to better, with grey at the median country of the year; a metric without one uses the single blue ramp. Countries without data are always #2a2c2f.

**The Kept Colour Rule.** Line colours are handed out in the fixed eight-colour order, and a country keeps its colour for as long as it stays selected; a freed colour goes to the next country added. At most eight countries plus World. World is always the dashed light grey line.

**The Ink-Only Chart Text Rule.** Chart text (axis labels, end labels, legends, tooltips) uses the ink tokens, never a series colour. Series colours appear only in lines, swatches and map fills.

## Do's and Don'ts

### Do:
- **Do** use Gear Gold (#ffd700) for every accent: primary buttons, value pills, the active nav link and series tab, focus glow and HUD corner ticks.
- **Do** head every card and the spotlight with the metric's name, with its question as a smaller subtitle beneath.
- **Do** put the source line (source, update date, fetch date) above every chart.
- **Do** set page titles, the home introduction headline, the spotlight title and section titles in Archivo at 75% width; keep card titles and body at normal width.
- **Do** write every number through the shared unit rules, in tabular figures, with an en dash for a missing value.
- **Do** keep a country's line colour while it stays selected, in the fixed eight-colour order, with World as the dashed #c9ccd0 line.
- **Do** keep the map at its own proportions, use the diverging ramp with the median at grey for metrics with a better direction, the blue ramp otherwise, and #2a2c2f for no data.
- **Do** stop the logo spin and slide animations under reduced motion.

### Don't:
- **Don't** introduce a second accent colour or any green or red in the interface, and don't use Kalshi's bright green for the title or anything else.
- **Don't** colour chart text with series colours.
- **Don't** place an eyebrow or kicker label above a heading; the question goes under the metric's name.
- **Don't** put resting shadows on cards; shadows belong only to dropdowns, the picker and tooltips.
- **Don't** let a glow be any colour but gold.
- **Don't** replace the page ground (#121416 with its faint 32 px grid) with flat black or a lighter grey.
- **Don't** square off controls: buttons, inputs, chips and value pills are full pills.
