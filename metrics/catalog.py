"""Every metric page the site publishes. The single source of truth for titles, descriptions, tags and series.

A metric reads one fact table in geo/models.py.
Its source and fetch date come from the table's latest row in etl_load, so the page always cites what was actually loaded.
"""

from dataclasses import dataclass, field

from geo import models as geo


@dataclass(frozen=True)
class Series:
    """One measure of a metric: a column of its fact table."""

    field: str
    label: str
    unit: str  # a key of metrics.formatting.UNITS
    better: str = ''  # 'higher', 'lower' or '' when neither is better
    log_scale: bool = False  # colour the map on a log scale (for very skewed values)
    short: str = ''  # tab label, when the full label is too long for a tab

    @property
    def tab_label(self):
        return self.short or self.label


@dataclass(frozen=True)
class Tags:
    """Search tags, from broad to narrow. See CLAUDE.md, Data design."""

    category: str
    subcategories: tuple[str, ...] = ()  # up to 4
    granularity: tuple[str, ...] = ('Country', 'Year')  # up to 3

    def all(self):
        return [self.category, *self.subcategories, *self.granularity]


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
    world_label: str = 'World'  # how the source's World aggregate is named
    keywords: tuple[str, ...] = field(default=())  # extra search words

    @property
    def table(self):
        return self.model._meta.db_table

    def search_text(self):
        words = [self.title, self.summary, *self.tags.all(), *self.keywords, *(s.label for s in self.series)]
        return ' '.join(words).lower()


