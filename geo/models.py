"""Country data tables. The ETL modules in providers/ write them; the website only reads them.

Every fact table is named geo_<metric>_country_year and holds one row per country and year.
"""

from django.db import models


class Country(models.Model):
    """The country dimension. Shapes and codes come from Natural Earth; World is an extra aggregate row."""

    iso3 = models.CharField(primary_key=True, max_length=3)
    iso2 = models.CharField(max_length=2, blank=True, help_text='Lower-case code used for the flag file name.')
    name = models.CharField(max_length=100)
    continent = models.CharField(max_length=50, blank=True)
    subregion = models.CharField(max_length=50, blank=True)
    is_aggregate = models.BooleanField(default=False, help_text='True for World, which has no shape on the map.')
    geometry = models.JSONField(null=True, blank=True, help_text='GeoJSON geometry, simplified for a world map.')

    class Meta:
        db_table = 'geo_country'
        ordering = ['name']
        verbose_name_plural = 'countries'

    def __str__(self):
        return self.name


class EtlLoad(models.Model):
    """One row per ETL run: which table was loaded, from where, and when."""

    table_name = models.CharField(max_length=100)
    source_name = models.CharField(max_length=200)
    source_url = models.URLField(max_length=500)
    source_updated = models.CharField(max_length=50, blank=True, help_text="The source's own release or update date.")
    row_count = models.PositiveIntegerField()
    loaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'etl_load'
        ordering = ['-loaded_at']

    def __str__(self):
        return f'{self.table_name} at {self.loaded_at:%Y-%m-%d %H:%M}'


class CountryYear(models.Model):
    """Shared shape of every fact table: one row per country and year."""

    country = models.ForeignKey(Country, on_delete=models.CASCADE, db_column='iso3', related_name='+')
    year = models.PositiveSmallIntegerField()

    class Meta:
        abstract = True
        ordering = ['country', 'year']
        constraints = [
            models.UniqueConstraint(fields=['country', 'year'], name='%(class)s_one_row_per_country_year'),
        ]


