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
    total: bool = False  # the values add up across countries (GDP, population): a group's value is its members' sum

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
        title=_('Life expectancy'),
        question=_('Where do people live longest?'),
        summary=_('How many years a newborn would live if today\'s death rates held for life.'),
        description=(
            _('Life expectancy at birth is the number of years a newborn would live if the death rates of the year '
            'it was born stayed the same for its whole life. It describes the health of a population in that year; '
            'it is not a forecast for any one person. The World Bank publishes it mainly from the UN Population '
            'Division\'s World Population Prospects, which draws on national statistical offices, censuses and '
            'surveys.')
        ),
        model=geo.LifeExpectancyCountryYear,
        series=(Series('value', _('Life expectancy at birth'), 'years', measured_in=pgettext_lazy('measured in', 'years'), better='higher'),),
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
        title=_('Child mortality'),
        question=_('Where do most children die before age five?'),
        summary=_('Deaths before age five, per 1,000 live births.'),
        description=(
            _('The under-five mortality rate is the probability that a newborn baby dies before turning five, per '
            '1,000 live births, if the death rates of that year held. The UN Inter-agency Group for Child Mortality '
            'Estimation (UNICEF, the WHO, the World Bank and the UN Population Division) produces the estimates from '
            'surveys, censuses and vital registration, and the World Bank republishes them.')
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
        title=_('Undernourished people'),
        question=_('Where do the most people go hungry?'),
        summary=_('People whose food does not give them the minimum energy they need.'),
        description=(
            _('This counts the people whose usual diet does not give them enough calories to meet their minimum energy '
            'needs. The Food and Agriculture Organization of the United Nations (FAO) estimates it for each country from '
            'national food and population data, and Our World in Data republishes it. Big countries have more '
            'undernourished people partly because they have more people, so compare countries of a similar size, or '
            'follow one country over time.')
        ),
        model=geo.UndernourishmentCountryYear,
        series=(Series('value', _('Undernourished people'), 'people', measured_in=pgettext_lazy('measured in', 'people'), log_scale=True, total=True),),
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
)

BY_SLUG = {metric.slug: metric for metric in METRICS}
CATEGORIES = sorted({metric.tags.category for metric in METRICS})
