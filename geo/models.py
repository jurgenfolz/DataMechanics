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
    value = models.FloatField(help_text='GDP per person in current US dollars.')

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