class GdpCountryYear(CountryYear):
    value = models.FloatField(help_text='GDP in current US dollars.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_gdp_country_year'


class GdpPerCapitaCountryYear(CountryYear):
    value = models.FloatField(null=True, help_text='GDP per person in current US dollars.')
    ppp = models.FloatField(null=True, help_text='GDP per person in current international dollars (PPP).')

    class Meta(CountryYear.Meta):
        db_table = 'geo_gdp_per_capita_country_year'


class LifeExpectancyCountryYear(CountryYear):
    value = models.FloatField(help_text='Life expectancy at birth, in years.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_life_expectancy_country_year'


class UnemploymentCountryYear(CountryYear):
    value = models.FloatField(help_text='Unemployed people as % of the labour force.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_unemployment_country_year'


class PopulationCountryYear(CountryYear):
    population = models.BigIntegerField(null=True)
    birth_rate = models.FloatField(null=True, help_text='Births per 1,000 people.')
    death_rate = models.FloatField(null=True, help_text='Deaths per 1,000 people.')
    net_migration = models.FloatField(null=True, help_text='Immigrants minus emigrants in the year.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_population_country_year'


class GovernmentDebtCountryYear(CountryYear):
    value = models.FloatField(help_text='General government gross debt as % of GDP.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_government_debt_country_year'


class HdiCountryYear(CountryYear):
    value = models.FloatField(help_text='Human Development Index, 0 to 1.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_hdi_country_year'


class SchoolingCountryYear(CountryYear):
    mean_years = models.FloatField(null=True, help_text='Average years of schooling of adults aged 25 and over.')
    expected_years = models.FloatField(null=True, help_text='Years of schooling a child entering school can expect.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_schooling_country_year'


class DemocracyCountryYear(CountryYear):
    """The five high-level V-Dem democracy indices, each from 0 to 1."""

    electoral = models.FloatField(null=True)
    liberal = models.FloatField(null=True)
    participatory = models.FloatField(null=True)
    deliberative = models.FloatField(null=True)
    egalitarian = models.FloatField(null=True)

    class Meta(CountryYear.Meta):
        db_table = 'geo_democracy_country_year'


class InflationCountryYear(CountryYear):
    value = models.FloatField(help_text='Consumer price inflation, % per year.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_inflation_country_year'


class GdpGrowthCountryYear(CountryYear):
    value = models.FloatField(help_text='Real GDP growth, % per year.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_gdp_growth_country_year'


class FertilityCountryYear(CountryYear):
    value = models.FloatField(help_text='Births per woman (total fertility rate).')

    class Meta(CountryYear.Meta):
        db_table = 'geo_fertility_country_year'


class ChildMortalityCountryYear(CountryYear):
    value = models.FloatField(help_text='Deaths before age 5 per 1,000 live births.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_child_mortality_country_year'


class PovertyCountryYear(CountryYear):
    value = models.FloatField(help_text='% of people living on less than $3.00 a day (2021 PPP).')

    class Meta(CountryYear.Meta):
        db_table = 'geo_poverty_country_year'


class InequalityCountryYear(CountryYear):
    value = models.FloatField(help_text='Gini index, 0 to 100.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_inequality_country_year'


class MilitarySpendingCountryYear(CountryYear):
    value = models.FloatField(help_text='Military expenditure, % of GDP.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_military_spending_country_year'


class HealthSpendingCountryYear(CountryYear):
    value = models.FloatField(help_text='Current health expenditure per person, current US$.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_health_spending_country_year'


class FemaleLabourCountryYear(CountryYear):
    value = models.FloatField(help_text='Women 15+ in the labour force, % of women 15+.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_female_labour_country_year'


class HomicideCountryYear(CountryYear):
    value = models.FloatField(help_text='Intentional homicides per 100,000 people.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_homicide_country_year'


class TaxRevenueCountryYear(CountryYear):
    value = models.FloatField(help_text='Tax revenue, % of GDP.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_tax_revenue_country_year'


class TradeCountryYear(CountryYear):
    value = models.FloatField(help_text='Exports plus imports, % of GDP.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_trade_country_year'


class LifeSatisfactionCountryYear(CountryYear):
    value = models.FloatField(help_text='Self-reported life satisfaction, 0 to 10.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_life_satisfaction_country_year'


class MedianAgeCountryYear(CountryYear):
    value = models.FloatField(help_text='Median age in years (UN estimates, no projections).')

    class Meta(CountryYear.Meta):
        db_table = 'geo_median_age_country_year'


class ObesityCountryYear(CountryYear):
    value = models.FloatField(help_text='% of adults 18+ with a BMI of 30 or more (age-standardised).')

    class Meta(CountryYear.Meta):
        db_table = 'geo_obesity_country_year'


class HumanRightsCountryYear(CountryYear):
    value = models.FloatField(help_text='V-Dem human rights index, 0 to 1.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_human_rights_country_year'


class Co2EmissionsCountryYear(CountryYear):
    """CO2 from fossil fuels and industry, excluding land-use change."""

    per_capita = models.FloatField(null=True, help_text='Tonnes per person.')
    total = models.FloatField(null=True, help_text='Tonnes.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_co2_emissions_country_year'


class ElectricityMixCountryYear(CountryYear):
    """Share of electricity generated by each source, in % of the total."""

    low_carbon = models.FloatField(null=True, help_text='Nuclear plus renewables.')
    coal = models.FloatField(null=True)
    gas = models.FloatField(null=True)
    oil = models.FloatField(null=True)
    nuclear = models.FloatField(null=True)
    hydro = models.FloatField(null=True)
    wind = models.FloatField(null=True)
    solar = models.FloatField(null=True)
    bioenergy = models.FloatField(null=True)
    other_renewables = models.FloatField(null=True, help_text='Renewables other than hydro, wind, solar and bioenergy.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_electricity_mix_country_year'
