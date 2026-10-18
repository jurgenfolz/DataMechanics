"""Every metric page the site publishes. The single source of truth for titles, descriptions, tags and series.

A metric reads one fact table in geo/models.py.
Its source and fetch date come from the table's latest row in etl_load, so the page always cites what was actually loaded.
Visible texts are written in English and translated through locale/ (see CLAUDE.md, Languages).
Slugs, fields and category keys stay English in every language: URLs and code use them.
"""

from dataclasses import dataclass, field

from django.utils import translation
from django.utils.translation import gettext_lazy as _

from geo import models as geo

# Category keys and how each is named on the page.
CATEGORY_LABELS = {
    'Demography': _('Demography'),
    'Development': _('Development'),
    'Economy': _('Economy'),
    'Education': _('Education'),
    'Environment': _('Environment'),
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
        series=(Series('value', _('GDP'), 'usd', log_scale=True),),
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
            Series('value', _('GDP per capita'), 'usd', better='higher', log_scale=True, short=_('Current US$')),
            Series('ppp', _('GDP per capita, PPP (international $)'), 'usd', better='higher', log_scale=True, short=_('PPP')),
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
            Series('electoral', _('Electoral democracy'), 'index', better='higher', short=_('Electoral')),
            Series('liberal', _('Liberal democracy'), 'index', better='higher', short=_('Liberal')),
            Series('participatory', _('Participatory democracy'), 'index', better='higher', short=_('Participatory')),
            Series('deliberative', _('Deliberative democracy'), 'index', better='higher', short=_('Deliberative')),
            Series('egalitarian', _('Egalitarian democracy'), 'index', better='higher', short=_('Egalitarian')),
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
        series=(Series('value', _('Human Development Index'), 'index', better='higher'),),
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
        series=(Series('value', _('Life expectancy at birth'), 'years', better='higher'),),
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
            Series('mean_years', _('Mean years of schooling'), 'years', better='higher', short=_('Mean years')),
            Series('expected_years', _('Expected years of schooling'), 'years', better='higher', short=_('Expected years')),
        ),
        tags=Tags('Education', (_('Schooling'), _('Mean years'), _('Expected years'))),
        keywords=(_('education'), _('school'), _('enrolment'), _('literacy')),
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
            Series('population', _('Population'), 'people', log_scale=True),
            Series('birth_rate', _('Births per 1,000 people'), 'per_1000'),
            Series('death_rate', _('Deaths per 1,000 people'), 'per_1000'),
            Series('net_migration', _('Net migration'), 'people'),
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
        series=(Series('value', _('Unemployment rate'), 'percent', better='lower'),),
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
        series=(Series('value', _('Gross debt, % of GDP'), 'percent', better='lower'),),
        tags=Tags('Economy', (_('Public finance'), _('Government debt'), _('IMF'))),
        keywords=(_('public debt'), _('national debt'), _('deficit'), _('borrowing'), _('debt to gdp')),
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
        series=(Series('value', _('Inflation, consumer prices'), 'percent'),),
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
        series=(Series('value', _('Real GDP growth'), 'percent', better='higher'),),
        tags=Tags('Economy', (_('GDP'), _('Growth'), _('Recession'))),
        keywords=(_('economic growth'), _('real gdp'), _('recession')),
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
        series=(Series('value', _('Tax revenue, % of GDP'), 'percent'),),
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
        series=(Series('value', _('Trade, % of GDP'), 'percent'),),
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
        series=(Series('value', _('Female labour force participation'), 'percent', better='higher'),),
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
        series=(Series('value', _('Births per woman'), 'per_woman'),),
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
        series=(Series('value', _('Median age'), 'years'),),
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
        series=(Series('value', _('Deaths before age 5 per 1,000 live births'), 'per_1000', better='lower'),),
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
        series=(Series('value', _('Adults with obesity'), 'percent', better='lower'),),
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
        series=(Series('value', _('Health spending per person'), 'usd', log_scale=True),),
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
        series=(Series('value', _('Living on under $3.00 a day'), 'percent', better='lower'),),
        tags=Tags('Development', (_('Poverty'), _('Income'))),
        keywords=(_('poor'), _('poverty line'), _('extreme poverty'), _('living on')),
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
        series=(Series('value', _('Gini index'), 'points', better='lower'),),
        tags=Tags('Development', (_('Inequality'), _('Income'), _('Gini'))),
        keywords=(_('gini coefficient'), _('income distribution'), _('inequality')),
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
        series=(Series('value', _('Life satisfaction (0 to 10)'), 'score', better='higher'),),
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
        series=(Series('value', _('Homicides per 100,000 people'), 'per_100k', better='lower', log_scale=True),),
        tags=Tags('Society', (_('Crime'), _('Violence'), _('UNODC'))),
        keywords=(_('murder rate'), _('crime'), _('safety'), _('violence')),
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
        series=(Series('value', _('Human rights index'), 'index', better='higher'),),
        tags=Tags('Governance', (_('Human rights'), _('Civil liberties'), _('V-Dem'))),
        world_label=_('World (average of countries)'),
        keywords=(_('civil liberties'), _('freedom'), _('vdem'), _('repression')),
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
        series=(Series('value', _('Military spending, % of GDP'), 'percent'),),
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
            Series('per_capita', _('CO2 per person'), 'tonnes', better='lower', log_scale=True, short=_('Per person')),
            Series('total', _('Total CO2'), 'tonnes_total', log_scale=True, short=_('Total')),
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
            Series('low_carbon', _('Low-carbon share'), 'percent', better='higher', short=_('Low-carbon')),
            Series('coal', _('Coal share'), 'percent', short=_('Coal')),
            Series('gas', _('Gas share'), 'percent', short=_('Gas')),
            Series('oil', _('Oil share'), 'percent', short=_('Oil')),
            Series('nuclear', _('Nuclear share'), 'percent', short=_('Nuclear')),
            Series('hydro', _('Hydro share'), 'percent', short=_('Hydro')),
            Series('wind', _('Wind share'), 'percent', short=_('Wind')),
            Series('solar', _('Solar share'), 'percent', short=_('Solar')),
            Series('bioenergy', _('Bioenergy share'), 'percent', short=_('Bioenergy')),
            Series('other_renewables', _('Other renewables share'), 'percent', short=_('Other renewables')),
        ),
        tags=Tags('Environment', (_('Energy'), _('Electricity'), _('Renewables'), _('Ember'))),
        keywords=(_('energy mix'), _('renewable energy'), _('solar power'), _('wind power'), _('nuclear power'), _('coal power')),
    ),
)

BY_SLUG = {metric.slug: metric for metric in METRICS}
CATEGORIES = sorted({metric.tags.category for metric in METRICS})