METRICS = (
    Metric(
        slug='gdp',
        title='GDP',
        question='Which economies are the largest?',
        summary='The total value of everything a country produces in a year, in US dollars.',
        description=(
            'Gross domestic product (GDP) is the total value of the goods and services produced in a country '
            'in a year. Each country\'s statistics office or central bank measures it from its national accounts, '
            'and the World Bank collects the figures and converts them to US dollars at each year\'s exchange rate. '
            'The values are in current dollars, not adjusted for inflation, so part of the growth over time is '
            'rising prices.'
        ),
        model=geo.GdpCountryYear,
        series=(Series('value', 'GDP', 'usd', log_scale=True),),
        tags=Tags('Economy', ('GDP', 'National accounts')),
        keywords=('gross domestic product', 'economy size', 'output'),
    ),
    Metric(
        slug='gdp-per-capita',
        title='GDP per capita',
        question='Where is output per person highest?',
        summary='GDP divided by population: what a country produces per person.',
        description=(
            'GDP per capita is a country\'s GDP divided by its mid-year population: the value of goods and services '
            'produced per person. It is a common gauge of average living standards, but it says nothing about how '
            'income is shared. The World Bank computes it from national accounts and population estimates, in '
            'current US dollars at market exchange rates. It is not adjusted for inflation or for price differences '
            'between countries.'
        ),
        model=geo.GdpPerCapitaCountryYear,
        series=(Series('value', 'GDP per capita', 'usd', better='higher', log_scale=True),),
        tags=Tags('Economy', ('GDP', 'Per capita', 'Living standards')),
        keywords=('income per person', 'gdp per person', 'wealth'),
    ),
    Metric(
        slug='democracy',
        title='Democracy indices (V-Dem)',
        question='How democratic is each country?',
        summary='Five V-Dem indices that rate how democratic a country is, from 0 to 1.',
        description=(
            'The Varieties of Democracy (V-Dem) project at the University of Gothenburg rates political regimes '
            'with five indices from 0 (least democratic) to 1 (most democratic). Each index captures one idea of '
            'democracy: free and fair elections (electoral), individual rights and limits on power (liberal), '
            'citizens taking part (participatory), decisions based on public reasoning (deliberative) and equal '
            'access to power across social groups (egalitarian). The scores combine the ratings of thousands of '
            'country experts through a statistical model. Our World in Data republishes the central estimates.'
        ),
        model=geo.DemocracyCountryYear,
        series=(
            Series('electoral', 'Electoral democracy', 'index', better='higher', short='Electoral'),
            Series('liberal', 'Liberal democracy', 'index', better='higher', short='Liberal'),
            Series('participatory', 'Participatory democracy', 'index', better='higher', short='Participatory'),
            Series('deliberative', 'Deliberative democracy', 'index', better='higher', short='Deliberative'),
            Series('egalitarian', 'Egalitarian democracy', 'index', better='higher', short='Egalitarian'),
        ),
        tags=Tags('Politics', ('Democracy', 'V-Dem', 'Elections', 'Rights')),
        world_label='World (average of countries)',
        keywords=('vdem', 'varieties of democracy', 'polyarchy', 'freedom', 'regime'),
    ),
    Metric(
        slug='hdi',
        title='Human Development Index',
        question='Where is human development highest?',
        summary='A 0 to 1 score combining health, education and income.',
        description=(
            'The Human Development Index (HDI) sums up three basic dimensions of human development: a long and '
            'healthy life (life expectancy at birth), knowledge (mean and expected years of schooling) and a decent '
            'standard of living (gross national income per person, adjusted for price differences). Each dimension '
            'is scaled from 0 to 1, and the HDI is their geometric mean. The United Nations Development Programme '
            '(UNDP) publishes it every year in its Human Development Report; this data comes from the 2025 report.'
        ),
        model=geo.HdiCountryYear,
        series=(Series('value', 'Human Development Index', 'index', better='higher'),),
        tags=Tags('Development', ('Human development', 'HDI', 'UNDP')),
        keywords=('human development index', 'well-being', 'undp'),
    ),
    Metric(
        slug='life-expectancy',
        title='Life expectancy',
        question='Where do people live longest?',
        summary='How many years a newborn would live if today\'s death rates held for life.',
        description=(
            'Life expectancy at birth is the number of years a newborn would live if the death rates of the year '
            'it was born stayed the same for its whole life. It describes the health of a population in that year; '
            'it is not a forecast for any one person. The World Bank publishes it mainly from the UN Population '
            'Division\'s World Population Prospects, which draws on national statistical offices, censuses and '
            'surveys.'
        ),
        model=geo.LifeExpectancyCountryYear,
        series=(Series('value', 'Life expectancy at birth', 'years', better='higher'),),
        tags=Tags('Health', ('Life expectancy', 'Mortality')),
        keywords=('lifespan', 'longevity', 'age at death'),
    ),
    Metric(
        slug='schooling',
        title='Years of schooling',
        question='How long do people stay in school?',
        summary='Average years adults spent in school, and the years a child can expect today.',
        description=(
            'Mean years of schooling is the average number of years of education completed by people aged 25 and '
            'over. Expected years of schooling is how many years a child starting school can expect to spend in '
            'education if today\'s enrolment rates stay the same. The UNDP uses both in the Human Development Index '
            'and builds them from UNESCO Institute for Statistics data, Barro and Lee estimates and household '
            'surveys.'
        ),
        model=geo.SchoolingCountryYear,
        series=(
            Series('mean_years', 'Mean years of schooling', 'years', better='higher', short='Mean years'),
            Series('expected_years', 'Expected years of schooling', 'years', better='higher', short='Expected years'),
        ),
        tags=Tags('Education', ('Schooling', 'Mean years', 'Expected years')),
        keywords=('education', 'school', 'enrolment', 'literacy'),
    ),
    Metric(
        slug='population',
        title='Population, births and deaths',
        question='Where are populations growing?',
        summary='How many people live in each country, and how many are born and die each year.',
        description=(
            'Population counts everyone who lives in a country at mid-year, whatever their legal status or '
            'citizenship. The birth rate and the death rate are the live births and the deaths in a year per '
            '1,000 people. When births outnumber deaths a population grows naturally; migration changes it too. '
            'The World Bank compiles these figures mainly from the UN Population Division\'s World Population '
            'Prospects, which combines censuses, civil registration and surveys.'
        ),
        model=geo.PopulationCountryYear,
        series=(
            Series('population', 'Population', 'people', log_scale=True),
            Series('birth_rate', 'Births per 1,000 people', 'per_1000'),
            Series('death_rate', 'Deaths per 1,000 people', 'per_1000'),
        ),
        tags=Tags('Demography', ('Population', 'Births', 'Deaths', 'Birth rate')),
        keywords=('people', 'inhabitants', 'fertility', 'mortality', 'death rate', 'demographics'),
    ),
    Metric(
        slug='unemployment',
        title='Unemployment rate',
        question='Where is unemployment highest?',
        summary='The share of the labour force without a job but looking for one.',
        description=(
            'The unemployment rate is the share of the labour force that has no job but is available for and '
            'looking for work. The labour force is everyone of working age who has a job or is looking for one. '
            'These are modelled estimates from the International Labour Organization (ILO), which fills gaps in '
            'national labour force surveys so that countries can be compared. The World Bank republishes them.'
        ),
        model=geo.UnemploymentCountryYear,
        series=(Series('value', 'Unemployment rate', 'percent', better='lower'),),
        tags=Tags('Economy', ('Labour market', 'Unemployment', 'ILO')),
        keywords=('jobs', 'jobless', 'employment', 'labor'),
    ),
    Metric(
        slug='government-debt',
        title='Government debt',
        question='Which governments owe the most?',
        summary='Everything a country\'s governments owe, as a share of its GDP.',
        description=(
            'General government gross debt is everything a country\'s governments owe: central, state and local '
            'government and social security funds together. It covers loans, bonds and other liabilities that must '
            'be repaid with interest, and is shown as a share of GDP so that countries of different sizes can be '
            'compared. The International Monetary Fund (IMF) publishes it in its World Economic Outlook. We show '
            'past years only and leave out the IMF\'s forecasts; the latest year can still be an IMF estimate.'
        ),
        model=geo.GovernmentDebtCountryYear,
        series=(Series('value', 'Gross debt, % of GDP', 'percent', better='lower'),),
        tags=Tags('Economy', ('Public finance', 'Government debt', 'IMF')),
        keywords=('public debt', 'national debt', 'deficit', 'borrowing', 'debt to gdp'),
    ),
)

BY_SLUG = {metric.slug: metric for metric in METRICS}
CATEGORIES = sorted({metric.tags.category for metric in METRICS})
