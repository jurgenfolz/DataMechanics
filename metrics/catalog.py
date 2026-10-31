"""Every metric page the site publishes. The single source of truth for titles, descriptions, tags and series.

A metric reads one fact table in geo/models.py.
Its source and fetch date come from the table's latest row in etl_load, so the page always cites what was actually loaded.
Visible texts are written in English and translated through locale/ (see CLAUDE.md, Languages).
Slugs, fields and category keys stay English in every language: URLs and code use them.
"""

from dataclasses import dataclass, field

from django.utils import translation
from django.utils.translation import gettext_lazy as _, pgettext_lazy

from geo import models as geo

# Category keys and how each is named on the page.
CATEGORY_LABELS = {
    'Corruption': _('Corruption'),
    'Demography': _('Demography'),
    'Development': _('Development'),
    'Economy': _('Economy'),
    'Education': _('Education'),
    'Environment': _('Environment'),
    'Food': _('Food'),
    'Governance': _('Governance'),
    'Health': _('Health'),
    'Society': _('Society'),
}


@dataclass(frozen=True)
class Series:
    """One measure of a metric: a column of its fact table."""

    field: str
    label: str
    unit: str  # a key of metrics.formatting.UNITS
    better: str = ''  # 'higher', 'lower' or '' when neither is better
    log_scale: bool = False  # colour the map on a log scale (for very skewed values)
    short: str = ''  # tab label, when the full label is too long for a tab
    note: str = ''  # what sets this measure apart from the metric's others, shown under the measure tabs
    measured_in: str = ''  # what the values are in, for titles: 'current US$', '% of GDP', '0 to 1'
    total: bool = False  # the values add up across countries (GDP, population): Politics mode compares them with no group

    @property
    def tab_label(self):
        return self.short or self.label


@dataclass(frozen=True)
class Tags:
    """Search tags, from broad to narrow. See CLAUDE.md, Data design."""

    category: str  # a key of CATEGORY_LABELS
    subcategories: tuple[str, ...] = ()  # up to 4
    granularity: tuple[str, ...] = (_('Country'), _('Year'))  # up to 3

    @property
    def category_label(self):
        return CATEGORY_LABELS[self.category]

    def all(self):
        return [self.category_label, *self.subcategories, *self.granularity]


@dataclass(frozen=True)
class Metric:
    slug: str
    title: str
    question: str  # the question the metric answers, shown under its name on cards
    summary: str  # one line, for cards and search results
    description: str  # one paragraph: what it is, how it is measured, by whom
    model: type
    series: tuple[Series, ...]
    tags: Tags
    world_label: str = _('World')  # how the source's World aggregate is named
    keywords: tuple[str, ...] = field(default=())  # extra search words
    default_countries: tuple[str, ...] = ()  # countries the line chart opens with, when the site's usual ones don't suit
    opens_from: int = 0  # the first year the line chart opens with, when the address names none: centuries of data stay behind the slider

    @property
    def table(self):
        return self.model._meta.db_table

    def search_text(self):
        """The words search matches, in the active language and in English, so an English term finds a metric anywhere."""
        texts = [self._words()]
        with translation.override('en'):
            texts.append(self._words())
        return ' '.join(texts).lower()

    def _words(self):
        words = [self.title, self.summary, *self.tags.all(), *self.keywords, *(s.label for s in self.series)]
        return ' '.join(str(word) for word in words)


METRICS = (
    Metric(
        slug='gdp',
        title=_('GDP'),
        question=_('Which economies are the largest?'),
        summary=_('The total value of everything a country produces in a year, in US dollars.'),
        description=(
            _('Gross domestic product (GDP) is the total value of the goods and services produced in a country '
            'in a year. Each country\'s statistics office or central bank measures it from its national accounts, '
            'and the World Bank collects the figures and converts them to US dollars at each year\'s exchange rate. '
            'The values are in current dollars, not adjusted for inflation, so part of the growth over time is '
            'rising prices.')
        ),
        model=geo.GdpCountryYear,
        series=(Series('value', _('GDP'), 'usd', measured_in=pgettext_lazy('measured in', 'current US$'), log_scale=True, total=True),),
        tags=Tags('Economy', (_('GDP'), _('National accounts'))),
        keywords=(_('gross domestic product'), _('economy size'), _('output')),
    ),
    Metric(
        slug='gdp-per-capita',
        title=_('GDP per capita'),
        question=_('Where is output per person highest?'),
        summary=_('GDP divided by population: what a country produces per person.'),
        description=(
            _('GDP per capita is a country\'s GDP divided by its mid-year population: the value of goods and services '
            'produced per person. It is a common gauge of average living standards, but it says nothing about how '
            'income is shared. The World Bank computes it from national accounts and population estimates in two '
            'ways: in current US dollars at market exchange rates, and at purchasing power parity (PPP), which '
            'corrects for price differences between countries using the International Comparison Program\'s prices. '
            'PPP is the fairer way to compare living standards. Neither measure is adjusted for inflation over time.')
        ),
        model=geo.GdpPerCapitaCountryYear,
        series=(
            Series('value', _('GDP per capita'), 'usd', measured_in=pgettext_lazy('measured in', 'current US$'), better='higher', log_scale=True, short=_('Current US$'),
                   note=_('In current US dollars, converted at each year\'s market exchange rate. Prices differ between '
                          'countries, so a dollar does not buy the same everywhere.')),
            Series('ppp', _('GDP per capita, PPP (international $)'), 'usd', measured_in=pgettext_lazy('measured in', 'international $'), better='higher', log_scale=True, short=_('PPP'),
                   note=_('At purchasing power parity (PPP), in international dollars: a dollar that buys the same amount '
                          'of goods and services in every country, using the prices of the International Comparison '
                          'Program. This is the fairer way to compare living standards between countries.')),
        ),
        tags=Tags('Economy', (_('GDP'), _('Per capita'), _('Living standards'))),
        keywords=(_('income per person'), _('gdp per person'), _('wealth'), _('ppp'), _('purchasing power parity')),
    ),
    Metric(
        slug='democracy',
        title=_('Democracy indices (V-Dem)'),
        question=_('How democratic is each country?'),
        summary=_('Five V-Dem indices that rate how democratic a country is, from 0 to 1.'),
        description=(
            _('The Varieties of Democracy (V-Dem) project at the University of Gothenburg rates political regimes '
            'with five indices from 0 (least democratic) to 1 (most democratic). Each index captures one idea of '
            'democracy: free and fair elections (electoral), individual rights and limits on power (liberal), '
            'citizens taking part (participatory), decisions based on public reasoning (deliberative) and equal '
            'access to power across social groups (egalitarian). The scores combine the ratings of thousands of '
            'country experts through a statistical model. Our World in Data republishes the central estimates.')
        ),
        model=geo.DemocracyCountryYear,
        series=(
            Series('electoral', _('Electoral democracy'), 'index', measured_in=pgettext_lazy('measured in', '0 to 1'), better='higher', short=_('Electoral')),
            Series('liberal', _('Liberal democracy'), 'index', measured_in=pgettext_lazy('measured in', '0 to 1'), better='higher', short=_('Liberal')),
            Series('participatory', _('Participatory democracy'), 'index', measured_in=pgettext_lazy('measured in', '0 to 1'), better='higher', short=_('Participatory')),
            Series('deliberative', _('Deliberative democracy'), 'index', measured_in=pgettext_lazy('measured in', '0 to 1'), better='higher', short=_('Deliberative')),
            Series('egalitarian', _('Egalitarian democracy'), 'index', measured_in=pgettext_lazy('measured in', '0 to 1'), better='higher', short=_('Egalitarian')),
        ),
        tags=Tags('Governance', (_('Democracy'), _('V-Dem'), _('Elections'), _('Rights'))),
        world_label=_('World (average of countries)'),
        keywords=(_('vdem'), _('varieties of democracy'), _('polyarchy'), _('freedom'), _('regime')),
    ),
    Metric(
        slug='hdi',
        title=_('Human Development Index'),
        question=_('Where is human development highest?'),
        summary=_('A 0 to 1 score combining health, education and income.'),
        description=(
            _('The Human Development Index (HDI) sums up three basic dimensions of human development: a long and '
            'healthy life (life expectancy at birth), knowledge (mean and expected years of schooling) and a decent '
            'standard of living (gross national income per person, adjusted for price differences). Each dimension '
            'is scaled from 0 to 1, and the HDI is their geometric mean. The United Nations Development Programme '
            '(UNDP) publishes it every year in its Human Development Report; this data comes from the 2025 report.')
        ),
        model=geo.HdiCountryYear,
        series=(Series('value', _('Human Development Index'), 'index', measured_in=pgettext_lazy('measured in', '0 to 1'), better='higher'),),
        tags=Tags('Development', (_('Human development'), _('HDI'), _('UNDP'))),
        keywords=(_('human development index'), _('well-being'), _('undp')),
    ),
    Metric(
        slug='life-expectancy',
        opens_from=1800,
        title=_('Life expectancy'),
        question=_('Where do people live longest?'),
        summary=_('How many years a newborn would live if today\'s death rates held for life.'),
        description=(
            _('Life expectancy at birth is the number of years a newborn would live if the death rates of the year '
            'it was born stayed the same for its whole life. It describes the health of a population in that year; '
            'it is not a forecast for any one person. Our World in Data joins the UN Population Division\'s World '
            'Population Prospects, from 1950, with the Human Mortality Database and historical estimates by Riley '
            'and by Zijdeman and others, so the series reaches back to the 1800s for many countries. The figures for '
            'women and men come from the UN alone, from 1950.')
        ),
        model=geo.LifeExpectancyCountryYear,
        series=(
            Series('value', _('Life expectancy at birth'), 'years', measured_in=pgettext_lazy('measured in', 'years'), better='higher', short=_('Everyone')),
            Series('women', _('Life expectancy of women'), 'years', measured_in=pgettext_lazy('measured in', 'years'), better='higher', short=_('Women')),
            Series('men', _('Life expectancy of men'), 'years', measured_in=pgettext_lazy('measured in', 'years'), better='higher', short=_('Men')),
        ),
        tags=Tags('Health', (_('Life expectancy'), _('Mortality'))),
        keywords=(_('lifespan'), _('longevity'), _('age at death')),
    ),
    Metric(
        slug='schooling',
        title=_('Years of schooling'),
        question=_('How long do people stay in school?'),
        summary=_('Average years adults spent in school, and the years a child can expect today.'),
        description=(
            _('Mean years of schooling is the average number of years of education completed by people aged 25 and '
            'over. Expected years of schooling is how many years a child starting school can expect to spend in '
            'education if today\'s enrolment rates stay the same. The UNDP uses both in the Human Development Index '
            'and builds them from UNESCO Institute for Statistics data, Barro and Lee estimates and household '
            'surveys.')
        ),
        model=geo.SchoolingCountryYear,
        series=(
            Series('mean_years', _('Mean years of schooling'), 'years', measured_in=pgettext_lazy('measured in', 'years'), better='higher', short=_('Mean years')),
            Series('expected_years', _('Expected years of schooling'), 'years', measured_in=pgettext_lazy('measured in', 'years'), better='higher', short=_('Expected years')),
        ),
        tags=Tags('Education', (_('Schooling'), _('Mean years'), _('Expected years'))),
        keywords=(_('education'), _('school'), _('enrolment'), _('literacy')),
    ),
    Metric(
        slug='literacy-rate',
        title=_('Literacy rate'),
        question=_('Where can most adults read and write?'),
        summary=_('The share of people aged 15 and older who can read and write a simple sentence about their daily life.'),
        description=(
            _('The literacy rate is the share of people aged 15 and older who can read and write a simple sentence about '
            'their everyday life. Our World in Data combines historical estimates, back to the 15th century for some '
            'European countries, with recent figures from UNESCO and other sources. What counts as literate has varied '
            'between countries and over time, so compare with care. Many rich countries stopped tracking literacy in the '
            'late 20th century, once nearly everyone could read, so their series end early. It measures basic literacy, '
            'not whether people can follow complex written texts.')
        ),
        model=geo.LiteracyCountryYear,
        series=(Series('value', _('Adult literacy rate'), 'percent', measured_in=pgettext_lazy('measured in', '% of adults'), better='higher'),),
        tags=Tags('Education', (_('Literacy'), _('Reading'), _('UNESCO'))),
        keywords=(_('literacy'), _('illiteracy'), _('reading'), _('writing')),
        # Rich countries' series end around 1950 and some start in 1475; these run from about 1900 to today.
        default_countries=('BRA', 'MEX', 'IND', 'EGY', 'TUR'),
    ),
    Metric(
        slug='education-spending',
        title=_('Government spending on education'),
        question=_('Which governments spend the most on education?'),
        summary=_('What governments spend on education at every level, as a share of GDP.'),
        description=(
            _("This is what a country's central, regional and local governments spend on education at every level in a "
            'year, as a share of GDP. It includes salaries, textbooks, buildings and donor money that passes through the '
            'budget. Recent figures come from UNESCO; older ones from records such as League of Nations yearbooks and '
            'OECD reports, which differ in method, so read them with care. A higher share means more of the economy goes '
            'to education, not more per student or better results. Our World in Data combines the sources.')
        ),
        model=geo.EducationSpendingCountryYear,
        series=(Series('value', _('Education spending, % of GDP'), 'percent', measured_in=pgettext_lazy('measured in', '% of GDP')),),
        tags=Tags('Education', (_('Education spending'), _('Public finance'), _('UNESCO'))),
        keywords=(_('education budget'), _('school funding'), _('public spending'), _('unesco')),
    ),
    Metric(
        slug='scientific-articles',
        title=_('Scientific and technical articles'),
        question=_('Which countries publish the most science?'),
        summary=_('Articles in science and engineering journals and conference proceedings, per year.'),
        description=(
            _('This counts the articles from each country published each year in peer-reviewed journals and conference '
            'proceedings in science and engineering, from physics, biology and chemistry to clinical medicine, '
            'engineering and earth and space sciences. The US National Science Foundation compiles the counts from the '
            'Scopus database, and the World Bank republishes them. Big countries publish more partly because they are '
            'big, so compare countries of a similar size, or follow one country over time.')
        ),
        model=geo.ScientificArticlesCountryYear,
        series=(Series('value', _('Articles per year'), 'count', measured_in=pgettext_lazy('measured in', 'articles a year'), log_scale=True, total=True),),
        tags=Tags('Education', (_('Science'), _('Research'), _('Publications'))),
        keywords=(_('research'), _('papers'), _('publications'), _('science')),
    ),
    Metric(
        slug='population',
        title=_('Population, births and deaths'),
        question=_('Where are populations growing?'),
        summary=_('How many people live in each country, how many are born and die, and how many move in or out.'),
        description=(
            _('Population counts everyone who lives in a country at mid-year, whatever their legal status or '
            'citizenship. The birth rate and the death rate are the live births and the deaths in a year per '
            '1,000 people. When births outnumber deaths a population grows naturally; migration changes it too. '
            'Net migration is the number of people who moved into the country in the year minus those who left, '
            'citizens and non-citizens alike. The World Bank compiles these figures mainly from the UN Population '
            'Division\'s World Population Prospects, which combines censuses, civil registration and surveys.')
        ),
        model=geo.PopulationCountryYear,
        series=(
            Series('population', _('Population'), 'people', measured_in=pgettext_lazy('measured in', 'people'), log_scale=True, total=True),
            Series('birth_rate', _('Births per 1,000 people'), 'per_1000', measured_in=pgettext_lazy('measured in', 'per 1,000 people')),
            Series('death_rate', _('Deaths per 1,000 people'), 'per_1000', measured_in=pgettext_lazy('measured in', 'per 1,000 people')),
            Series('net_migration', _('Net migration'), 'people', measured_in=pgettext_lazy('measured in', 'people a year'), total=True),
        ),
        tags=Tags('Demography', (_('Population'), _('Births'), _('Deaths'), _('Birth rate'))),
        keywords=(_('people'), _('inhabitants'), _('mortality'), _('death rate'), _('demographics'), _('migration'), _('immigration'), _('emigration'), _('migrants')),
    ),
    Metric(
        slug='unemployment',
        title=_('Unemployment rate'),
        question=_('Where is unemployment highest?'),
        summary=_('The share of the labour force without a job but looking for one.'),
        description=(
            _('The unemployment rate is the share of the labour force that has no job but is available for and '
            'looking for work. The labour force is everyone of working age who has a job or is looking for one. '
            'These are modelled estimates from the International Labour Organization (ILO), which fills gaps in '
            'national labour force surveys so that countries can be compared. The World Bank republishes them.')
        ),
        model=geo.UnemploymentCountryYear,
        series=(Series('value', _('Unemployment rate'), 'percent', measured_in=pgettext_lazy('measured in', '% of the labour force'), better='lower'),),
        tags=Tags('Economy', (_('Labour market'), _('Unemployment'), _('ILO'))),
        keywords=(_('jobs'), _('jobless'), _('employment'), _('labor')),
    ),
    Metric(
        slug='government-debt',
        title=_('Government debt'),
        question=_('Which governments owe the most?'),
        summary=_('Everything a country\'s governments owe, as a share of its GDP.'),
        description=(
            _('General government gross debt is everything a country\'s governments owe: central, state and local '
            'government and social security funds together. It covers loans, bonds and other liabilities that must '
            'be repaid with interest, and is shown as a share of GDP so that countries of different sizes can be '
            'compared. The International Monetary Fund (IMF) publishes it in its World Economic Outlook. We show '
            'past years only and leave out the IMF\'s forecasts; the latest year can still be an IMF estimate.')
        ),
        model=geo.GovernmentDebtCountryYear,
        series=(Series('value', _('Gross debt, % of GDP'), 'percent', measured_in=pgettext_lazy('measured in', '% of GDP'), better='lower'),),
        tags=Tags('Economy', (_('Public finance'), _('Government debt'), _('IMF'))),
        keywords=(_('public debt'), _('national debt'), _('deficit'), _('borrowing'), _('debt to gdp')),
    ),
    Metric(
        slug='interest-payments',
        title=_('Interest on government debt'),
        question=_('Where does debt cost governments the most?'),
        summary=_('The share of government revenue that goes to paying interest on its debt.'),
        description=(
            _('This is the interest a central government pays on its debt in a year, as a share of the revenue it '
            'collects: how much of every tax dollar goes to its lenders before it pays for anything else. It covers '
            'interest on bonds, loans and other debt, to lenders at home and abroad. It shows how heavy a debt is to '
            'carry, which the size of the debt alone does not: it also depends on interest rates and on how much '
            'the government collects. The IMF compiles the figures, and the World Bank publishes them.')
        ),
        model=geo.InterestPaymentsCountryYear,
        series=(Series('value', _('Interest payments, % of revenue'), 'percent',
                       measured_in=pgettext_lazy('measured in', '% of revenue'), better='lower'),),
        tags=Tags('Economy', (_('Public finance'), _('Government debt'), _('World Bank'))),
        keywords=(_('debt interest'), _('debt service'), _('interest burden'), _('public debt')),
    ),
    Metric(
        slug='budget-balance',
        title=_('Government budget balance'),
        question=_('Which governments spend more than they collect?'),
        summary=_('What governments collect minus what they spend, as a share of GDP: below zero is a deficit.'),
        description=(
            _("The budget balance is a country's government revenue minus its spending, interest included, as a share "
            'of GDP. Above zero is a surplus; below zero is a deficit, which the government covers by borrowing, so '
            'its debt grows. It covers central, state and local government and social security funds together. The '
            'International Monetary Fund (IMF) publishes it in its World Economic Outlook. We show past years only and '
            "leave out the IMF's forecasts; the latest year can still be an IMF estimate.")
        ),
        model=geo.BudgetBalanceCountryYear,
        series=(Series('value', _('Budget balance, % of GDP'), 'percent',
                       measured_in=pgettext_lazy('measured in', '% of GDP'), better='higher'),),
        tags=Tags('Economy', (_('Public finance'), _('Budget deficit'), _('IMF'))),
        keywords=(_('deficit'), _('surplus'), _('fiscal balance'), _('net borrowing')),
    ),
    Metric(
        slug='primary-balance',
        title=_('Primary balance'),
        question=_('Which governments live within their means, before interest?'),
        summary=_('The budget balance before interest on the debt, as a share of GDP.'),
        description=(
            _('The primary balance is the budget balance without the interest on the debt: what a government collects '
            'minus what it spends on everything else, as a share of GDP. It shows whether a government lives within its '
            'means today, apart from the cost of its old debt. A country with a primary surplus and a deficit overall '
            'borrows only to pay interest. The International Monetary Fund (IMF) publishes it in its Fiscal Monitor. '
            "We show past years only and leave out the IMF's forecasts.")
        ),
        model=geo.PrimaryBalanceCountryYear,
        series=(Series('value', _('Primary balance, % of GDP'), 'percent',
                       measured_in=pgettext_lazy('measured in', '% of GDP'), better='higher'),),
        tags=Tags('Economy', (_('Public finance'), _('Budget deficit'), _('IMF'))),
        keywords=(_('primary deficit'), _('primary surplus'), _('fiscal balance'), _('deficit')),
    ),
    Metric(
        slug='government-spending',
        title=_('Government spending'),
        question=_('Which governments spend the most?'),
        summary=_('Everything the government spends in a year, interest on its debt included, as a share of GDP.'),
        description=(
            _('This is everything a government spends in a year, including the interest on its debt, as a share of '
            "GDP. The IMF's Public Finances in Modern History database gathers 200 years of it from historical "
            'records. Depending on the country and year, it covers the central government only, or also the states '
            'and local authorities, so compare with care. Our World in Data republishes it.')
        ),
        model=geo.GovernmentSpendingCountryYear,
        series=(Series('value', _('Government spending, % of GDP'), 'percent', measured_in=pgettext_lazy('measured in', '% of GDP')),),
        tags=Tags('Economy', (_('Government spending'), _('Public finance'), _('IMF'))),
        keywords=(_('public spending'), _('government expenditure'), _('budget'), _('size of government')),
    ),
    Metric(
        slug='inflation',
        title=_('Inflation'),
        question=_('Where are prices rising fastest?'),
        summary=_('How fast consumer prices rise each year.'),
        description=(
            _('Inflation is how fast consumer prices rise: the yearly percentage change in what an average household '
            'pays for a basket of goods and services, measured by the consumer price index. National statistics '
            'offices collect the prices, the International Monetary Fund compiles the figures, and the World Bank '
            'republishes them. A few percent a year is normal. Very high rates erode wages and savings, while '
            'falling prices (deflation) can be a sign of a weak economy.')
        ),
        model=geo.InflationCountryYear,
        series=(Series('value', _('Inflation, consumer prices'), 'percent', measured_in=pgettext_lazy('measured in', '% a year')),),
        tags=Tags('Economy', (_('Prices'), _('Inflation'), _('Consumer price index'))),
        keywords=(_('cpi'), _('cost of living'), _('price rises'), _('deflation')),
        default_countries=('USA', 'CHN', 'IND', 'DEU', 'JPN'),
    ),
    Metric(
        slug='gdp-growth',
        title=_('GDP growth'),
        question=_('Which economies are growing fastest?'),
        summary=_('How much more an economy produced than the year before, after inflation.'),
        description=(
            _('GDP growth is the yearly percentage change in a country\'s GDP after removing the effect of price '
            'changes, so it shows how much more the economy really produced than the year before. The World Bank '
            'computes it from national accounts at constant 2015 prices. A negative value means the economy shrank, '
            'as it did in many countries in 2020.')
        ),
        model=geo.GdpGrowthCountryYear,
        series=(Series('value', _('Real GDP growth'), 'percent', measured_in=pgettext_lazy('measured in', '% a year'), better='higher'),),
        tags=Tags('Economy', (_('GDP'), _('Growth'), _('Recession'))),
        keywords=(_('economic growth'), _('real gdp'), _('recession')),
    ),
    Metric(
        slug='labour-productivity',
        title=_('Productivity: output per hour worked'),
        question=_('Where does an hour of work produce the most?'),
        summary=_('GDP per hour worked: what an hour of work produces, adjusted for prices.'),
        description=(
            _('Labour productivity is GDP divided by all the hours worked in the economy: what an hour of work '
            'produces. It is adjusted for inflation and for differences in living costs between countries, and given '
            'in international dollars at 2021 prices. The Penn World Table (Feenstra and others, University of '
            'Groningen) compiles it, and Our World in Data republishes it.')
        ),
        model=geo.LabourProductivityCountryYear,
        series=(Series('value', _('Output per hour worked'), 'usd', measured_in=pgettext_lazy('measured in', 'international $ an hour'),
                       better='higher', log_scale=True),),
        tags=Tags('Economy', (_('Productivity'), _('Labour'), _('Penn World Table'))),
        keywords=(_('productivity'), _('output per hour'), _('working hours'), _('efficiency')),
    ),
    Metric(
        slug='tax-revenue',
        title=_('Tax revenue'),
        question=_('Which governments collect the most in taxes?'),
        summary=_('Taxes collected by the central government, as a share of GDP.'),
        description=(
            _('Tax revenue is what a country\'s central government collects in compulsory payments such as taxes on '
            'income, profits, goods and services and trade, shown as a share of GDP. Fines, penalties and most social '
            'security contributions are not counted. The International Monetary Fund compiles the figures from '
            'government finance statistics, and the World Bank republishes them.')
        ),
        model=geo.TaxRevenueCountryYear,
        series=(Series('value', _('Tax revenue, % of GDP'), 'percent', measured_in=pgettext_lazy('measured in', '% of GDP')),),
        tags=Tags('Economy', (_('Public finance'), _('Taxes'))),
        keywords=(_('taxation'), _('tax burden'), _('government revenue')),
    ),
    Metric(
        slug='trade',
        title=_('Trade'),
        question=_('Which economies trade the most?'),
        summary=_('Exports plus imports, as a share of GDP.'),
        description=(
            _('Trade is the sum of a country\'s exports and imports of goods and services, shown as a share of its '
            'GDP. Small, open economies often trade more than their whole GDP in a year, partly because goods pass '
            'through them on the way elsewhere, while large economies trade less relative to their size. The World '
            'Bank computes it from national accounts.')
        ),
        model=geo.TradeCountryYear,
        series=(Series('value', _('Trade, % of GDP'), 'percent', measured_in=pgettext_lazy('measured in', '% of GDP')),),
        tags=Tags('Economy', (_('Trade'), _('Exports'), _('Imports'))),
        keywords=(_('openness'), _('globalisation'), _('globalization'), _('exports'), _('imports')),
    ),
    Metric(
        slug='women-in-the-labour-force',
        title=_('Women in the labour force'),
        question=_('Where do most women work or look for work?'),
        summary=_('The share of women aged 15 and over who have a job or are looking for one.'),
        description=(
            _('The female labour force participation rate is the share of women aged 15 and over who are in the labour '
            'force: those who have a job and those who are looking for one. These are modelled estimates from the '
            'International Labour Organization (ILO), which fills gaps in national labour force surveys so that '
            'countries can be compared. The World Bank republishes them.')
        ),
        model=geo.FemaleLabourCountryYear,
        series=(Series('value', _('Female labour force participation'), 'percent', measured_in=pgettext_lazy('measured in', '% of women'), better='higher'),),
        tags=Tags('Economy', (_('Labour market'), _('Gender'), _('ILO'))),
        keywords=(_('female employment'), _('women working'), _('gender gap'), _('labor force participation')),
    ),
    Metric(
        slug='fertility-rate',
        title=_('Fertility rate'),
        question=_('How many children do women have?'),
        summary=_('The number of children a woman would have at this year\'s birth rates.'),
        description=(
            _('The total fertility rate is the number of children a woman would have over her life if, at each age, '
            'she had children at the rates of that year. In countries where few children die young, about 2.1 '
            'children per woman keeps a population stable in the long run, without migration. The World Bank '
            'publishes it mainly from the UN Population Division\'s World Population Prospects.')
        ),
        model=geo.FertilityCountryYear,
        series=(Series('value', _('Births per woman'), 'per_woman', measured_in=pgettext_lazy('measured in', 'births per woman')),),
        tags=Tags('Demography', (_('Fertility'), _('Births'))),
        keywords=(_('birth rate'), _('children per woman'), _('total fertility rate'), _('tfr')),
    ),
    Metric(
        slug='median-age',
        title=_('Median age'),
        question=_('Where are populations oldest?'),
        summary=_('The age that splits a population in two: half younger, half older.'),
        description=(
            _('The median age splits a population in two: half the people are younger and half are older. It is a '
            'simple measure of how old a population is. The UN Population Division estimates it in its World '
            'Population Prospects from censuses, surveys and registers, and Our World in Data republishes the '
            'estimates. The UN\'s projections for future years are left out.')
        ),
        model=geo.MedianAgeCountryYear,
        series=(Series('value', _('Median age'), 'years', measured_in=pgettext_lazy('measured in', 'years')),),
        tags=Tags('Demography', (_('Ageing'), _('Age structure'))),
        keywords=(_('aging'), _('ageing'), _('old population'), _('average age')),
    ),
    Metric(
        slug='child-mortality',
        opens_from=1800,
        title=_('Child mortality'),
        question=_('Where do most children die before age five?'),
        summary=_('Deaths before age five, per 1,000 live births.'),
        description=(
            _('The under-five mortality rate is the probability that a newborn baby dies before turning five, per '
            '1,000 live births, if the death rates of that year held. The UN Inter-agency Group for Child Mortality '
            'Estimation (UNICEF, the WHO, the World Bank and the UN Population Division) produces the estimates from '
            'surveys, censuses and vital registration. Our World in Data joins them with Gapminder\'s historical '
            'estimates, so the series reaches back to the 1800s for many countries, and to 1751 for Sweden.')
        ),
        model=geo.ChildMortalityCountryYear,
        series=(Series('value', _('Deaths before age 5 per 1,000 live births'), 'per_1000', measured_in=pgettext_lazy('measured in', 'per 1,000 births'), better='lower'),),
        tags=Tags('Health', (_('Child mortality'), _('Mortality'), _('UNICEF'))),
        keywords=(_('under-5 mortality'), _('infant deaths'), _('child deaths')),
    ),
    Metric(
        slug='obesity',
        title=_('Obesity'),
        question=_('Where is obesity most common?'),
        summary=_('The share of adults with a body mass index of 30 or more.'),
        description=(
            _('This is the share of adults aged 18 and over with obesity, meaning a body mass index (BMI) of 30 or '
            'more. The World Health Organization estimates it from national surveys and adjusts it for age, so that '
            'countries with older or younger populations can be compared. Our World in Data republishes it. The WHO '
            'licenses this data under CC BY-NC-SA 4.0: free for non-commercial use, and copies keep the same licence.')
        ),
        model=geo.ObesityCountryYear,
        series=(Series('value', _('Adults with obesity'), 'percent', measured_in=pgettext_lazy('measured in', '% of adults'), better='lower'),),
        tags=Tags('Health', (_('Obesity'), _('Nutrition'), _('WHO'))),
        keywords=(_('overweight'), _('bmi'), _('body mass index')),
    ),
    Metric(
        slug='health-spending',
        title=_('Health spending'),
        question=_('Where is most spent on health per person?'),
        summary=_('What a country spends on healthcare per person in a year, in US dollars.'),
        description=(
            _('Current health expenditure per person covers the healthcare goods and services a country consumes in a '
            'year, whether governments, insurers or households pay for them, in current US dollars. Investment in '
            'buildings and equipment is not included. The World Health Organization compiles it in its Global Health '
            'Expenditure Database, and the World Bank republishes it.')
        ),
        model=geo.HealthSpendingCountryYear,
        series=(Series('value', _('Health spending per person'), 'usd', measured_in=pgettext_lazy('measured in', 'US$ per person'), log_scale=True),),
        tags=Tags('Health', (_('Health spending'), _('Healthcare'), _('WHO'))),
        keywords=(_('healthcare cost'), _('health expenditure'), _('medical spending')),
    ),
    Metric(
        slug='extreme-poverty',
        title=_('Extreme poverty'),
        question=_('Where do most people live on under $3 a day?'),
        summary=_('The share of people living on less than $3.00 a day.'),
        description=(
            _('This is the share of people living on less than $3.00 a day, the World Bank\'s international poverty '
            'line, at 2021 prices adjusted for differences in purchasing power between countries. The World Bank\'s '
            'Poverty and Inequality Platform builds it from household surveys run by national statistics offices. '
            'Surveys are not held every year, so many countries have gaps between years.')
        ),
        model=geo.PovertyCountryYear,
        series=(Series('value', _('Living on under $3.00 a day'), 'percent', measured_in=pgettext_lazy('measured in', '% of people'), better='lower'),),
        tags=Tags('Development', (_('Poverty'), _('Income'))),
        keywords=(_('poor'), _('poverty line'), _('extreme poverty'), _('living on')),
    ),
    Metric(
        slug='mean-income',
        title=_('Mean income or consumption'),
        question=_('How much do people live on each day?'),
        summary=_('The average income or consumption per person per day, adjusted for prices.'),
        description=(
            _('This is the average income or consumption per person per day, adjusted for inflation and for '
            "differences in living costs between countries, in international dollars at 2021 prices. The World Bank's "
            'Poverty and Inequality Platform builds it from national household surveys. Rich countries measure income '
            'after taxes and benefits; most low- and middle-income countries measure consumption instead, including '
            'food people grow for themselves. Surveys change over time, so some years compare less well. Our World in '
            'Data republishes the figures.')
        ),
        model=geo.MeanIncomeCountryYear,
        series=(Series('value', _('Mean income or consumption per day'), 'usd', measured_in=pgettext_lazy('measured in', 'international $ a day'),
                       better='higher', log_scale=True),),
        tags=Tags('Development', (_('Income'), _('Living standards'), _('World Bank'))),
        keywords=(_('income'), _('consumption'), _('living standards'), _('average income')),
    ),
    Metric(
        slug='income-inequality',
        title=_('Income inequality (Gini)'),
        question=_('Where is income most unequal?'),
        summary=_('The Gini index, from 0 (everyone has the same) to 100 (one person has everything).'),
        description=(
            _('The Gini index measures how unequally income, or in some countries consumption, is shared among a '
            'country\'s people, from 0 (everyone has the same) to 100 (one person has everything). The World Bank\'s '
            'Poverty and Inequality Platform computes it from household surveys. Surveys are not held every year, so '
            'many countries have gaps between years.')
        ),
        model=geo.InequalityCountryYear,
        series=(Series('value', _('Gini index'), 'points', measured_in=pgettext_lazy('measured in', '0 to 100'), better='lower'),),
        tags=Tags('Development', (_('Inequality'), _('Income'), _('Gini'))),
        keywords=(_('gini coefficient'), _('income distribution'), _('inequality')),
    ),
    Metric(
        slug='top-income-share',
        title=_('Income share of the richest 1%'),
        question=_('Where do the richest 1% take the biggest share?'),
        summary=_('The share of all income that goes to the richest 1% of people, before taxes and benefits.'),
        description=(
            _('This is the share of all income that goes to the richest 1% of people, measured before taxes and '
            'benefits. If income were shared equally, the richest 1% would get 1% of it. The World Inequality Database '
            '(WID.world) combines tax records, surveys and national accounts to capture the incomes at the very top, '
            'which surveys alone tend to miss. Our World in Data republishes the figures.')
        ),
        model=geo.TopIncomeShareCountryYear,
        series=(Series('value', _('Income share of the richest 1%'), 'percent', measured_in=pgettext_lazy('measured in', '% of income'),
                       better='lower'),),
        tags=Tags('Development', (_('Inequality'), _('Top incomes'), _('WID.world'))),
        keywords=(_('top 1%'), _('richest'), _('inequality'), _('wealth gap')),
    ),
    Metric(
        slug='life-satisfaction',
        title=_('Life satisfaction'),
        question=_('Where are people happiest with their lives?'),
        summary=_('How people rate their own lives, from 0 (worst possible) to 10 (best possible).'),
        description=(
            _('Life satisfaction is the average answer to one survey question: imagine a ladder where 10 is the best '
            'possible life for you and 0 the worst; on which step do you stand now? Gallup asks it in its World Poll, '
            'usually of about 1,000 people per country a year, and the World Happiness Report publishes the results '
            'from the Wellbeing Research Centre at the University of Oxford. Our World in Data republishes them.')
        ),
        model=geo.LifeSatisfactionCountryYear,
        series=(Series('value', _('Life satisfaction (0 to 10)'), 'score', measured_in=pgettext_lazy('measured in', '0 to 10'), better='higher'),),
        tags=Tags('Society', (_('Happiness'), _('Well-being'), _('World Happiness Report'))),
        keywords=(_('happiness'), _('happiest countries'), _('wellbeing'), _('cantril ladder')),
    ),
    Metric(
        slug='homicide-rate',
        title=_('Homicide rate'),
        question=_('Where are homicide rates highest?'),
        summary=_('Intentional killings per 100,000 people.'),
        description=(
            _('The homicide rate counts intentional homicides per 100,000 people: unlawful killings meant to cause death '
            'or serious injury. The UN Office on Drugs and Crime (UNODC) collects the figures from national police '
            'and health records, and the World Bank republishes them. Countries record deaths differently, so small '
            'differences between them are uncertain.')
        ),
        model=geo.HomicideCountryYear,
        series=(Series('value', _('Homicides per 100,000 people'), 'per_100k', measured_in=pgettext_lazy('measured in', 'per 100,000 people'), better='lower', log_scale=True),),
        tags=Tags('Society', (_('Crime'), _('Violence'), _('UNODC'))),
        keywords=(_('murder rate'), _('crime'), _('safety'), _('violence')),
    ),
    Metric(
        slug='gender-wage-gap',
        title=_('Gender wage gap'),
        question=_("Where is the gap between men's and women's pay widest?"),
        summary=_("How much less women earn than men on average, as a share of men's earnings."),
        description=(
            _("The gender wage gap is the difference between men's and women's average hourly earnings, as a share of "
            "men's earnings. A positive gap means men earn more; a negative one means women do. It is unadjusted: it "
            'does not account for education, experience or the kind of job, so it reflects both unequal pay for similar '
            'work and the different jobs men and women hold. It covers employees only, not the self-employed. The '
            'International Labour Organization compiles it from national surveys, which differ, so compare countries '
            'with care. Our World in Data leaves out the figures the ILO flags as unreliable.')
        ),
        model=geo.GenderWageGapCountryYear,
        series=(Series('value', _('Gender wage gap'), 'percent', measured_in=pgettext_lazy('measured in', "% of men's pay"), better='lower'),),
        tags=Tags('Society', (_('Gender'), _('Wages'), _('ILO'))),
        keywords=(_('pay gap'), _('equal pay'), _('women'), _('earnings')),
    ),
    Metric(
        slug='women-political-empowerment',
        title=_("Women's political empowerment index (V-Dem)"),
        question=_('Where do women have the most political power?'),
        summary=_('How far women enjoy civil liberties, take part in civil society and are represented in politics, from 0 to 1.'),
        description=(
            _("The V-Dem women's political empowerment index measures how far women enjoy civil liberties, can take part "
            'in civil society and are represented in politics. It runs from 0 (least empowered) to 1 (most empowered) '
            "and is made up of three sub-indices: women's civil liberties, women's civil society participation and "
            "women's political participation. It rests mainly on the ratings of V-Dem's country experts, combined "
            'through a statistical model, and also uses the share of women in parliament. Our World in Data republishes '
            'the central estimates.')
        ),
        model=geo.WomenPoliticalEmpowermentCountryYear,
        series=(Series('value', _("Women's political empowerment index"), 'index', measured_in=pgettext_lazy('measured in', '0 to 1'), better='higher'),),
        tags=Tags('Society', (_('Gender'), _("Women's rights"), _('V-Dem'))),
        world_label=_('World (average of countries)'),
        keywords=(_('women'), _('gender equality'), _('vdem'), _('empowerment')),
    ),
    Metric(
        slug='women-in-parliament',
        title=_('Share of women in parliament'),
        question=_('Where do women hold the most seats in parliament?'),
        summary=_('The share of seats in the lower or only chamber of parliament held by women.'),
        description=(
            _("This is the share of seats in the lower or only chamber of a country's parliament held by women. V-Dem "
            'compiles it from sources such as the Inter-Parliamentary Union, and Our World in Data republishes it. The '
            'World value is the average of the countries, each counted once.')
        ),
        model=geo.WomenInParliamentCountryYear,
        series=(Series('value', _('Women in parliament'), 'percent', measured_in=pgettext_lazy('measured in', '% of seats'), better='higher'),),
        tags=Tags('Society', (_('Gender'), _('Parliament'), _('V-Dem'))),
        world_label=_('World (average of countries)'),
        keywords=(_('women'), _('parliament'), _('representation'), _('legislators')),
    ),
    Metric(
        slug='undernourishment',
        title=_('Undernourishment'),
        question=_('Where is hunger most common?'),
        summary=_('The share of people whose food does not give them the minimum energy they need.'),
        description=(
            _('This is the share of people whose usual diet does not give them enough calories to meet their minimum '
            'energy needs. The Food and Agriculture Organization of the United Nations (FAO) estimates it for each '
            'country from national food supply, food consumption surveys and population data, as an average over '
            'three years, and the World Bank republishes it. The FAO publishes no share below 2.5%: those years show '
            'as 2.5%, which means 2.5% or less. Its current estimates start in 2001.')
        ),
        model=geo.UndernourishmentCountryYear,
        series=(Series('value', _('Undernourished, % of population'), 'percent', better='lower',
                       measured_in=pgettext_lazy('measured in', '% of population')),),
        tags=Tags('Food', (_('Hunger'), _('Nutrition'), _('FAO'))),
        keywords=(_('hunger'), _('malnutrition'), _('food security'), _('fao')),
    ),
    Metric(
        slug='healthy-diet-unaffordable',
        title=_('People who cannot afford a healthy diet'),
        question=_('Where is a healthy diet out of reach?'),
        summary=_('The share of people whose income cannot pay for the cheapest healthy diet and basic needs.'),
        description=(
            _("This is the share of people who cannot afford the cheapest healthy diet in their country: the lowest-cost "
            "set of foods that meets the dietary guidelines of governments and public health agencies. A diet counts as "
            'unaffordable when its cost, plus basic non-food needs such as housing and transport, is more than daily '
            'income. FAO and the World Bank compute it with methods from Bai et al. (2024), and Our World in Data '
            'republishes it.')
        ),
        model=geo.HealthyDietUnaffordableCountryYear,
        series=(Series('value', _('Cannot afford a healthy diet'), 'percent', measured_in=pgettext_lazy('measured in', '% of people'), better='lower'),),
        tags=Tags('Food', (_('Food prices'), _('Nutrition'), _('World Bank'))),
        keywords=(_('food prices'), _('cost of a healthy diet'), _('affordability'), _('hunger')),
    ),
    Metric(
        slug='meat-production',
        title=_('Meat production'),
        question=_('Which countries produce the most meat?'),
        summary=_('Meat produced in a year, in tonnes: cattle, poultry, pigs, sheep, goats and game.'),
        description=(
            _('This is the meat a country produces in a year, in tonnes, from cattle, poultry, pigs, sheep, goats and '
            'wild game. The Food and Agriculture Organization of the United Nations (FAO) compiles it, and Our World in '
            'Data republishes it.')
        ),
        model=geo.MeatProductionCountryYear,
        series=(Series('value', _('Meat production'), 'tonnes_total', measured_in=pgettext_lazy('measured in', 'tonnes'), log_scale=True, total=True),),
        tags=Tags('Food', (_('Meat'), _('Agriculture'), _('FAO'))),
        keywords=(_('meat'), _('livestock'), _('beef'), _('chicken'), _('pork')),
    ),
    Metric(
        slug='human-rights',
        title=_('Human rights index (V-Dem)'),
        question=_('Where are civil liberties best protected?'),
        summary=_('How free people are from state violence, and how far they enjoy basic freedoms, from 0 to 1.'),
        description=(
            _('The V-Dem human rights index measures how free people are from government torture, political killings '
            'and forced labour, and how far they enjoy property rights and the freedoms of movement, religion, '
            'expression and association. It runs from 0 (least free) to 1 (most free) and, like the V-Dem democracy '
            'indices, combines the ratings of thousands of country experts through a statistical model. Our World in '
            'Data republishes the central estimates.')
        ),
        model=geo.HumanRightsCountryYear,
        series=(Series('value', _('Human rights index'), 'index', measured_in=pgettext_lazy('measured in', '0 to 1'), better='higher'),),
        tags=Tags('Governance', (_('Human rights'), _('Civil liberties'), _('V-Dem'))),
        world_label=_('World (average of countries)'),
        keywords=(_('civil liberties'), _('freedom'), _('vdem'), _('repression')),
    ),
    Metric(
        slug='political-corruption',
        title=_('Political corruption index (V-Dem)'),
        question=_('Where is political corruption most widespread?'),
        summary=_('How far leaders and officials take bribes and steal public money, from 0 (least corrupt) to 1 (most corrupt).'),
        description=(
            _('The V-Dem political corruption index measures how far a country\'s government, parliament, courts and '
            'public officials take bribes or steal public money, and how far corruption shapes how laws are made and '
            'carried out. It runs from 0 (least corrupt) to 1 (most corrupt) and is made up of four sub-indices: '
            'executive, legislative, judicial and public sector corruption. Like the other V-Dem indices, it combines '
            'the ratings of thousands of country experts through a statistical model. It is about bribery and theft at '
            'high levels, not the corruption people meet in daily life. Our World in Data republishes the central '
            'estimates.')
        ),
        model=geo.PoliticalCorruptionCountryYear,
        series=(Series('value', _('Political corruption index'), 'index', measured_in=pgettext_lazy('measured in', '0 to 1'), better='lower'),),
        tags=Tags('Corruption', (_('Bribery'), _('Embezzlement'), _('V-Dem'))),
        keywords=(_('corruption'), _('bribery'), _('embezzlement'), _('vdem')),
    ),
    Metric(
        slug='executive-corruption',
        title=_('Executive corruption index (V-Dem)'),
        question=_('Where do leaders and ministers take the most bribes?'),
        summary=_('How far heads of government and ministers take bribes or steal public money, from 0 (least corrupt) to 1 (most corrupt).'),
        description=(
            _('The V-Dem executive corruption index measures how far high-ranking members of the executive, such as the '
            'head of government and cabinet ministers, take bribes or steal public money. It runs from 0 (least '
            'corrupt) to 1 (most corrupt) and is one of the four parts of the political corruption index. Like the '
            'other V-Dem indices, it combines the ratings of thousands of country experts through a statistical model. '
            'Our World in Data republishes the central estimates.')
        ),
        model=geo.ExecutiveCorruptionCountryYear,
        series=(Series('value', _('Executive corruption index'), 'index', measured_in=pgettext_lazy('measured in', '0 to 1'), better='lower'),),
        tags=Tags('Corruption', (_('Executive'), _('Bribery'), _('V-Dem'))),
        keywords=(_('corruption'), _('government corruption'), _('ministers'), _('vdem')),
    ),
    Metric(
        slug='public-sector-corruption',
        title=_('Public sector corruption index (V-Dem)'),
        question=_('Where do public officials take the most bribes?'),
        summary=_('How far public sector employees take bribes or steal public money, from 0 (least corrupt) to 1 (most corrupt).'),
        description=(
            _('The V-Dem public sector corruption index measures how far public sector employees take bribes or steal '
            'public money. It runs from 0 (least corrupt) to 1 (most corrupt) and is one of the four parts of the '
            'political corruption index. Like the other V-Dem indices, it combines the ratings of thousands of country '
            'experts through a statistical model. Our World in Data republishes the central estimates.')
        ),
        model=geo.PublicSectorCorruptionCountryYear,
        series=(Series('value', _('Public sector corruption index'), 'index', measured_in=pgettext_lazy('measured in', '0 to 1'), better='lower'),),
        tags=Tags('Corruption', (_('Public sector'), _('Bribery'), _('V-Dem'))),
        keywords=(_('corruption'), _('civil servants'), _('bureaucracy'), _('vdem')),
    ),
    Metric(
        slug='judicial-corruption',
        title=_('Judicial corruption score (V-Dem)'),
        question=_('Where can court decisions be bought?'),
        summary=_('How often people and businesses bribe the courts. Higher means less corruption; 0 is about the average.'),
        description=(
            _('The V-Dem judicial corruption score measures how often people or businesses make undocumented extra '
            'payments or bribes to speed up or delay a court case, or to win a favourable decision. Unlike the V-Dem '
            'corruption indices, a higher score means less corruption. A score of 0 is about the average across all '
            'countries and years, and scores run from about -3 to 4. It is one of the four parts of the political '
            'corruption index. Like the other V-Dem measures, it combines the ratings of thousands of country experts '
            'through a statistical model. Our World in Data republishes the central estimates.')
        ),
        model=geo.JudicialCorruptionCountryYear,
        series=(Series('value', _('Judicial corruption score'), 'score', better='higher'),),
        tags=Tags('Corruption', (_('Courts'), _('Bribery'), _('V-Dem'))),
        keywords=(_('corruption'), _('courts'), _('judges'), _('justice'), _('vdem')),
    ),
    Metric(
        slug='corruption-perceptions',
        title=_('Corruption Perceptions Index (CPI)'),
        question=_('Which countries are seen as the most corrupt?'),
        summary=_("How corrupt experts and business people see a country's public sector, from 0 (very corrupt) to 100 (very clean)."),
        description=(
            _("Transparency International's Corruption Perceptions Index scores how corrupt a country's public sector "
            'is seen to be by experts and business people. Each year it averages up to 13 independent sources, such as '
            'expert assessments and business surveys, each converted to a scale from 0 (very corrupt) to 100 (very '
            'clean). It measures perceptions, not corruption itself, because no fully objective national measure of '
            'corruption exists. The method has stayed the same since 2012, so scores from 2012 on can be compared over '
            'time. Our World in Data republishes the scores.')
        ),
        model=geo.CorruptionPerceptionsCountryYear,
        series=(Series('value', _('Corruption Perceptions Index'), 'score_100', measured_in=pgettext_lazy('measured in', '0 to 100'), better='higher'),),
        tags=Tags('Corruption', (_('Perceptions'), _('Public sector'), _('Transparency International'))),
        keywords=(_('corruption'), _('cpi'), _('transparency international'), _('bribery')),
    ),
    Metric(
        slug='military-spending',
        title=_('Military spending'),
        question=_('Which countries spend most on their armed forces?'),
        summary=_('Military expenditure as a share of GDP.'),
        description=(
            _('Military expenditure covers spending on the armed forces, including peacekeeping, defence ministries, '
            'paramilitary forces and military space activities, shown as a share of GDP. The Stockholm International '
            'Peace Research Institute (SIPRI) compiles it from official sources, and the World Bank republishes it.')
        ),
        model=geo.MilitarySpendingCountryYear,
        series=(Series('value', _('Military spending, % of GDP'), 'percent', measured_in=pgettext_lazy('measured in', '% of GDP')),),
        tags=Tags('Governance', (_('Defence'), _('Military'), _('SIPRI'))),
        keywords=(_('defense'), _('defence budget'), _('army'), _('armed forces'), _('sipri')),
    ),
    Metric(
        slug='co2-emissions',
        title=_('CO2 emissions'),
        question=_('Who emits the most carbon dioxide per person?'),
        summary=_('Carbon dioxide from fossil fuels and industry, per person and in total.'),
        description=(
            _('These are emissions of carbon dioxide (CO2) from burning fossil fuels and from industry, such as cement, '
            'counted in the country where they are produced. Emissions from land-use change, such as deforestation, '
            'are not included. The Global Carbon Project publishes them in its yearly Global Carbon Budget, and Our '
            'World in Data adds the per-person figures and republishes them.')
        ),
        model=geo.Co2EmissionsCountryYear,
        series=(
            Series('per_capita', _('CO2 per person'), 'tonnes', measured_in=pgettext_lazy('measured in', 'tonnes per person'), better='lower', log_scale=True, short=_('Per person')),
            Series('total', _('Total CO2'), 'tonnes_total', measured_in=pgettext_lazy('measured in', 'tonnes'), log_scale=True, short=_('Total'), total=True),
        ),
        tags=Tags('Environment', (_('Climate'), _('CO2'), _('Emissions'))),
        keywords=(_('carbon dioxide'), _('carbon emissions'), _('greenhouse gas'), _('climate change'), _('co2')),
    ),
    Metric(
        slug='electricity-mix',
        title=_('Electricity mix'),
        question=_('Where does each country\'s electricity come from?'),
        summary=_('The share of electricity generated by each source, from coal to solar.'),
        description=(
            _('This is the share of a country\'s electricity generated by each source, in percent of the total. '
            'Low-carbon sources are nuclear power and renewables: hydro, wind, solar, bioenergy and others. Ember, an '
            'energy think tank, compiles the figures from national and international statistics, and Our World in '
            'Data combines them with other sources for earlier years.')
        ),
        model=geo.ElectricityMixCountryYear,
        series=(
            Series('low_carbon', _('Low-carbon share'), 'percent', measured_in=pgettext_lazy('measured in', '% of electricity'), better='higher', short=_('Low-carbon')),
            Series('coal', _('Coal share'), 'percent', measured_in=pgettext_lazy('measured in', '% of electricity'), short=_('Coal')),
            Series('gas', _('Gas share'), 'percent', measured_in=pgettext_lazy('measured in', '% of electricity'), short=_('Gas')),
            Series('oil', _('Oil share'), 'percent', measured_in=pgettext_lazy('measured in', '% of electricity'), short=_('Oil')),
            Series('nuclear', _('Nuclear share'), 'percent', measured_in=pgettext_lazy('measured in', '% of electricity'), short=_('Nuclear')),
            Series('hydro', _('Hydro share'), 'percent', measured_in=pgettext_lazy('measured in', '% of electricity'), short=_('Hydro')),
            Series('wind', _('Wind share'), 'percent', measured_in=pgettext_lazy('measured in', '% of electricity'), short=_('Wind')),
            Series('solar', _('Solar share'), 'percent', measured_in=pgettext_lazy('measured in', '% of electricity'), short=_('Solar')),
            Series('bioenergy', _('Bioenergy share'), 'percent', measured_in=pgettext_lazy('measured in', '% of electricity'), short=_('Bioenergy')),
            Series('other_renewables', _('Other renewables share'), 'percent', measured_in=pgettext_lazy('measured in', '% of electricity'), short=_('Other renewables')),
        ),
        tags=Tags('Environment', (_('Energy'), _('Electricity'), _('Renewables'), _('Ember'))),
        keywords=(_('energy mix'), _('renewable energy'), _('solar power'), _('wind power'), _('nuclear power'), _('coal power')),
    ),
    Metric(
        slug='air-pollution',
        title=_('Air pollution'),
        question=_('Where is the air most polluted?'),
        summary=_('How much fine-particle pollution people breathe, and how many live above the WHO guideline.'),
        description=(
            _('Fine particles smaller than 2.5 microns (PM2.5) reach deep into the lungs and cause severe harm. The first '
            'measure is the average yearly concentration people are exposed to, weighted by where they live, in cities '
            "and the countryside; IHME's Global Burden of Disease study estimates it. The second is the share of people "
            'living where it is above 10 micrograms per cubic metre, the guideline value of the World Health '
            'Organization (WHO) that these estimates use. The World Bank republishes both.')
        ),
        model=geo.AirPollutionCountryYear,
        series=(
            Series('pm25', _('PM2.5 exposure'), 'ugm3', measured_in=pgettext_lazy('measured in', 'µg/m³'), better='lower'),
            Series('above_guideline', _('People above the WHO guideline'), 'percent', measured_in=pgettext_lazy('measured in', '% of people'), better='lower',
                   short=_('Above WHO guideline'),
                   note=_('The share of people living where PM2.5 is above 10 µg/m³, the WHO guideline these estimates use. The data ends in 2017.')),
        ),
        tags=Tags('Environment', (_('Air pollution'), _('PM2.5'), _('Health'))),
        keywords=(_('smog'), _('air quality'), _('particulate matter'), _('pollution')),
    ),
    # ---------- Economy and work ----------
    Metric(
        slug='youth-unemployment',
        title=_('Youth unemployment'),
        question=_('Where do young people struggle most to find work?'),
        summary=_('The share of 15 to 24 year olds in the labour force who have no job and are looking for one.'),
        description=(
            _('Youth unemployment is the share of people aged 15 to 24 who are in the labour force, that is working or '
            'looking for work, but have no job. Students who are not looking for work are not counted. These are '
            'modelled estimates from the International Labour Organization (ILO), which fills the gaps in national '
            'labour force surveys so that countries can be compared. The World Bank republishes them.')
        ),
        model=geo.YouthUnemploymentCountryYear,
        series=(Series('value', _('Youth unemployment rate'), 'percent', measured_in=pgettext_lazy('measured in', '% of the youth labour force'), better='lower'),),
        tags=Tags('Economy', (_('Labour market'), _('Unemployment'), _('Youth'), _('ILO'))),
        keywords=(_('young people'), _('jobs'), _('joblessness'), _('neet')),
    ),
    Metric(
        slug='employment-rate',
        title=_('Employment rate'),
        question=_('Where do most adults work?'),
        summary=_('The share of people aged 15 and over who have a job, and the share who have one or look for one.'),
        description=(
            _('The employment-to-population ratio is the share of people aged 15 and over who have a job. The labour '
            'force participation rate adds those who are looking for one. Unlike the unemployment rate, these shares '
            'also count people who have given up looking or who stay out of the labour market, such as students, '
            'pensioners and people caring for family. They are modelled estimates from the International Labour '
            'Organization (ILO), which fills the gaps in national labour force surveys. The World Bank republishes them.')
        ),
        model=geo.EmploymentRateCountryYear,
        series=(
            Series('employed', _('Employment-to-population ratio'), 'percent', measured_in=pgettext_lazy('measured in', '% of people aged 15 and over'), short=_('Employed')),
            Series('in_labour_force', _('Labour force participation rate'), 'percent', measured_in=pgettext_lazy('measured in', '% of people aged 15 and over'), short=_('In the labour force')),
        ),
        tags=Tags('Economy', (_('Labour market'), _('Employment'), _('ILO'))),
        keywords=(_('jobs'), _('workers'), _('working age'), _('participation')),
    ),
    Metric(
        slug='vulnerable-employment',
        title=_('Vulnerable employment'),
        question=_('Where do most people work for themselves or their family?'),
        summary=_('The share of workers who work on their own account or in a family business, often without a contract or protection.'),
        description=(
            _('Vulnerable employment is the share of employed people who work on their own account or help in a family '
            'business, rather than for a wage. These jobs often come without a contract, social security or a steady '
            'income, so the measure is a widely used proxy for informal work. The International Labour Organization '
            '(ILO) estimates it from national labour force surveys with a model that fills the gaps, and the World Bank '
            'republishes it.')
        ),
        model=geo.VulnerableEmploymentCountryYear,
        series=(Series('value', _('Vulnerable employment'), 'percent', measured_in=pgettext_lazy('measured in', '% of employment'), better='lower'),),
        tags=Tags('Economy', (_('Labour market'), _('Informal work'), _('ILO'))),
        keywords=(_('informal economy'), _('self-employed'), _('own-account workers'), _('family workers')),
    ),
    Metric(
        slug='working-hours',
        title=_('Working hours'),
        question=_('Where do people work the longest hours?'),
        summary=_('The hours a worker puts in over a year, on average.'),
        description=(
            _('This is the average number of hours worked per worker in a year, counting full-time and part-time workers '
            'alike. It falls when working weeks get shorter, holidays get longer or more people work part-time. The '
            'figures come from the Penn World Table, which draws on national accounts and labour statistics, and Our '
            'World in Data republishes them. The series starts in 1950; earlier historical estimates are left out.')
        ),
        model=geo.WorkingHoursCountryYear,
        series=(Series('value', _('Annual working hours per worker'), 'hours', measured_in=pgettext_lazy('measured in', 'hours a year')),),
        tags=Tags('Economy', (_('Labour market'), _('Working time'), _('Penn World Table'))),
        keywords=(_('hours worked'), _('working week'), _('work-life balance'), _('overtime')),
    ),
    Metric(
        slug='savings-and-investment',
        title=_('Savings and investment'),
        question=_('Which countries invest most in their future?'),
        summary=_('Gross capital formation and gross savings as a share of GDP.'),
        description=(
            _('Gross capital formation, the investment rate, is what a country spends in a year on things that last: '
            'buildings, roads, machines, software and additions to stocks, as a share of GDP. Gross savings is the part '
            'of national income that is not consumed, which pays for that investment or is lent abroad. When a country '
            'invests more than it saves, it borrows the difference from the rest of the world. Both come from the '
            'national accounts that each country\'s statistics office compiles, collected by the World Bank.')
        ),
        model=geo.SavingsInvestmentCountryYear,
        series=(
            Series('investment', _('Gross capital formation'), 'percent', measured_in=pgettext_lazy('measured in', '% of GDP'), short=_('Investment')),
            Series('fixed', _('Gross fixed capital formation'), 'percent', measured_in=pgettext_lazy('measured in', '% of GDP'), short=_('Fixed investment'),
                   note=_('Investment in buildings, machines and other fixed assets, without changes in inventories.')),
            Series('savings', _('Gross savings'), 'percent', measured_in=pgettext_lazy('measured in', '% of GDP'), short=_('Savings')),
        ),
        tags=Tags('Economy', (_('National accounts'), _('Investment'), _('Savings'))),
        keywords=(_('capital formation'), _('investment rate'), _('saving rate')),
    ),
    Metric(
        slug='fdi-inflows',
        title=_('Foreign direct investment'),
        question=_('Which countries attract the most foreign investment?'),
        summary=_('Net inflows of foreign direct investment as a share of GDP.'),
        description=(
            _('Foreign direct investment (FDI) is money that investors from abroad put into a lasting stake in a '
            'country\'s businesses: at least 10% of a company\'s voting shares, or new plants and offices. Net inflows are '
            'what came in minus what foreign investors took out, as a share of GDP. The figures are volatile, as one big '
            'deal can move a small economy\'s number a lot, and tax havens show very large flows that pass through them. '
            'They come from the balance of payments that the IMF compiles, and the World Bank republishes them.')
        ),
        model=geo.FdiInflowsCountryYear,
        series=(Series('value', _('FDI net inflows'), 'percent', measured_in=pgettext_lazy('measured in', '% of GDP')),),
        tags=Tags('Economy', (_('Investment'), _('Foreign investment'), _('Balance of payments'))),
        keywords=(_('fdi'), _('foreign capital'), _('multinationals')),
    ),
    Metric(
        slug='current-account',
        title=_('Current account balance'),
        question=_('Which countries sell more to the world than they buy?'),
        summary=_('What a country earns from the rest of the world minus what it pays, as a share of GDP.'),
        description=(
            _('The current account balance sums up a country\'s dealings with the rest of the world: exports minus '
            'imports of goods and services, plus income from abroad such as interest, dividends and workers\' '
            'remittances, minus the same flows going out. A surplus means the country lends to the rest of the world; '
            'a deficit means it borrows. The International Monetary Fund (IMF) publishes it in its World Economic '
            'Outlook. We show past years only and leave out the IMF\'s forecasts; the latest year can still be an IMF '
            'estimate.')
        ),
        model=geo.CurrentAccountCountryYear,
        series=(Series('value', _('Current account balance'), 'percent', measured_in=pgettext_lazy('measured in', '% of GDP')),),
        tags=Tags('Economy', (_('Balance of payments'), _('Trade'), _('IMF'))),
        keywords=(_('trade surplus'), _('trade deficit'), _('external balance')),
    ),
    Metric(
        slug='private-debt',
        title=_('Private debt'),
        question=_('Where do households and companies owe the most?'),
        summary=_('The debt of households and non-financial companies as a share of GDP.'),
        description=(
            _('Private debt is what households and non-financial companies owe in loans and debt securities, as a share '
            'of GDP. Household debt, shown on its own, is mostly mortgages. Rising private debt can fuel growth and then '
            'a crisis, as in 2008. The International Monetary Fund (IMF) compiles it in its Global Debt Database from '
            'national financial accounts and central bank data, back to 1950 for some countries.')
        ),
        model=geo.PrivateDebtCountryYear,
        series=(
            Series('total', _('Private debt'), 'percent', measured_in=pgettext_lazy('measured in', '% of GDP'), better='lower', short=_('Households and companies')),
            Series('households', _('Household debt'), 'percent', measured_in=pgettext_lazy('measured in', '% of GDP'), better='lower', short=_('Households'),
                   note=_('Loans and debt securities of households only, mostly mortgages. Fewer countries report it.')),
        ),
        tags=Tags('Economy', (_('Debt'), _('Households'), _('Companies'), _('IMF'))),
        keywords=(_('household debt'), _('corporate debt'), _('mortgages'), _('credit'), _('leverage')),
    ),
    Metric(
        slug='remittances',
        title=_('Remittances'),
        question=_('Where does money sent home from abroad matter most?'),
        summary=_('Money that migrants send home, as a share of the receiving country\'s GDP.'),
        description=(
            _('Personal remittances are the money that people working abroad send home to their families, plus the '
            'earnings of workers employed in another country for less than a year. For some countries they are a '
            'bigger source of income than exports or aid. The figures come from the balance of payments that the IMF '
            'compiles, with World Bank estimates where countries report none, and the World Bank republishes them. '
            'Money sent through informal channels is not counted.')
        ),
        model=geo.RemittancesCountryYear,
        series=(Series('value', _('Remittances received'), 'percent', measured_in=pgettext_lazy('measured in', '% of GDP')),),
        tags=Tags('Economy', (_('Migration'), _('Remittances'), _('Balance of payments'))),
        keywords=(_('migrants'), _('money transfers'), _('diaspora')),
    ),
    Metric(
        slug='foreign-reserves',
        title=_('Foreign reserves'),
        question=_('Which countries hold the biggest buffer of reserves?'),
        summary=_('How many months of imports a country\'s reserves could pay for.'),
        description=(
            _('Total reserves are the foreign currency, gold and IMF assets a central bank holds. Dividing them by a '
            'month\'s imports of goods and services shows how long a country could keep paying for imports if money '
            'from abroad stopped: the buffer against a crisis. Three months is a common rule of thumb for a safe '
            'minimum. The IMF compiles the figures from central banks, and the World Bank republishes them.')
        ),
        model=geo.ForeignReservesCountryYear,
        series=(Series('value', _('Reserves in months of imports'), 'months', measured_in=pgettext_lazy('measured in', 'months of imports')),),
        tags=Tags('Economy', (_('Reserves'), _('Central banks'), _('Balance of payments'))),
        keywords=(_('foreign exchange'), _('central bank'), _('gold'), _('currency crisis')),
    ),
    Metric(
        slug='economic-structure',
        title=_('Economic structure'),
        question=_('Which economies run on farms, factories or services?'),
        summary=_('The share of GDP that agriculture, industry and services each produce.'),
        description=(
            _('This splits a country\'s GDP by sector: agriculture, forestry and fishing; industry, which includes '
            'mining, manufacturing, energy and construction; and services, from shops and transport to banking, '
            'health and government. As countries get richer, work usually moves from farms to factories and then to '
            'services. The shares come from the national accounts that each country\'s statistics office compiles, '
            'collected by the World Bank. Taxes and subsidies on products are not assigned to any sector, so the three '
            'shares do not always add up to 100.')
        ),
        model=geo.EconomicStructureCountryYear,
        series=(
            Series('agriculture', _('Agriculture share'), 'percent', measured_in=pgettext_lazy('measured in', '% of GDP'), short=_('Agriculture')),
            Series('industry', _('Industry share'), 'percent', measured_in=pgettext_lazy('measured in', '% of GDP'), short=_('Industry')),
            Series('services', _('Services share'), 'percent', measured_in=pgettext_lazy('measured in', '% of GDP'), short=_('Services')),
        ),
        tags=Tags('Economy', (_('National accounts'), _('Agriculture'), _('Industry'), _('Services'))),
        keywords=(_('manufacturing'), _('farming'), _('value added'), _('sectors'), _('deindustrialisation')),
    ),
    Metric(
        slug='rd-spending',
        title=_('Research and development spending'),
        question=_('Which countries spend most on research?'),
        summary=_('Spending on research and development by companies, universities and governments, as a share of GDP.'),
        description=(
            _('Research and development (R&D) spending is what a country\'s companies, universities, governments and '
            'non-profits spend in a year on creating new knowledge and new products, as a share of GDP. The UNESCO '
            'Institute for Statistics collects it from national surveys of research, and the World Bank republishes '
            'it. Many countries report it with a delay of two years or more.')
        ),
        model=geo.RdSpendingCountryYear,
        series=(Series('value', _('R&D spending'), 'percent', measured_in=pgettext_lazy('measured in', '% of GDP'), better='higher'),),
        tags=Tags('Education', (_('Research'), _('Innovation'), _('UNESCO'))),
        keywords=(_('r&d'), _('science'), _('innovation'), _('technology')),
    ),
    Metric(
        slug='internet-users',
        title=_('Internet and phones'),
        question=_('Where is everyone online?'),
        summary=_('The share of people who use the internet, and mobile and broadband subscriptions per 100 people.'),
        description=(
            _('Internet users are the share of people who used the internet in the last three months, from any device. '
            'Mobile subscriptions count active mobile phone subscriptions per 100 people; they can pass 100 where people '
            'hold several SIM cards. Fixed broadband counts subscriptions to fast internet at home or work per 100 '
            'people. The International Telecommunication Union (ITU) collects the figures from telecom regulators and '
            'household surveys, and the World Bank republishes them.')
        ),
        model=geo.InternetUsersCountryYear,
        series=(
            Series('internet', _('Internet users'), 'percent', measured_in=pgettext_lazy('measured in', '% of people'), better='higher', short=_('Internet users')),
            Series('mobile', _('Mobile subscriptions'), 'per_100', measured_in=pgettext_lazy('measured in', 'per 100 people'), short=_('Mobile')),
            Series('broadband', _('Fixed broadband subscriptions'), 'per_100', measured_in=pgettext_lazy('measured in', 'per 100 people'), better='higher', short=_('Broadband')),
        ),
        tags=Tags('Society', (_('Technology'), _('Internet'), _('Telecommunications'), _('ITU'))),
        keywords=(_('digital divide'), _('connectivity'), _('mobile phones'), _('smartphones'), _('online')),
    ),
    Metric(
        slug='electricity-access',
        title=_('Access to electricity'),
        question=_('Where do people still live without electricity?'),
        summary=_('The share of people with access to electricity.'),
        description=(
            _('This is the share of people who have access to electricity at home, whether from the grid or from '
            'off-grid sources such as solar systems. The World Bank estimates it from household surveys and censuses, '
            'filling the gaps with a model, for its tracking of the UN goal of energy for all. In rich countries it has '
            'been 100% for decades, so the differences are in Africa and South Asia.')
        ),
        model=geo.ElectricityAccessCountryYear,
        series=(Series('value', _('Access to electricity'), 'percent', measured_in=pgettext_lazy('measured in', '% of people'), better='higher'),),
        tags=Tags('Development', (_('Energy'), _('Electricity'), _('Infrastructure'))),
        keywords=(_('electrification'), _('power'), _('grid'), _('energy poverty')),
    ),
    # ---------- Health and demography ----------
    Metric(
        slug='infant-mortality',
        title=_('Infant mortality'),
        question=_('Where do the most babies die in their first year?'),
        summary=_('Deaths before the first birthday per 1,000 live births.'),
        description=(
            _('The infant mortality rate is the number of babies who die before their first birthday per 1,000 live '
            'births in that year. It is one of the oldest and most telling measures of a country\'s health, as it '
            'responds to clean water, vaccines, nutrition and care at birth. The UN Inter-agency Group for Child '
            'Mortality Estimation (UNICEF, the WHO, the World Bank and the UN Population Division) produces the '
            'estimates from surveys, censuses and vital registration, and the World Bank republishes them.')
        ),
        model=geo.InfantMortalityCountryYear,
        series=(Series('value', _('Infant mortality rate'), 'per_1000', measured_in=pgettext_lazy('measured in', 'per 1,000 live births'), better='lower', log_scale=True),),
        tags=Tags('Health', (_('Mortality'), _('Children'), _('Infants'))),
        keywords=(_('babies'), _('newborns'), _('deaths'), _('child health')),
    ),
    Metric(
        slug='maternal-mortality',
        title=_('Maternal mortality'),
        question=_('Where is giving birth most dangerous?'),
        summary=_('Women who die from pregnancy or childbirth per 100,000 live births.'),
        description=(
            _('The maternal mortality ratio is the number of women who die from causes related to pregnancy or '
            'childbirth, during pregnancy or within 42 days of its end, per 100,000 live births. Almost all these '
            'deaths are preventable with skilled care at birth. The estimates are modelled by the WHO, UNICEF, UNFPA, '
            'the World Bank and the UN Population Division from civil registration, surveys and studies, because many '
            'countries do not record every death. The World Bank republishes them.')
        ),
        model=geo.MaternalMortalityCountryYear,
        series=(Series('value', _('Maternal mortality ratio'), 'per_100k', measured_in=pgettext_lazy('measured in', 'per 100,000 live births'), better='lower', log_scale=True),),
        tags=Tags('Health', (_('Mortality'), _('Women'), _('Childbirth'))),
        keywords=(_('pregnancy'), _('mothers'), _('childbirth'), _('deaths')),
    ),
    Metric(
        slug='adolescent-fertility',
        title=_('Teenage births'),
        question=_('Where do most teenagers become mothers?'),
        summary=_('Births per 1,000 women aged 15 to 19.'),
        description=(
            _('The adolescent fertility rate is the number of births per 1,000 women aged 15 to 19 in a year. Early '
            'motherhood often cuts short a girl\'s schooling and carries higher health risks for mother and child. The '
            'UN Population Division estimates it in its World Population Prospects from censuses, surveys and birth '
            'registers, and the World Bank republishes it.')
        ),
        model=geo.AdolescentFertilityCountryYear,
        series=(Series('value', _('Adolescent fertility rate'), 'per_1000', measured_in=pgettext_lazy('measured in', 'per 1,000 women aged 15 to 19'), better='lower'),),
        tags=Tags('Demography', (_('Births'), _('Teenagers'), _('Women'))),
        keywords=(_('teen pregnancy'), _('adolescents'), _('girls'), _('young mothers')),
    ),
    Metric(
        slug='immunisation',
        title=_('Childhood vaccination'),
        question=_('Where are children vaccinated?'),
        summary=_('The share of one-year-olds vaccinated against measles, and against diphtheria, tetanus and pertussis.'),
        description=(
            _('These are the shares of children aged 12 to 23 months who have received the measles vaccine, and the '
            'third dose of the vaccine against diphtheria, tetanus and pertussis (DTP). Both are standard measures of '
            'how well a health system reaches children. The WHO and UNICEF estimate them each year from official '
            'reports and household surveys, and the World Bank republishes them. Measles spreads so easily that about '
            '95% coverage is needed to stop outbreaks.')
        ),
        model=geo.ImmunisationCountryYear,
        series=(
            Series('measles', _('Measles vaccination'), 'percent', measured_in=pgettext_lazy('measured in', '% of one-year-olds'), better='higher', short=_('Measles')),
            Series('dtp', _('DTP vaccination'), 'percent', measured_in=pgettext_lazy('measured in', '% of one-year-olds'), better='higher', short=_('DTP')),
        ),
        tags=Tags('Health', (_('Vaccination'), _('Children'), _('WHO'))),
        keywords=(_('vaccines'), _('immunization'), _('measles'), _('dtp'), _('public health')),
    ),
    Metric(
        slug='suicide-rate',
        title=_('Suicide rate'),
        question=_('Where are suicides most common?'),
        summary=_('Suicides per 100,000 people, adjusted for age.'),
        description=(
            _('The suicide mortality rate is the number of deaths by suicide per 100,000 people in a year, adjusted for '
            'the age structure of each country so that countries can be compared. The World Health Organization (WHO) '
            'estimates it in its Global Health Estimates from death registers, which many countries keep incompletely, '
            'so the figures for some countries rest on models. The World Bank republishes them.')
        ),
        model=geo.SuicideRateCountryYear,
        series=(Series('value', _('Suicide rate'), 'per_100k', measured_in=pgettext_lazy('measured in', 'per 100,000 people'), better='lower'),),
        tags=Tags('Health', (_('Mortality'), _('Mental health'), _('WHO'))),
        keywords=(_('suicides'), _('mental health'), _('depression'), _('deaths')),
    ),
    Metric(
        slug='tuberculosis',
        title=_('Tuberculosis'),
        question=_('Where is tuberculosis still common?'),
        summary=_('New cases of tuberculosis per 100,000 people in a year.'),
        description=(
            _('Tuberculosis incidence is the estimated number of new and relapse cases of tuberculosis per 100,000 '
            'people in a year, including people who also have HIV. Tuberculosis is the infectious disease that kills '
            'the most people worldwide, though it is curable. The World Health Organization (WHO) estimates it from '
            'case reports, surveys and models, and the World Bank republishes it.')
        ),
        model=geo.TuberculosisCountryYear,
        series=(Series('value', _('Tuberculosis incidence'), 'per_100k', measured_in=pgettext_lazy('measured in', 'per 100,000 people'), better='lower', log_scale=True),),
        tags=Tags('Health', (_('Infectious diseases'), _('Tuberculosis'), _('WHO'))),
        keywords=(_('tb'), _('infection'), _('disease'), _('epidemic')),
    ),
    Metric(
        slug='hiv-prevalence',
        title=_('HIV prevalence'),
        question=_('Where do most adults live with HIV?'),
        summary=_('The share of people aged 15 to 49 living with HIV.'),
        description=(
            _('HIV prevalence is the share of people aged 15 to 49 who live with HIV, whether or not they know it or '
            'receive treatment. UNAIDS estimates it with models fed by surveys, antenatal clinic data and case '
            'reports, and the World Bank republishes the figures. Countries with very low prevalence often have no '
            'estimate, so they show no data.')
        ),
        model=geo.HivPrevalenceCountryYear,
        series=(Series('value', _('HIV prevalence'), 'percent', measured_in=pgettext_lazy('measured in', '% of people aged 15 to 49'), better='lower', log_scale=True),),
        tags=Tags('Health', (_('Infectious diseases'), _('HIV'), _('UNAIDS'))),
        keywords=(_('aids'), _('hiv'), _('epidemic'), _('infection')),
    ),
    Metric(
        slug='out-of-pocket-health',
        title=_('Out-of-pocket health spending'),
        question=_('Where do patients pay for health care themselves?'),
        summary=_('The share of health spending that people pay directly from their own pockets.'),
        description=(
            _('Out-of-pocket spending is what people pay directly for health care, at the doctor, the hospital or the '
            'pharmacy, as a share of all current health spending. The rest is paid by governments, social insurance or '
            'private insurance. A high share means illness can push families into poverty. The World Health '
            'Organization (WHO) compiles it in its Global Health Expenditure Database, and the World Bank republishes it.')
        ),
        model=geo.OutOfPocketHealthCountryYear,
        series=(Series('value', _('Out-of-pocket share of health spending'), 'percent', measured_in=pgettext_lazy('measured in', '% of health spending'), better='lower'),),
        tags=Tags('Health', (_('Health spending'), _('Health insurance'), _('WHO'))),
        keywords=(_('health costs'), _('medical bills'), _('insurance'), _('universal health coverage')),
    ),
    Metric(
        slug='alcohol-consumption',
        title=_('Alcohol consumption'),
        question=_('Where do people drink the most?'),
        summary=_('Litres of pure alcohol per adult in a year.'),
        description=(
            _('This is the alcohol drunk per person aged 15 and over in a year, in litres of pure alcohol, counting '
            'beer, wine and spirits together. It includes recorded sales and an estimate of unrecorded alcohol such as '
            'home-made drinks and cross-border shopping, averaged over three years. The World Health Organization '
            '(WHO) estimates it from production, trade and sales data and surveys, and the World Bank republishes it. '
            'A litre of pure alcohol is about 25 litres of wine or 100 small beers.')
        ),
        model=geo.AlcoholConsumptionCountryYear,
        series=(Series('value', _('Alcohol per adult'), 'litres', measured_in=pgettext_lazy('measured in', 'litres of pure alcohol a year'), better='lower'),),
        tags=Tags('Health', (_('Alcohol'), _('Lifestyle'), _('WHO'))),
        keywords=(_('drinking'), _('beer'), _('wine'), _('spirits')),
    ),
    Metric(
        slug='road-deaths',
        title=_('Road deaths'),
        question=_('Where are the roads most deadly?'),
        summary=_('Deaths from road traffic injuries per 100,000 people.'),
        description=(
            _('This is the number of people killed in road traffic crashes per 100,000 people in a year, whether '
            'drivers, passengers, cyclists or pedestrians. The World Health Organization (WHO) estimates it from '
            'death registers and police reports, with a model that corrects for under-reporting in countries that '
            'count poorly, and the World Bank republishes it.')
        ),
        model=geo.RoadDeathsCountryYear,
        series=(Series('value', _('Road traffic deaths'), 'per_100k', measured_in=pgettext_lazy('measured in', 'per 100,000 people'), better='lower'),),
        tags=Tags('Health', (_('Mortality'), _('Road safety'), _('WHO'))),
        keywords=(_('traffic accidents'), _('car crashes'), _('road safety'), _('deaths')),
    ),
    Metric(
        slug='doctors-and-beds',
        title=_('Doctors and hospital beds'),
        question=_('Where are doctors and hospital beds scarce?'),
        summary=_('Physicians and hospital beds per 1,000 people.'),
        description=(
            _('Physicians per 1,000 people counts generalist and specialist doctors who practise in the country. '
            'Hospital beds per 1,000 people counts beds in public and private hospitals, including psychiatric and '
            'rehabilitation beds. Both measure the capacity of a health system, not its quality. The World Health '
            'Organization (WHO) collects them from national registers and surveys, and the World Bank republishes '
            'them. Countries report in different years, so the series have gaps.')
        ),
        model=geo.DoctorsBedsCountryYear,
        series=(
            Series('physicians', _('Physicians per 1,000 people'), 'per_1000', measured_in=pgettext_lazy('measured in', 'per 1,000 people'), better='higher', short=_('Doctors')),
            Series('beds', _('Hospital beds per 1,000 people'), 'per_1000', measured_in=pgettext_lazy('measured in', 'per 1,000 people'), short=_('Hospital beds')),
        ),
        tags=Tags('Health', (_('Health system'), _('Doctors'), _('Hospitals'), _('WHO'))),
        keywords=(_('physicians'), _('medical staff'), _('health care capacity'), _('hospitals')),
    ),
    Metric(
        slug='water-and-sanitation',
        title=_('Drinking water and sanitation'),
        question=_('Where do people have safe water and toilets?'),
        summary=_('The share of people with safely managed or at least basic drinking water and sanitation.'),
        description=(
            _('Safely managed drinking water is water from an improved source at home, available when needed and free '
            'of contamination. Safely managed sanitation is a toilet not shared with other households whose waste is '
            'treated or safely disposed of. The "at least basic" measures are less strict: an improved source within a '
            '30-minute round trip, or an unshared improved toilet. The WHO/UNICEF Joint Monitoring Programme estimates '
            'them from household surveys and censuses for the UN\'s water and sanitation goal, and the World Bank '
            'republishes them. Fewer countries have the safely managed figures.')
        ),
        model=geo.WaterSanitationCountryYear,
        series=(
            Series('water_safe', _('Safely managed drinking water'), 'percent', measured_in=pgettext_lazy('measured in', '% of people'), better='higher', short=_('Safe water')),
            Series('water_basic', _('At least basic drinking water'), 'percent', measured_in=pgettext_lazy('measured in', '% of people'), better='higher', short=_('Basic water')),
            Series('sanitation_safe', _('Safely managed sanitation'), 'percent', measured_in=pgettext_lazy('measured in', '% of people'), better='higher', short=_('Safe sanitation')),
            Series('sanitation_basic', _('At least basic sanitation'), 'percent', measured_in=pgettext_lazy('measured in', '% of people'), better='higher', short=_('Basic sanitation')),
        ),
        tags=Tags('Health', (_('Water'), _('Sanitation'), _('Infrastructure'), _('WHO'))),
        keywords=(_('clean water'), _('toilets'), _('sewage'), _('hygiene'), _('wash')),
    ),
    Metric(
        slug='child-stunting',
        title=_('Child stunting'),
        question=_('Where are children too short for their age?'),
        summary=_('The share of children under five who are stunted by chronic malnutrition.'),
        description=(
            _('Stunting means a child is much shorter than healthy children of the same age: more than two standard '
            'deviations below the WHO growth standard. It is the mark of chronic malnutrition and repeated infection '
            'in the first years of life, and it harms learning and health for life. UNICEF, the WHO and the World Bank '
            'estimate the share of children under five who are stunted from household surveys with a model that fills '
            'the gaps between surveys.')
        ),
        model=geo.ChildStuntingCountryYear,
        series=(Series('value', _('Stunting'), 'percent', measured_in=pgettext_lazy('measured in', '% of children under 5'), better='lower'),),
        tags=Tags('Food', (_('Malnutrition'), _('Children'), _('Stunting'))),
        keywords=(_('malnutrition'), _('child growth'), _('hunger'), _('nutrition')),
    ),
    Metric(
        slug='urban-population',
        title=_('Urban population'),
        question=_('Where do most people live in cities?'),
        summary=_('The share of people living in urban areas.'),
        description=(
            _('This is the share of a country\'s people who live in urban areas, as each country defines them: by '
            'population size, density or administrative status. Definitions differ, so compare between countries with '
            'care; the trend within a country is more reliable. The UN Population Division compiles the figures in its '
            'World Urbanization Prospects from national censuses, and the World Bank republishes them.')
        ),
        model=geo.UrbanPopulationCountryYear,
        series=(Series('value', _('Urban population'), 'percent', measured_in=pgettext_lazy('measured in', '% of people')),),
        tags=Tags('Demography', (_('Urbanisation'), _('Cities'), _('Population'))),
        keywords=(_('cities'), _('urbanization'), _('rural'), _('towns')),
    ),
    Metric(
        slug='age-dependency',
        title=_('Ageing and dependency'),
        question=_('Where are the oldest populations?'),
        summary=_('People over 64 as a share of the population, and the young and old per 100 people of working age.'),
        description=(
            _('The age dependency ratio is the number of people under 15 and over 64 per 100 people of working age, 15 '
            'to 64. The old-age dependency ratio counts only those over 64, the people whom pensions and health care '
            'must support per 100 workers. The share aged 65 and over is the plainest measure of an ageing population. '
            'The UN Population Division estimates them in its World Population Prospects, and the World Bank '
            'republishes them.')
        ),
        model=geo.AgeDependencyCountryYear,
        series=(
            Series('over_65', _('People aged 65 and over'), 'percent', measured_in=pgettext_lazy('measured in', '% of people'), short=_('Over 65')),
            Series('old', _('Old-age dependency ratio'), 'per_100', measured_in=pgettext_lazy('measured in', 'per 100 people aged 15 to 64'), short=_('Old-age dependency')),
            Series('total', _('Age dependency ratio'), 'per_100', measured_in=pgettext_lazy('measured in', 'per 100 people aged 15 to 64'), short=_('Total dependency')),
        ),
        tags=Tags('Demography', (_('Ageing'), _('Population'), _('Pensions'))),
        keywords=(_('elderly'), _('old people'), _('retirement'), _('working age'), _('demographics')),
    ),
    Metric(
        slug='refugees',
        title=_('Refugees'),
        question=_('Where do refugees come from, and where do they go?'),
        summary=_('Refugees by the country they fled and by the country that hosts them.'),
        description=(
            _('Refugees are people who fled their country because of persecution, war or violence and are recognised '
            'as refugees under international law, including people in refugee-like situations. The first measure counts '
            'them by the country they come from; the second by the country that hosts them. Asylum seekers whose '
            'claims are pending and people displaced inside their own country are not counted. The UN Refugee Agency '
            '(UNHCR) compiles the figures from governments and its own registration, and the World Bank republishes them.')
        ),
        model=geo.RefugeesCountryYear,
        series=(
            Series('from_country', _('Refugees from the country'), 'people', measured_in=pgettext_lazy('measured in', 'people'), log_scale=True, total=True, short=_('By origin')),
            Series('in_country', _('Refugees hosted'), 'people', measured_in=pgettext_lazy('measured in', 'people'), log_scale=True, total=True, short=_('By host country')),
        ),
        tags=Tags('Demography', (_('Migration'), _('Refugees'), _('UNHCR'))),
        keywords=(_('asylum'), _('displaced people'), _('migration'), _('war')),
    ),
    Metric(
        slug='school-enrolment',
        title=_('Secondary and tertiary enrolment'),
        question=_('Where do most young people go to secondary school and university?'),
        summary=_('Pupils in secondary and students in tertiary education, as a share of the age group.'),
        description=(
            _('Gross enrolment is the number of pupils or students in a level of education, whatever their age, as a '
            'share of the population of the age group that officially belongs to that level. It can pass 100% where '
            'many pupils repeat a year or start late. Secondary covers lower and upper secondary school; tertiary '
            'covers universities and other higher education. The UNESCO Institute for Statistics collects the figures '
            'from education ministries, and the World Bank republishes them.')
        ),
        model=geo.SchoolEnrolmentCountryYear,
        series=(
            Series('secondary', _('Secondary enrolment, gross'), 'percent', measured_in=pgettext_lazy('measured in', '% of the age group'), better='higher', short=_('Secondary')),
            Series('tertiary', _('Tertiary enrolment, gross'), 'percent', measured_in=pgettext_lazy('measured in', '% of the age group'), better='higher', short=_('Tertiary')),
        ),
        tags=Tags('Education', (_('Enrolment'), _('Secondary school'), _('Higher education'), _('UNESCO'))),
        keywords=(_('university'), _('students'), _('pupils'), _('high school'), _('college')),
    ),
    # ---------- Environment and energy ----------
    Metric(
        slug='greenhouse-gas-emissions',
        title=_('Greenhouse gas emissions'),
        question=_('Who emits the most greenhouse gases per person?'),
        summary=_('All greenhouse gases, including methane and nitrous oxide, per person and in total.'),
        description=(
            _('These are emissions of all greenhouse gases from energy, industry, agriculture and waste, converted to '
            'tonnes of CO2 equivalent by how much each gas warms the planet over 100 years. Unlike the CO2 page, they '
            'include methane from cattle, rice and gas leaks and nitrous oxide from fertiliser, which matter a lot for '
            'farming countries. Emissions from land use and forests are not included. The European Commission\'s '
            'Joint Research Centre estimates them in its EDGAR database, and the World Bank republishes them.')
        ),
        model=geo.GreenhouseGasCountryYear,
        series=(
            Series('per_capita', _('Greenhouse gases per person'), 'tonnes', measured_in=pgettext_lazy('measured in', 'tonnes of CO2 equivalent per person'), better='lower', log_scale=True, short=_('Per person')),
            Series('total', _('Total greenhouse gases'), 'tonnes_total', measured_in=pgettext_lazy('measured in', 'tonnes of CO2 equivalent'), log_scale=True, short=_('Total'), total=True),
        ),
        tags=Tags('Environment', (_('Climate'), _('Emissions'), _('Methane'), _('EDGAR'))),
        keywords=(_('ghg'), _('methane'), _('nitrous oxide'), _('climate change'), _('co2 equivalent')),
    ),
    Metric(
        slug='consumption-co2',
        title=_('Consumption-based CO2 emissions'),
        question=_('Who causes the most CO2 through what they buy?'),
        summary=_('CO2 emissions caused by what a country consumes, imports included and exports left out, per person.'),
        description=(
            _('Consumption-based emissions assign CO2 to the country where goods are consumed rather than where they '
            'are made: a country\'s own emissions, plus those embedded in its imports, minus those in its exports. '
            'They show whether a country has cut its emissions or moved them abroad. The Global Carbon Project '
            'estimates them from trade and energy data, and Our World in Data republishes the per-person figures. '
            'Fewer countries are covered than for production-based CO2.')
        ),
        model=geo.ConsumptionCo2CountryYear,
        series=(Series('value', _('Consumption-based CO2 per person'), 'tonnes', measured_in=pgettext_lazy('measured in', 'tonnes per person'), better='lower', log_scale=True),),
        tags=Tags('Environment', (_('Climate'), _('CO2'), _('Trade'))),
        keywords=(_('carbon footprint'), _('embedded emissions'), _('imports'), _('offshoring')),
    ),
    Metric(
        slug='temperature-anomaly',
        title=_('Temperature change'),
        question=_('Which countries have warmed the most?'),
        summary=_('How much warmer a year was than the 1991 to 2020 average, country by country.'),
        description=(
            _('The temperature anomaly is the difference between a year\'s average temperature over a country\'s land '
            'and the average of 1991 to 2020, in degrees Celsius. A positive value means a warmer year than that '
            'baseline. The figures come from ERA5, the Copernicus Climate Change Service\'s reanalysis, which blends '
            'weather observations with a climate model to cover the whole globe since 1940; Our World in Data averages '
            'it by country. Single years swing with the weather, so look at the trend.')
        ),
        model=geo.TemperatureAnomalyCountryYear,
        series=(Series('value', _('Temperature anomaly'), 'celsius', measured_in=pgettext_lazy('measured in', '°C above the 1991–2020 average'), better='lower'),),
        tags=Tags('Environment', (_('Climate'), _('Temperature'), _('Global warming'), _('Copernicus'))),
        keywords=(_('warming'), _('climate change'), _('heat'), _('weather')),
        default_countries=('BRA', 'DEU', 'USA', 'IND', 'RUS'),
    ),
    Metric(
        slug='forest-area',
        title=_('Forest area'),
        question=_('Which countries are losing their forests?'),
        summary=_('Forest as a share of a country\'s land area.'),
        description=(
            _('Forest area is land of at least half a hectare with trees taller than five metres and a canopy cover '
            'above 10%, as a share of the country\'s land area. It includes plantations but not orchards or city parks. '
            'The UN Food and Agriculture Organization (FAO) compiles it every five years in its Global Forest Resources '
            'Assessment from national forest inventories and satellite data, with yearly values in between, and the '
            'World Bank republishes it. A rising share can mean new plantations as well as natural regrowth.')
        ),
        model=geo.ForestAreaCountryYear,
        series=(Series('value', _('Forest area'), 'percent', measured_in=pgettext_lazy('measured in', '% of land area'), better='higher'),),
        tags=Tags('Environment', (_('Forests'), _('Land use'), _('FAO'))),
        keywords=(_('deforestation'), _('trees'), _('amazon'), _('reforestation'), _('land')),
    ),
    Metric(
        slug='energy-use',
        title=_('Energy use per person'),
        question=_('Who uses the most energy?'),
        summary=_('All the energy a country uses per person, in kilograms of oil equivalent.'),
        description=(
            _('Energy use is a country\'s primary energy supply, the energy in the fuels it produces and imports minus '
            'exports and stock changes, divided by its population. It covers electricity, heating, transport and '
            'industry together, in kilograms of oil equivalent: the energy in one kilogram of crude oil, about 11.6 '
            'kilowatt-hours. The International Energy Agency (IEA) compiles the energy balances, and the World Bank '
            'republishes the per-person figures.')
        ),
        model=geo.EnergyUseCountryYear,
        series=(Series('value', _('Energy use per person'), 'kgoe', measured_in=pgettext_lazy('measured in', 'kg of oil equivalent per person'), log_scale=True),),
        tags=Tags('Environment', (_('Energy'), _('Consumption'), _('IEA'))),
        keywords=(_('energy consumption'), _('oil equivalent'), _('fuel'), _('primary energy')),
    ),
    Metric(
        slug='renewable-energy',
        title=_('Renewable energy'),
        question=_('Where does renewable energy power most of daily life?'),
        summary=_('The share of all final energy, not just electricity, that comes from renewable sources.'),
        description=(
            _('This is the share of a country\'s final energy consumption, the energy used in homes, transport, industry '
            'and services, that comes from renewable sources: hydro, wind, solar, geothermal and bioenergy, including '
            'traditional wood and charcoal. It differs from the electricity mix because most energy is used as fuel '
            'and heat, not as electricity. Poor countries often score high because they cook with wood. The '
            'International Energy Agency and the UN compile it for the UN\'s energy goal, and the World Bank '
            'republishes it.')
        ),
        model=geo.RenewableEnergyCountryYear,
        series=(Series('value', _('Renewable share of final energy'), 'percent', measured_in=pgettext_lazy('measured in', '% of final energy consumption'), better='higher'),),
        tags=Tags('Environment', (_('Energy'), _('Renewables'), _('Energy transition'))),
        keywords=(_('renewables'), _('clean energy'), _('solar'), _('wind'), _('biomass')),
    ),
    Metric(
        slug='electricity-consumption',
        title=_('Electricity consumption per person'),
        question=_('Who uses the most electricity?'),
        summary=_('Electricity used per person in a year, in kilowatt-hours.'),
        description=(
            _('Electric power consumption is the electricity a country\'s homes, businesses and industry use in a year, '
            'divided by its population, in kilowatt-hours. It is production plus imports minus exports and the losses '
            'in transmission and distribution. The International Energy Agency (IEA) compiles it from national energy '
            'statistics, and the World Bank republishes it.')
        ),
        model=geo.ElectricityConsumptionCountryYear,
        series=(Series('value', _('Electricity consumption per person'), 'kwh', measured_in=pgettext_lazy('measured in', 'kWh per person'), log_scale=True),),
        tags=Tags('Environment', (_('Energy'), _('Electricity'), _('IEA'))),
        keywords=(_('power consumption'), _('electricity use'), _('kilowatt-hours')),
    ),
    Metric(
        slug='water-stress',
        title=_('Water stress'),
        question=_('Where is fresh water running short?'),
        summary=_('How much of a country\'s renewable fresh water is withdrawn each year.'),
        description=(
            _('Water stress is the fresh water withdrawn by farms, industry and households in a year as a share of the '
            'renewable fresh water available, after the flows that nature needs are set aside. Above 25% a country is '
            'under water stress by the UN\'s definition; above 100% it uses more than renews, drawing down groundwater '
            'or desalinating. The UN Food and Agriculture Organization (FAO) compiles it in its AQUASTAT database for '
            'the UN\'s water goal, and the World Bank republishes it.')
        ),
        model=geo.WaterStressCountryYear,
        series=(Series('value', _('Water stress'), 'percent', measured_in=pgettext_lazy('measured in', '% of renewable fresh water withdrawn'), better='lower', log_scale=True),),
        tags=Tags('Environment', (_('Water'), _('Scarcity'), _('FAO'))),
        keywords=(_('water scarcity'), _('drought'), _('freshwater'), _('irrigation')),
    ),
    # ---------- Governance and society ----------
    Metric(
        slug='governance-indicators',
        title=_('Worldwide Governance Indicators'),
        question=_('Which countries are governed best?'),
        summary=_('Six World Bank scores for how a country is governed, from about -2.5 (worst) to 2.5 (best).'),
        description=(
            _('The Worldwide Governance Indicators sum up how a country is governed in six scores: rule of law, '
            'government effectiveness, regulatory quality, voice and accountability, political stability and the '
            'absence of violence, and control of corruption. Each runs from about -2.5 (worst) to 2.5 (best), with 0 '
            'the average across countries. The World Bank builds them from more than 30 sources: surveys of firms and '
            'households, and assessments by experts, NGOs and international organisations. They measure perceptions, '
            'and small differences between countries are within the margin of error.')
        ),
        model=geo.GovernanceIndicatorsCountryYear,
        series=(
            Series('rule_of_law', _('Rule of law'), 'score', measured_in=pgettext_lazy('measured in', '-2.5 to 2.5'), better='higher', short=_('Rule of law')),
            Series('effectiveness', _('Government effectiveness'), 'score', measured_in=pgettext_lazy('measured in', '-2.5 to 2.5'), better='higher', short=_('Effectiveness')),
            Series('regulation', _('Regulatory quality'), 'score', measured_in=pgettext_lazy('measured in', '-2.5 to 2.5'), better='higher', short=_('Regulation')),
            Series('voice', _('Voice and accountability'), 'score', measured_in=pgettext_lazy('measured in', '-2.5 to 2.5'), better='higher', short=_('Voice and accountability')),
            Series('stability', _('Political stability and absence of violence'), 'score', measured_in=pgettext_lazy('measured in', '-2.5 to 2.5'), better='higher', short=_('Stability')),
            Series('corruption', _('Control of corruption'), 'score', measured_in=pgettext_lazy('measured in', '-2.5 to 2.5'), better='higher', short=_('Control of corruption')),
        ),
        tags=Tags('Governance', (_('Governance'), _('Rule of law'), _('Institutions'), _('World Bank'))),
        keywords=(_('wgi'), _('government quality'), _('institutions'), _('regulation'), _('stability')),
    ),
    Metric(
        slug='rule-of-law',
        title=_('Rule of law index (V-Dem)'),
        question=_('Where does the law bind everyone, rulers included?'),
        summary=_('How far laws are clear, public, stable and applied equally, including to the government, from 0 to 1.'),
        description=(
            _('The V-Dem rule of law index measures how far laws are transparent and applied equally, how far the '
            'courts and the public administration are independent and free of corruption, and how far the government '
            'itself obeys the law. It runs from 0 (least) to 1 (most). Like the other V-Dem indices, it combines the '
            'ratings of thousands of country experts through a statistical model. Our World in Data republishes the '
            'central estimates.')
        ),
        model=geo.RuleOfLawCountryYear,
        series=(Series('value', _('Rule of law index'), 'index', measured_in=pgettext_lazy('measured in', '0 to 1'), better='higher'),),
        tags=Tags('Governance', (_('Rule of law'), _('Courts'), _('V-Dem'))),
        keywords=(_('justice'), _('courts'), _('legal system'), _('vdem')),
    ),
    Metric(
        slug='freedom-of-expression',
        title=_('Freedom of expression index (V-Dem)'),
        question=_('Where can people speak and publish freely?'),
        summary=_('How free the press, the media and ordinary people are to speak, from 0 to 1.'),
        description=(
            _('The V-Dem freedom of expression and alternative sources of information index measures how far the '
            'government respects press and media freedom, how free people are to discuss politics at home and in '
            'public, how free academic and cultural expression is, and how far the media offer a range of views. It '
            'runs from 0 (least free) to 1 (most free). Like the other V-Dem indices, it combines the ratings of '
            'thousands of country experts through a statistical model. Our World in Data republishes the central '
            'estimates.')
        ),
        model=geo.FreedomOfExpressionCountryYear,
        series=(Series('value', _('Freedom of expression index'), 'index', measured_in=pgettext_lazy('measured in', '0 to 1'), better='higher'),),
        tags=Tags('Governance', (_('Press freedom'), _('Free speech'), _('Media'), _('V-Dem'))),
        keywords=(_('press freedom'), _('censorship'), _('journalists'), _('free speech'), _('vdem')),
    ),
    Metric(
        slug='conflict-deaths',
        title=_('Deaths in armed conflicts'),
        question=_('Where are people being killed in wars?'),
        summary=_('People killed in armed conflicts in each country, by year.'),
        description=(
            _('This counts the people killed in armed conflicts in a country in a year: soldiers and civilians, in '
            'wars between states, civil wars, fighting between armed groups and one-sided violence against civilians. '
            'Deaths are assigned to the country where they happened. The Uppsala Conflict Data Program (UCDP) records '
            'every event from news reports, NGO and UN sources and other documents, and gives its best estimate; '
            'Our World in Data republishes it. The current year is left out until it is complete.')
        ),
        model=geo.ConflictDeathsCountryYear,
        series=(Series('value', _('Deaths in armed conflicts'), 'people', measured_in=pgettext_lazy('measured in', 'people'), better='lower', log_scale=True, total=True),),
        tags=Tags('Governance', (_('War'), _('Conflict'), _('Violence'), _('UCDP'))),
        keywords=(_('war'), _('civil war'), _('battle deaths'), _('violence'), _('terrorism')),
        default_countries=('UKR', 'SDN', 'MMR', 'COD', 'ETH'),
    ),
    Metric(
        slug='arms-imports',
        title=_('Arms imports'),
        question=_('Who buys the most weapons?'),
        summary=_('The volume of major weapons a country imports, in SIPRI\'s trend-indicator values.'),
        description=(
            _('Arms imports are the deliveries of major conventional weapons, such as aircraft, ships, tanks, missiles '
            'and artillery, that a country received in a year. The Stockholm International Peace Research Institute '
            '(SIPRI) values them in its trend-indicator value, a measure of military capability based on production '
            'costs rather than the price paid, in constant 1990 US dollars, so that volumes can be compared across '
            'years and countries. Small arms are not included. Deliveries are lumpy, so single years jump. The World '
            'Bank republishes the figures.')
        ),
        model=geo.ArmsImportsCountryYear,
        series=(Series('value', _('Arms imports'), 'usd', measured_in=pgettext_lazy('measured in', 'constant 1990 US$, SIPRI trend-indicator values'), log_scale=True, total=True),),
        tags=Tags('Governance', (_('Defence'), _('Weapons'), _('Arms trade'), _('SIPRI'))),
        keywords=(_('weapons'), _('arms trade'), _('military'), _('sipri')),
        default_countries=('IND', 'SAU', 'UKR', 'CHN', 'EGY'),
    ),
    Metric(
        slug='lgbt-rights',
        title=_('LGBT+ rights'),
        question=_('Where does the law protect LGBT+ people?'),
        summary=_('An index of laws that protect or discriminate against LGBT+ people, in points.'),
        description=(
            _('The LGBT+ Policy Index scores each country\'s laws on sexual orientation and gender identity. Laws that '
            'protect, such as the right to marry, to adopt or to be shielded from discrimination, add points; laws '
            'that discriminate, such as criminalising same-sex relations, subtract them. It covers 18 kinds of law, '
            'weighted by how much they matter, and runs from strongly negative to strongly positive. Kristopher Velasco '
            '(Princeton University) compiles it from legal records, and Our World in Data republishes it.')
        ),
        model=geo.LgbtRightsCountryYear,
        series=(Series('value', _('LGBT+ Policy Index'), 'points', measured_in=pgettext_lazy('measured in', 'points'), better='higher'),),
        tags=Tags('Society', (_('Rights'), _('LGBT'), _('Equality'))),
        keywords=(_('gay rights'), _('same-sex marriage'), _('discrimination'), _('equality'), _('lgbtq')),
    ),
    Metric(
        slug='minimum-wage',
        title=_('Minimum wage'),
        question=_('Where is the minimum wage highest?'),
        summary=_('The legal monthly minimum wage, in dollars that buy the same everywhere and in US dollars.'),
        description=(
            _('This is the statutory gross monthly minimum wage, the lowest pay the law allows for a full month of '
            'work, as it stood at the end of each year. The first measure converts it to international dollars at '
            'purchasing power parity, so it compares what the wage buys at home; the second converts it at the '
            'exchange rate. Where several minimum wages exist, the ILO takes the national one or the rate for '
            'unskilled workers. Countries that set wages by collective agreement instead, such as Austria, Italy and '
            'the Nordic countries, have none. The International Labour Organization (ILO) compiles the figures from '
            'national laws and labour ministries in its ILOSTAT database.')
        ),
        model=geo.MinimumWageCountryYear,
        series=(
            Series('ppp', _('Minimum wage, PPP (international $ a month)'), 'usd', measured_in=pgettext_lazy('measured in', 'international $ a month'), better='higher', log_scale=True, short=_('PPP')),
            Series('usd', _('Minimum wage, US$ a month'), 'usd', measured_in=pgettext_lazy('measured in', 'US$ a month'), better='higher', log_scale=True, short=_('US$')),
        ),
        tags=Tags('Economy', (_('Labour market'), _('Wages'), _('Minimum wage'), _('ILO'))),
        keywords=(_('pay'), _('salary'), _('wages'), _('low pay'), _('workers')),
    ),
    Metric(
        slug='gdp-per-capita-long-run',
        opens_from=1820,
        title=_('GDP per capita since 1820'),
        question=_('How did living standards grow over the centuries?'),
        summary=_('GDP per person over two centuries, adjusted for prices across countries and time.'),
        description=(
            _('The Maddison Project Database is the longest series of GDP per person there is: for some countries it '
            'reaches back to the Middle Ages, for most to the nineteenth century. The values are in international '
            'dollars of 2011, so they are comparable across countries and years. The project, founded by the '
            'economic historian Angus Maddison and continued at the University of Groningen, pieces together the '
            'work of hundreds of historians; the early figures are estimates, and the recent ones follow the '
            'national accounts. Our World in Data republishes the database.')
        ),
        model=geo.MaddisonGdpPerCapitaCountryYear,
        series=(Series('value', _('GDP per capita, 2011 international $'), 'usd', measured_in=pgettext_lazy('measured in', 'international $ of 2011'), log_scale=True),),
        tags=Tags('Economy', (_('GDP'), _('Long run'), _('Maddison'), _('Economic history'))),
        keywords=(_('maddison'), _('historical gdp'), _('living standards'), _('economic history'), _('industrial revolution')),
    ),
    Metric(
        slug='voter-turnout',
        opens_from=1900,
        title=_('Voter turnout'),
        question=_('How many of those who could vote did?'),
        summary=_('Voters as a share of registered voters, in each national election.'),
        description=(
            _('Voter turnout is the share of registered voters who voted in a national election, for the presidency '
            'or the legislature. It is measured only in election years, so the line skips the years between. The '
            'Varieties of Democracy project (V-Dem) collects the figures from electoral authorities and historical '
            'sources, back to the first elections of the nineteenth century. Where voting is compulsory, as in '
            'Brazil, turnout is higher by law.')
        ),
        model=geo.VoterTurnoutCountryYear,
        series=(Series('value', _('Turnout, % of registered voters'), 'percent', measured_in=pgettext_lazy('measured in', '% of registered voters'), better='higher'),),
        tags=Tags('Governance', (_('Elections'), _('Democracy'), _('V-Dem'))),
        keywords=(_('elections'), _('voting'), _('participation'), _('abstention')),
    ),
    Metric(
        slug='schooling-long-run',
        opens_from=1870,
        title=_('Years of schooling since 1870'),
        question=_('How did education spread over 150 years?'),
        summary=_('The average years of schooling of people aged 15 to 64, every five years since 1870.'),
        description=(
            _('This is the average number of years of school completed by people aged 15 to 64, every five years '
            'from 1870. The economists Jong-Wha Lee and Hanol Lee built the series from censuses, enrolment records '
            'and historical statistics, extending the Barro-Lee dataset back in time. It shows how mass education '
            'spread: from about four years in the richest countries of 1870 to more than twelve today. The '
            'Schooling page gives the UN\'s yearly figures for recent decades.')
        ),
        model=geo.SchoolingLongRunCountryYear,
        series=(Series('value', _('Average years of schooling'), 'years', measured_in=pgettext_lazy('measured in', 'years'), better='higher'),),
        tags=Tags('Education', (_('Schooling'), _('Long run'), _('Barro-Lee'))),
        keywords=(_('education'), _('literacy'), _('school years'), _('educational attainment')),
    ),
    Metric(
        slug='calorie-supply',
        opens_from=1800,
        title=_('Food supply per person'),
        question=_('How much food does each country have per person?'),
        summary=_('The calories available per person and day, from the food a country produces and imports.'),
        description=(
            _('Food supply is the energy in the food available for people to eat, in kilocalories per person and '
            'day: what a country produces and imports, minus exports, animal feed, seed and waste before the '
            'kitchen. It is not what people actually eat, which is lower, but it tracks how well fed a population '
            'is; about 2,000 to 2,500 kilocalories a day is a healthy supply for an adult. The Food and Agriculture '
            'Organization (FAO) compiles it from food balance sheets, and Our World in Data joins it with '
            'historical estimates for some countries.')
        ),
        model=geo.CalorieSupplyCountryYear,
        series=(Series('value', _('Kilocalories per person and day'), 'kcal', measured_in=pgettext_lazy('measured in', 'kcal per person and day'), better='higher'),),
        tags=Tags('Food', (_('Food supply'), _('Nutrition'), _('FAO'))),
        keywords=(_('calories'), _('diet'), _('hunger'), _('food availability')),
    ),
    Metric(
        slug='total-factor-productivity',
        title=_('Total factor productivity'),
        question=_('Which economies get more out of their workers and capital?'),
        summary=_('How much output an economy gets from its labour and capital together, relative to 2017.'),
        description=(
            _('Total factor productivity (TFP) is the part of output that is not explained by how much labour and '
            'capital an economy uses: technology, organisation, skills and institutions. The Penn World Table '
            'computes it at constant national prices, as an index where each country\'s 2017 value is 1, so it '
            'shows how a country\'s productivity changed over time, not how it compares with others. The table is '
            'maintained at the University of Groningen and the University of California, Davis, and Our World in '
            'Data republishes it.')
        ),
        model=geo.TotalFactorProductivityCountryYear,
        series=(Series('value', _('Total factor productivity, 2017 = 1'), 'index', measured_in=pgettext_lazy('measured in', 'index, 2017 = 1'), better='higher'),),
        tags=Tags('Economy', (_('Productivity'), _('Growth'), _('Penn World Table'))),
        keywords=(_('tfp'), _('efficiency'), _('technology'), _('solow residual')),
    ),
    Metric(
        slug='fossil-fuel-production',
        opens_from=1900,
        title=_('Oil and coal production'),
        question=_('Who produces the oil and the coal?'),
        summary=_('Each country\'s production of oil and of coal, in terawatt-hours of energy.'),
        description=(
            _('This is how much oil and how much coal each country produces in a year, measured by the energy they '
            'contain, in terawatt-hours, so the two can be compared. The Energy Institute\'s Statistical Review of '
            'World Energy gives the figures from 1965 (coal from 1981), and Our World in Data extends them back to '
            '1900 with historical sources, such as Etemad and Luciani for oil.')
        ),
        model=geo.FossilFuelProductionCountryYear,
        series=(
            Series('oil', _('Oil production'), 'twh', measured_in=pgettext_lazy('measured in', 'TWh'), log_scale=True, short=_('Oil'), total=True),
            Series('coal', _('Coal production'), 'twh', measured_in=pgettext_lazy('measured in', 'TWh'), log_scale=True, short=_('Coal'), total=True),
        ),
        tags=Tags('Environment', (_('Energy'), _('Fossil fuels'), _('Oil'), _('Coal'))),
        keywords=(_('petroleum'), _('crude oil'), _('mining'), _('opec'), _('energy production')),
        default_countries=('USA', 'SAU', 'RUS', 'CHN', 'BRA', 'NOR'),
    ),
    Metric(
        slug='net-migration',
        title=_('Net migration'),
        question=_('Which countries gain people from migration, and which lose them?'),
        summary=_('The people who moved in minus the people who moved out, each year.'),
        description=(
            _('Net migration is the number of immigrants minus the number of emigrants in a year, including citizens '
            'and foreigners. A positive number means more people arrived than left. The UN Population Division '
            'estimates it in its World Population Prospects from censuses, registers and surveys, often as the '
            'difference between population change and births minus deaths, and the World Bank republishes it. '
            'The totals are large for large countries: the United States gains more people than Luxembourg could.')
        ),
        model=geo.NetMigrationCountryYear,
        series=(Series('value', _('Net migration'), 'people', measured_in=pgettext_lazy('measured in', 'people a year'), total=True),),
        tags=Tags('Demography', (_('Migration'), _('Population'), _('UN'))),
        keywords=(_('immigration'), _('emigration'), _('migrants'), _('population change')),
    ),
    Metric(
        slug='birth-and-death-rates',
        title=_('Birth and death rates'),
        question=_('How many people are born, and how many die, per thousand?'),
        summary=_('Births and deaths in a year per 1,000 people.'),
        description=(
            _('The crude birth rate is the number of births in a year per 1,000 people, and the crude death rate '
            'the number of deaths. The difference between them is a population\'s natural growth, before migration. '
            'They are called crude because they take no account of age: an old population has a high death rate '
            'even when people live long. The UN Population Division estimates them in its World Population '
            'Prospects, and the World Bank republishes them.')
        ),
        model=geo.BirthDeathRatesCountryYear,
        series=(
            Series('births', _('Births per 1,000 people'), 'per_1000', measured_in=pgettext_lazy('measured in', 'per 1,000 people'), short=_('Births')),
            Series('deaths', _('Deaths per 1,000 people'), 'per_1000', measured_in=pgettext_lazy('measured in', 'per 1,000 people'), short=_('Deaths')),
        ),
        tags=Tags('Demography', (_('Births'), _('Deaths'), _('Population'))),
        keywords=(_('natality'), _('mortality'), _('natural increase'), _('crude birth rate'), _('crude death rate')),
    ),
    Metric(
        slug='population-growth',
        title=_('Population growth'),
        question=_('Whose population grows fastest, and whose shrinks?'),
        summary=_('How much a country\'s population grew or shrank in a year, in percent.'),
        description=(
            _('Population growth is the change in a country\'s population from one year to the next, in percent, '
            'counting births, deaths and migration together. The World Bank computes it from the UN Population '
            'Division\'s estimates. Growth above 3% a year, as in parts of Africa, doubles a population in about 23 '
            'years; several countries in Europe and East Asia now shrink.')
        ),
        model=geo.PopulationGrowthCountryYear,
        series=(Series('value', _('Population growth, % a year'), 'percent', measured_in=pgettext_lazy('measured in', '% a year')),),
        tags=Tags('Demography', (_('Population'), _('Growth'))),
        keywords=(_('demographics'), _('population change'), _('depopulation')),
    ),
    Metric(
        slug='gni-per-capita',
        title=_('GNI per capita'),
        question=_('How much income does each country\'s people earn per person?'),
        summary=_('Gross national income per person in US dollars, as the World Bank ranks countries by income.'),
        description=(
            _('Gross national income (GNI) is GDP plus the income a country\'s people and companies earn abroad, '
            'minus what foreigners earn in it. Per person and in US dollars by the Atlas method, which smooths '
            'exchange rates over three years, it is the figure the World Bank uses to class countries as low, '
            'middle or high income. In 2025 a country was high income above about $14,000 per person.')
        ),
        model=geo.GniPerCapitaCountryYear,
        series=(Series('value', _('GNI per capita, Atlas method'), 'usd', measured_in=pgettext_lazy('measured in', 'current US$'), log_scale=True),),
        tags=Tags('Economy', (_('National income'), _('GNI'), _('Income groups'))),
        keywords=(_('gross national income'), _('atlas method'), _('income level'), _('high income'), _('low income')),
    ),
    Metric(
        slug='household-consumption',
        title=_('Household consumption'),
        question=_('How much of the economy is what households spend?'),
        summary=_('What households spend on goods and services, as a share of GDP.'),
        description=(
            _('Household final consumption is what households spend on goods and services, from food and rent to '
            'cars and holidays, as a share of GDP. It is the largest part of most economies: about two thirds of '
            'GDP in the United States, less than two fifths in China, where investment and exports weigh more. The '
            'World Bank computes it from national accounts.')
        ),
        model=geo.HouseholdConsumptionCountryYear,
        series=(Series('value', _('Household consumption, % of GDP'), 'percent', measured_in=pgettext_lazy('measured in', '% of GDP')),),
        tags=Tags('Economy', (_('Consumption'), _('National accounts'), _('Households'))),
        keywords=(_('consumer spending'), _('private consumption'), _('demand')),
    ),
    Metric(
        slug='exchange-rate',
        title=_('Exchange rate'),
        question=_('How much of each currency does a dollar buy?'),
        summary=_('Units of a country\'s currency per US dollar, averaged over the year.'),
        description=(
            _('The official exchange rate is how many units of a country\'s currency one US dollar bought, averaged '
            'over the year, as the central bank or the market set it. A rising line means the currency weakened. '
            'The World Bank takes the rates from the IMF\'s International Financial Statistics. Rates are in '
            'today\'s units: Brazil\'s early values are in reais although the real only existed from 1994, and '
            'eurozone countries show the euro before 1999, converted at their fixed rates.')
        ),
        model=geo.ExchangeRateCountryYear,
        series=(Series('value', _('Local currency per US dollar'), 'currency', measured_in=pgettext_lazy('measured in', 'local currency per US$'), log_scale=True),),
        tags=Tags('Economy', (_('Currency'), _('Exchange rates'), _('IMF'))),
        keywords=(_('currency'), _('devaluation'), _('dollar'), _('forex')),
        default_countries=('BRA', 'DEU', 'GBR', 'JPN', 'IND', 'MEX'),
    ),
    Metric(
        slug='export-structure',
        title=_('Exports by kind'),
        question=_('What do countries sell to the world?'),
        summary=_('Fuels, manufactures, food, farm materials and metals as shares of a country\'s goods exports.'),
        description=(
            _('This splits a country\'s exports of goods into five kinds, each as a share of the total: fuels, '
            'manufactured goods, food, agricultural raw materials such as cotton and timber, and ores and metals. '
            'Together they show what an economy sells to the world: Germany mostly manufactures, Saudi Arabia '
            'fuels, Brazil food and metals. The figures come from the UN\'s Comtrade database through the World '
            'Bank; services such as tourism and software are not goods, so they are not included.')
        ),
        model=geo.ExportStructureCountryYear,
        series=(
            Series('manufactures', _('Manufactured goods'), 'percent', measured_in=pgettext_lazy('measured in', '% of goods exports'), short=_('Manufactures')),
            Series('fuel', _('Fuels'), 'percent', measured_in=pgettext_lazy('measured in', '% of goods exports'), short=_('Fuels')),
            Series('food', _('Food'), 'percent', measured_in=pgettext_lazy('measured in', '% of goods exports'), short=_('Food')),
            Series('agriculture', _('Agricultural raw materials'), 'percent', measured_in=pgettext_lazy('measured in', '% of goods exports'), short=_('Farm materials')),
            Series('metals', _('Ores and metals'), 'percent', measured_in=pgettext_lazy('measured in', '% of goods exports'), short=_('Metals')),
        ),
        tags=Tags('Economy', (_('Trade'), _('Exports'), _('Commodities'))),
        keywords=(_('export structure'), _('commodity exports'), _('industrialisation'), _('oil exports'), _('resource dependence')),
    ),
    Metric(
        slug='cereal-yield',
        title=_('Cereal yield'),
        question=_('How much grain does a hectare of land produce?'),
        summary=_('Kilograms of cereals harvested per hectare of land.'),
        description=(
            _('Cereal yield is the weight of wheat, rice, maize, barley and other grains harvested per hectare of '
            'the land sown with them, in kilograms. It is the plainest measure of how productive farming is, and '
            'of how far the Green Revolution of better seeds, fertiliser and irrigation has reached. The Food and '
            'Agriculture Organization (FAO) compiles it from national statistics, and the World Bank republishes '
            'it.')
        ),
        model=geo.CerealYieldCountryYear,
        series=(Series('value', _('Cereal yield, kg per hectare'), 'kg_ha', measured_in=pgettext_lazy('measured in', 'kg per hectare'), better='higher'),),
        tags=Tags('Food', (_('Agriculture'), _('Yields'), _('FAO'))),
        keywords=(_('crop yield'), _('wheat'), _('rice'), _('maize'), _('farming'), _('green revolution')),
    ),
    Metric(
        slug='food-production',
        title=_('Food production'),
        question=_('Where is food production growing?'),
        summary=_('How much food a country produces, as an index where 2014 to 2016 is 100.'),
        description=(
            _('The food production index measures the volume of food a country produces, compared with the '
            'average of 2014 to 2016, which is set to 100. It covers crops and animals that people can eat, so '
            'coffee and tea are left out because they have no nutritional value. The Food and Agriculture '
            'Organization (FAO) computes it with international prices as weights, and the World Bank republishes '
            'it. It shows how fast production grew in each country, not how much it produces compared with others.')
        ),
        model=geo.FoodProductionCountryYear,
        series=(Series('value', _('Food production index, 2014–2016 = 100'), 'points', measured_in=pgettext_lazy('measured in', 'index, 2014–2016 = 100')),),
        tags=Tags('Food', (_('Agriculture'), _('Production'), _('FAO'))),
        keywords=(_('harvest'), _('agricultural output'), _('farming')),
    ),
    Metric(
        slug='land-use',
        title=_('Farmland'),
        question=_('How much of each country is farmed?'),
        summary=_('Agricultural land as a share of the land area, and arable land per person.'),
        description=(
            _('Agricultural land is the share of a country\'s land under crops, meadows and pastures. Arable land '
            'is the part under temporary crops, such as grain, and the amount per person says how much farmland '
            'each inhabitant has: less than a tenth of a hectare in Japan, more than a hectare in Canada. The '
            'Food and Agriculture Organization (FAO) compiles both, and the World Bank republishes them.')
        ),
        model=geo.LandUseCountryYear,
        series=(
            Series('agricultural', _('Agricultural land, % of land area'), 'percent', measured_in=pgettext_lazy('measured in', '% of land area'), short=_('Agricultural land')),
            Series('arable_per_person', _('Arable land per person'), 'hectares', measured_in=pgettext_lazy('measured in', 'hectares per person'), short=_('Arable land per person')),
        ),
        tags=Tags('Environment', (_('Land'), _('Agriculture'), _('FAO'))),
        keywords=(_('farmland'), _('cropland'), _('pasture'), _('land use')),
    ),
    Metric(
        slug='telephones',
        title=_('Telephones'),
        question=_('How did the telephone, then the mobile phone, spread?'),
        summary=_('Fixed telephone lines and mobile subscriptions per 100 people.'),
        description=(
            _('Fixed telephone lines are the landlines in service per 100 people; mobile subscriptions are the '
            'active mobile phone contracts and prepaid cards per 100 people, which can exceed 100 where people have '
            'several. Together they trace how the telephone spread over sixty years, and how in poorer countries '
            'the mobile phone arrived before the landline ever did. The International Telecommunication Union '
            '(ITU) compiles the figures from operators and regulators, and the World Bank republishes them.')
        ),
        model=geo.TelephonesCountryYear,
        series=(
            Series('mobile', _('Mobile subscriptions per 100 people'), 'per_100', measured_in=pgettext_lazy('measured in', 'per 100 people'), short=_('Mobile')),
            Series('fixed', _('Fixed telephone lines per 100 people'), 'per_100', measured_in=pgettext_lazy('measured in', 'per 100 people'), short=_('Fixed lines')),
        ),
        tags=Tags('Society', (_('Technology'), _('Telecommunications'), _('ITU'))),
        keywords=(_('mobile phones'), _('cell phones'), _('landlines'), _('smartphones'), _('connectivity')),
    ),
    Metric(
        slug='air-passengers',
        title=_('Air passengers'),
        question=_('Who flies the most?'),
        summary=_('The passengers carried by each country\'s airlines in a year.'),
        description=(
            _('Air passengers carried are the people who flew with the airlines registered in a country, on '
            'domestic and international flights, in a year. The figures follow the airline, not the airport: '
            'passengers on a German airline count for Germany wherever they fly. The International Civil Aviation '
            'Organization (ICAO) compiles them from the airlines, and the World Bank republishes them. The '
            'pandemic of 2020 shows as a collapse everywhere.')
        ),
        model=geo.AirPassengersCountryYear,
        series=(Series('value', _('Passengers carried'), 'people', measured_in=pgettext_lazy('measured in', 'passengers a year'), log_scale=True, total=True),),
        tags=Tags('Society', (_('Transport'), _('Aviation'), _('ICAO'))),
        keywords=(_('flights'), _('airlines'), _('aviation'), _('travel')),
    ),
    Metric(
        slug='adult-mortality',
        title=_('Adult mortality'),
        question=_('How likely is it to die between 15 and 60?'),
        summary=_('Of 1,000 people aged 15, how many would die before 60 at this year\'s death rates.'),
        description=(
            _('The adult mortality rate is the probability that a 15-year-old dies before turning 60, per 1,000, if '
            'the death rates of that year held. It captures deaths in working age, from illness, accidents and '
            'violence, which child mortality and life expectancy at birth blur. Men die younger than women almost '
            'everywhere. The UN Population Division estimates the rates in its World Population Prospects, and the '
            'World Bank republishes them.')
        ),
        model=geo.AdultMortalityCountryYear,
        series=(
            Series('men', _('Men dying between 15 and 60, per 1,000'), 'per_1000', measured_in=pgettext_lazy('measured in', 'per 1,000 men'), better='lower', short=_('Men')),
            Series('women', _('Women dying between 15 and 60, per 1,000'), 'per_1000', measured_in=pgettext_lazy('measured in', 'per 1,000 women'), better='lower', short=_('Women')),
        ),
        tags=Tags('Health', (_('Mortality'), _('Adults'), _('UN'))),
        keywords=(_('premature death'), _('death rate'), _('working age'), _('men and women')),
    ),
    Metric(
        slug='terrorism-deaths',
        title=_('Deaths from terrorism'),
        question=_('Where do terrorist attacks kill the most people?'),
        summary=_('People killed in terrorist attacks in each country and year.'),
        description=(
            _('This is the number of people killed in terrorist attacks in a country in a year, attackers included. '
            'The Global Terrorism Database, kept by the University of Maryland\'s START consortium, records attacks '
            'from news reports since 1970: the violent use of force by non-state actors to reach a political, '
            'economic, religious or social goal. Our World in Data republishes it. The count depends on what '
            'the press reports, so it is less complete in countries with little press, and 1993 is missing from '
            'the database.')
        ),
        model=geo.TerrorismDeathsCountryYear,
        series=(Series('value', _('People killed'), 'people', measured_in=pgettext_lazy('measured in', 'deaths a year'), better='lower', log_scale=True, total=True),),
        tags=Tags('Governance', (_('Terrorism'), _('Violence'), _('Global Terrorism Database'))),
        keywords=(_('terror attacks'), _('terrorist'), _('bombings'), _('violence')),
    ),
    Metric(
        slug='labour-force-participation',
        title=_('Labour force participation'),
        question=_('How many adults work or look for work?'),
        summary=_('People who work or look for work, as a share of everyone aged 15 and over.'),
        description=(
            _('The labour force participation rate is the share of people aged 15 and over who are in the labour '
            'force: employed, or without work but looking for it. Students, pensioners, people who care for family '
            'at home and those who have given up looking are outside it. It falls where populations age and where '
            'the young study longer, and rises where women enter paid work. The International Labour Organization '
            '(ILO) models it from labour force surveys, and the World Bank republishes it.')
        ),
        model=geo.LabourForceParticipationCountryYear,
        series=(Series('value', _('Labour force, % of people aged 15 and over'), 'percent', measured_in=pgettext_lazy('measured in', '% of people aged 15 and over')),),
        tags=Tags('Economy', (_('Labour'), _('Employment'), _('ILO'))),
        keywords=(_('activity rate'), _('workforce'), _('working age'), _('inactivity')),
    ),
    Metric(
        slug='employment-by-sector',
        title=_('Employment by sector'),
        question=_('Do people work on farms, in factories or in services?'),
        summary=_('Where people work: agriculture, industry or services, and how many work for themselves.'),
        description=(
            _('This splits everyone employed into the three sectors they work in, as shares of the total: '
            'agriculture, including fishing and forestry; industry, including mining, manufacturing and '
            'construction; and services, from shops to schools. As countries grow richer, work moves from farms to '
            'factories and then to services. The share who are self-employed, working for themselves or in a '
            'family business rather than for a wage, is high where formal jobs are scarce. The International '
            'Labour Organization (ILO) models the figures from labour force surveys, and the World Bank republishes '
            'them.')
        ),
        model=geo.EmploymentBySectorCountryYear,
        series=(
            Series('services', _('Employment in services'), 'percent', measured_in=pgettext_lazy('measured in', '% of employment'), short=_('Services')),
            Series('industry', _('Employment in industry'), 'percent', measured_in=pgettext_lazy('measured in', '% of employment'), short=_('Industry')),
            Series('agriculture', _('Employment in agriculture'), 'percent', measured_in=pgettext_lazy('measured in', '% of employment'), short=_('Agriculture')),
            Series('self_employed', _('Self-employed'), 'percent', measured_in=pgettext_lazy('measured in', '% of employment'), short=_('Self-employed')),
        ),
        tags=Tags('Economy', (_('Labour'), _('Employment'), _('Sectors'), _('ILO'))),
        keywords=(_('workers'), _('farming jobs'), _('manufacturing jobs'), _('informal work'), _('self-employment')),
    ),
    Metric(
        slug='youth-neet',
        title=_('Young people not in work or school'),
        question=_('How many young people are neither working nor studying?'),
        summary=_('People aged 15 to 24 who are not in employment, education or training.'),
        description=(
            _('The NEET rate is the share of people aged 15 to 24 who are not in employment, education or '
            'training: neither working, nor at school, nor learning a trade. It catches young people the '
            'unemployment rate misses, because those who are not looking for work do not count as unemployed. The '
            'International Labour Organization (ILO) compiles it from labour force surveys, and the World Bank '
            'republishes it.')
        ),
        model=geo.YouthNeetCountryYear,
        series=(Series('value', _('NEET rate, % of people aged 15 to 24'), 'percent', measured_in=pgettext_lazy('measured in', '% of people aged 15 to 24'), better='lower'),),
        tags=Tags('Economy', (_('Labour'), _('Youth'), _('ILO'))),
        keywords=(_('neet'), _('youth'), _('idle youth'), _('young people')),
    ),
    Metric(
        slug='patents',
        title=_('Patent applications'),
        question=_('Where are the most inventions patented?'),
        summary=_('Patent applications filed in each country, by its residents and by foreigners.'),
        description=(
            _('Patent applications are the requests for a patent filed with a country\'s patent office in a year. '
            'Those by residents show how much a country\'s own people and companies invent; those by non-residents '
            'show how attractive its market is to foreign inventors, who patent where they expect to sell. The '
            'World Intellectual Property Organization (WIPO) compiles the counts from patent offices, and the '
            'World Bank republishes them. China has filed the most since 2011.')
        ),
        model=geo.PatentsCountryYear,
        series=(
            Series('residents', _('Applications by residents'), 'count', measured_in=pgettext_lazy('measured in', 'applications a year'), log_scale=True, short=_('By residents'), total=True),
            Series('non_residents', _('Applications by non-residents'), 'count', measured_in=pgettext_lazy('measured in', 'applications a year'), log_scale=True, short=_('By non-residents'), total=True),
        ),
        tags=Tags('Education', (_('Innovation'), _('Research'), _('WIPO'))),
        keywords=(_('inventions'), _('innovation'), _('intellectual property'), _('technology')),
    ),
    Metric(
        slug='market-cap',
        title=_('Stock market size'),
        question=_('How big is each country\'s stock market?'),
        summary=_('The value of all listed domestic companies, as a share of GDP.'),
        description=(
            _('Market capitalisation is the value of all the shares of the companies listed on a country\'s stock '
            'exchanges, at the year\'s end, as a share of GDP. It says how large a role the stock market plays in '
            'financing companies: large in the United States, Switzerland and Hong Kong, small where companies '
            'borrow from banks instead. It also rises and falls with share prices. The World Bank compiles it '
            'from the World Federation of Exchanges.')
        ),
        model=geo.MarketCapCountryYear,
        series=(Series('value', _('Market capitalisation, % of GDP'), 'percent', measured_in=pgettext_lazy('measured in', '% of GDP')),),
        tags=Tags('Economy', (_('Finance'), _('Stock markets'), _('Companies'))),
        keywords=(_('stock exchange'), _('shares'), _('equities'), _('capital markets')),
    ),
    Metric(
        slug='prison-population',
        title=_('Prison population'),
        question=_('Which countries imprison the most people?'),
        summary=_('People in prison per 100,000 inhabitants.'),
        description=(
            _('The prison population rate is the number of people held in prisons and remand centres per 100,000 '
            'inhabitants, including those awaiting trial. The World Prison Brief, kept by the Institute for Crime '
            'and Justice Policy Research in London, collects the figures from prison administrations, every year '
            'or two for most countries since 2000; Our World in Data republishes them. The United States and '
            'El Salvador imprison the largest shares of their people.')
        ),
        model=geo.PrisonPopulationCountryYear,
        series=(Series('value', _('Prisoners per 100,000 people'), 'per_100k', measured_in=pgettext_lazy('measured in', 'prisoners per 100,000 people'), log_scale=True),),
        tags=Tags('Society', (_('Crime'), _('Justice'), _('Prisons'))),
        keywords=(_('prisoners'), _('incarceration'), _('inmates'), _('jail')),
    ),
    Metric(
        slug='armed-forces',
        title=_('Armed forces personnel'),
        question=_('How large are the armies, compared with the population?'),
        summary=_('Soldiers and paramilitary forces per 1,000 people.'),
        description=(
            _('Armed forces personnel are the active soldiers and the paramilitary forces, such as gendarmeries, '
            'that a government keeps, per 1,000 people. Conscription, a hostile neighbour or a large security '
            'state all raise the figure. The International Institute for Strategic Studies (IISS) counts them in '
            'its yearly Military Balance, and the World Bank republishes them; the series stops in 2020. The '
            'Military spending page gives what the forces cost.')
        ),
        model=geo.ArmedForcesCountryYear,
        series=(Series('value', _('Armed forces personnel per 1,000 people'), 'per_1000', measured_in=pgettext_lazy('measured in', 'per 1,000 people'), log_scale=True),),
        tags=Tags('Governance', (_('Military'), _('Security'), _('IISS'))),
        keywords=(_('soldiers'), _('army'), _('military'), _('conscription'), _('troops')),
    ),
    Metric(
        slug='pisa',
        title=_('PISA scores'),
        question=_('How well do 15-year-olds read and do maths?'),
        summary=_('The average scores of 15-year-olds in the OECD\'s PISA tests of mathematics and reading.'),
        description=(
            _('PISA, the Programme for International Student Assessment, tests 15-year-olds in mathematics, reading '
            'and science every three years, in the same way everywhere, so the results compare across countries. '
            'The scale is set so that the OECD average was 500 points in the first round; about 40 points '
            'correspond to a year of schooling. The OECD runs the tests, with national samples of schools, and '
            'Our World in Data republishes the averages. The test of 2021 was moved to 2022 by the pandemic.')
        ),
        model=geo.PisaCountryYear,
        series=(
            Series('maths', _('Mathematics score'), 'points', measured_in=pgettext_lazy('measured in', 'PISA points'), better='higher', short=_('Mathematics')),
            Series('reading', _('Reading score'), 'points', measured_in=pgettext_lazy('measured in', 'PISA points'), better='higher', short=_('Reading')),
        ),
        tags=Tags('Education', (_('Schooling'), _('Test scores'), _('OECD'))),
        keywords=(_('pisa'), _('student performance'), _('school quality'), _('test results'), _('oecd')),
    ),
    Metric(
        slug='smoking',
        title=_('Smoking'),
        question=_('Where do most people smoke?'),
        summary=_('People aged 15 and over who use tobacco, in percent, and among men and women.'),
        description=(
            _('This is the share of people aged 15 and over who use tobacco, smoked or smokeless, and the shares '
            'among men and among women; it is age-standardised, so countries with young and old populations '
            'compare. Men smoke far more than women in most of Asia and Africa, while the gap is small in Europe. '
            'The World Health Organization estimates the rates from national surveys, every few years from 2000, '
            'and the World Bank republishes them.')
        ),
        model=geo.SmokingCountryYear,
        series=(
            Series('total', _('Tobacco use, % of people aged 15 and over'), 'percent', measured_in=pgettext_lazy('measured in', '% of people aged 15 and over'), better='lower', short=_('Everyone')),
            Series('men', _('Tobacco use among men'), 'percent', measured_in=pgettext_lazy('measured in', '% of men aged 15 and over'), better='lower', short=_('Men')),
            Series('women', _('Tobacco use among women'), 'percent', measured_in=pgettext_lazy('measured in', '% of women aged 15 and over'), better='lower', short=_('Women')),
        ),
        tags=Tags('Health', (_('Tobacco'), _('Risk factors'), _('WHO'))),
        keywords=(_('tobacco'), _('cigarettes'), _('smokers'), _('nicotine')),
    ),
    Metric(
        slug='tourism',
        title=_('Tourism'),
        question=_('Which countries do tourists visit, and who lives from them?'),
        summary=_('Tourist arrivals from abroad, and what tourism earns as a share of exports.'),
        description=(
            _('International tourist arrivals are the people who came from abroad for at least one night, for '
            'leisure, business or family, counted at the border or in hotels. Tourism receipts are what those '
            'visitors spent, as a share of the country\'s exports: tourism is an export, paid for in foreign '
            'money, and for islands like the Maldives it is most of them. UN Tourism, the United Nations\' tourism '
            'agency, compiles both, and the World Bank republishes them; the series stops in 2020, the year '
            'tourism collapsed.')
        ),
        model=geo.TourismCountryYear,
        series=(
            Series('arrivals', _('Tourist arrivals'), 'people', measured_in=pgettext_lazy('measured in', 'arrivals a year'), log_scale=True, short=_('Arrivals'), total=True),
            Series('receipts', _('Tourism receipts, % of exports'), 'percent', measured_in=pgettext_lazy('measured in', '% of exports'), short=_('Receipts')),
        ),
        tags=Tags('Economy', (_('Tourism'), _('Travel'), _('Exports'))),
        keywords=(_('tourists'), _('visitors'), _('travel'), _('hotels')),
    ),
)

BY_SLUG = {metric.slug: metric for metric in METRICS}
CATEGORIES = sorted({metric.tags.category for metric in METRICS})
