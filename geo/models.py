"""Country data tables. The ETL modules in providers/ write them; the website only reads them.

Every fact table is named geo_<metric>_country_year and holds one row per country and year.
"""

from django.db import models
from django.utils import translation


class Country(models.Model):
    """The country dimension. Shapes and codes come from Natural Earth; World is an extra aggregate row."""

    iso3 = models.CharField(primary_key=True, max_length=3)
    iso2 = models.CharField(max_length=2, blank=True, help_text='Lower-case code used for the flag file name.')
    name = models.CharField(max_length=100, help_text='English name. URLs, downloads and sorting use it.')
    name_de = models.CharField(max_length=100, blank=True)
    name_pt = models.CharField(max_length=100, blank=True)
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

    @property
    def local_name(self):
        """The name in the active language, or the English name where there is no translation."""
        return getattr(self, f'name_{translation.get_language()}', '') or self.name


class State(models.Model):
    """A country's states, Länder or provinces, from Natural Earth: only the countries whose data the site maps by state."""

    code = models.CharField(primary_key=True, max_length=6, help_text='ISO 3166-2, e.g. DE-BY or BR-SP.')
    country = models.ForeignKey(Country, on_delete=models.CASCADE, db_column='iso3', related_name='states')
    name = models.CharField(max_length=100, help_text='English name.')
    name_de = models.CharField(max_length=100, blank=True)
    name_pt = models.CharField(max_length=100, blank=True)
    geometry = models.JSONField(help_text='GeoJSON geometry, simplified for a map of the country.')

    class Meta:
        db_table = 'geo_state'
        ordering = ['code']

    def __str__(self):
        return self.name

    @property
    def local_name(self):
        """The name in the active language, or the English name where there is no translation."""
        return getattr(self, f'name_{translation.get_language()}', '') or self.name


def table_name(model):
    """The name etl_load gives a model's table: "ww2.battle" for a table in a schema, else the table's own name."""
    return model._meta.db_table.replace('"."', '.')


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
    women = models.FloatField(null=True, help_text='Life expectancy at birth of women, in years.')
    men = models.FloatField(null=True, help_text='Life expectancy at birth of men, in years.')

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


class InterestPaymentsCountryYear(CountryYear):
    value = models.FloatField(help_text='Interest paid on government debt, % of government revenue.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_interest_payments_country_year'


class BudgetBalanceCountryYear(CountryYear):
    value = models.FloatField(help_text='General government net lending (+) or borrowing (-), % of GDP.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_budget_balance_country_year'


class PrimaryBalanceCountryYear(CountryYear):
    value = models.FloatField(help_text='General government balance before interest, % of GDP.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_primary_balance_country_year'


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


class PoliticalCorruptionCountryYear(CountryYear):
    value = models.FloatField(help_text='V-Dem political corruption index, 0 (least corrupt) to 1 (most corrupt).')

    class Meta(CountryYear.Meta):
        db_table = 'geo_political_corruption_country_year'


class ExecutiveCorruptionCountryYear(CountryYear):
    value = models.FloatField(help_text='V-Dem executive corruption index, 0 (least corrupt) to 1 (most corrupt).')

    class Meta(CountryYear.Meta):
        db_table = 'geo_executive_corruption_country_year'


class PublicSectorCorruptionCountryYear(CountryYear):
    value = models.FloatField(help_text='V-Dem public sector corruption index, 0 (least corrupt) to 1 (most corrupt).')

    class Meta(CountryYear.Meta):
        db_table = 'geo_public_sector_corruption_country_year'


class JudicialCorruptionCountryYear(CountryYear):
    value = models.FloatField(help_text='V-Dem judicial corruption score: higher is less corrupt, 0 is about the average.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_judicial_corruption_country_year'


class CorruptionPerceptionsCountryYear(CountryYear):
    value = models.FloatField(help_text='Transparency International CPI, 0 (very corrupt) to 100 (very clean).')

    class Meta(CountryYear.Meta):
        db_table = 'geo_corruption_perceptions_country_year'


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


class LiteracyCountryYear(CountryYear):
    value = models.FloatField(help_text='Share of people aged 15 and older who can read and write, %.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_literacy_country_year'


class EducationSpendingCountryYear(CountryYear):
    value = models.FloatField(help_text='General government spending on education, % of GDP.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_education_spending_country_year'


class ScientificArticlesCountryYear(CountryYear):
    value = models.FloatField(help_text='Articles in science and engineering journals and proceedings, per year.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_scientific_articles_country_year'


class GenderWageGapCountryYear(CountryYear):
    value = models.FloatField(help_text="Men's minus women's average hourly earnings, % of men's (unadjusted).")

    class Meta(CountryYear.Meta):
        db_table = 'geo_gender_wage_gap_country_year'


class WomenPoliticalEmpowermentCountryYear(CountryYear):
    value = models.FloatField(help_text="V-Dem women's political empowerment index, 0 to 1.")

    class Meta(CountryYear.Meta):
        db_table = 'geo_women_political_empowerment_country_year'


class WomenInParliamentCountryYear(CountryYear):
    value = models.FloatField(help_text='Share of seats in the lower or only chamber held by women, %.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_women_in_parliament_country_year'


class UndernourishmentCountryYear(CountryYear):
    value = models.FloatField(help_text='% of people whose food intake is below their minimum energy needs (FAO); 2.5 means 2.5 or less.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_undernourishment_country_year'


class HealthyDietUnaffordableCountryYear(CountryYear):
    value = models.FloatField(help_text='Share of people who cannot afford the cheapest healthy diet, %.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_healthy_diet_unaffordable_country_year'


class MeatProductionCountryYear(CountryYear):
    value = models.FloatField(help_text='Meat produced in a year, tonnes (FAO).')

    class Meta(CountryYear.Meta):
        db_table = 'geo_meat_production_country_year'


class AirPollutionCountryYear(CountryYear):
    pm25 = models.FloatField(null=True, help_text='Mean annual exposure to PM2.5, micrograms per cubic metre.')
    above_guideline = models.FloatField(null=True, help_text='Share of people exposed to PM2.5 above 10 µg/m³, %.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_air_pollution_country_year'


class TopIncomeShareCountryYear(CountryYear):
    value = models.FloatField(help_text='Share of income going to the richest 1%, before taxes and benefits, %.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_top_income_share_country_year'


class MeanIncomeCountryYear(CountryYear):
    value = models.FloatField(help_text='Mean income or consumption per person per day, international-$ at 2021 prices.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_mean_income_country_year'


class LabourProductivityCountryYear(CountryYear):
    value = models.FloatField(help_text='GDP per hour worked, international-$ at 2021 prices.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_labour_productivity_country_year'


class GovernmentSpendingCountryYear(CountryYear):
    value = models.FloatField(help_text='Government expenditure, including interest, % of GDP.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_government_spending_country_year'


class YouthUnemploymentCountryYear(CountryYear):
    value = models.FloatField(help_text='% of the labour force aged 15 to 24 without a job and looking for one (ILO modelled estimate).')

    class Meta(CountryYear.Meta):
        db_table = 'geo_youth_unemployment_country_year'


class FdiInflowsCountryYear(CountryYear):
    value = models.FloatField(help_text='Net inflows of foreign direct investment, % of GDP.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_fdi_inflows_country_year'


class CurrentAccountCountryYear(CountryYear):
    value = models.FloatField(help_text='Current account balance, % of GDP.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_current_account_country_year'


class PrivateDebtCountryYear(CountryYear):
    total = models.FloatField(null=True, help_text='Debt of households and non-financial firms, loans and debt securities, % of GDP.')
    households = models.FloatField(null=True, help_text='Household debt, loans and debt securities, % of GDP.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_private_debt_country_year'


class SavingsInvestmentCountryYear(CountryYear):
    investment = models.FloatField(null=True, help_text='Gross capital formation, % of GDP.')
    savings = models.FloatField(null=True, help_text='Gross savings, % of GDP.')
    fixed = models.FloatField(null=True, help_text='Gross fixed capital formation, % of GDP.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_savings_and_investment_country_year'


class RemittancesCountryYear(CountryYear):
    value = models.FloatField(help_text='Personal remittances received, % of GDP.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_remittances_country_year'


class EmploymentRateCountryYear(CountryYear):
    employed = models.FloatField(null=True, help_text='% of people aged 15 and over who have a job (ILO modelled estimate).')
    in_labour_force = models.FloatField(null=True, help_text='% of people aged 15 and over who have a job or look for one (ILO modelled estimate).')

    class Meta(CountryYear.Meta):
        db_table = 'geo_employment_rate_country_year'


class VulnerableEmploymentCountryYear(CountryYear):
    value = models.FloatField(help_text='% of employed people who work on their own account or in a family business (ILO modelled estimate).')

    class Meta(CountryYear.Meta):
        db_table = 'geo_vulnerable_employment_country_year'


class EconomicStructureCountryYear(CountryYear):
    agriculture = models.FloatField(null=True, help_text='Agriculture, forestry and fishing, value added, % of GDP.')
    industry = models.FloatField(null=True, help_text='Industry including construction, value added, % of GDP.')
    services = models.FloatField(null=True, help_text='Services, value added, % of GDP.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_economic_structure_country_year'


class ForeignReservesCountryYear(CountryYear):
    value = models.FloatField(help_text='Total reserves, in months of imports they could pay for.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_foreign_reserves_country_year'


class RdSpendingCountryYear(CountryYear):
    value = models.FloatField(help_text='Spending on research and development, % of GDP.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_rd_spending_country_year'


class InternetUsersCountryYear(CountryYear):
    internet = models.FloatField(null=True, help_text='% of people who used the internet in the last three months.')
    mobile = models.FloatField(null=True, help_text='Mobile phone subscriptions per 100 people.')
    broadband = models.FloatField(null=True, help_text='Fixed broadband subscriptions per 100 people.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_internet_users_country_year'


class ElectricityAccessCountryYear(CountryYear):
    value = models.FloatField(help_text='% of people with access to electricity.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_electricity_access_country_year'


class InfantMortalityCountryYear(CountryYear):
    value = models.FloatField(help_text='Deaths before age 1 per 1,000 live births.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_infant_mortality_country_year'


class AdolescentFertilityCountryYear(CountryYear):
    value = models.FloatField(help_text='Births per 1,000 women aged 15 to 19.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_adolescent_fertility_country_year'


class MaternalMortalityCountryYear(CountryYear):
    value = models.FloatField(help_text='Maternal deaths per 100,000 live births (modelled estimate).')

    class Meta(CountryYear.Meta):
        db_table = 'geo_maternal_mortality_country_year'


class ImmunisationCountryYear(CountryYear):
    measles = models.FloatField(null=True, help_text='% of children aged 12 to 23 months vaccinated against measles.')
    dtp = models.FloatField(null=True, help_text='% of children aged 12 to 23 months vaccinated against diphtheria, tetanus and pertussis.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_immunisation_country_year'


class SuicideRateCountryYear(CountryYear):
    value = models.FloatField(help_text='Suicides per 100,000 people.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_suicide_rate_country_year'


class TuberculosisCountryYear(CountryYear):
    value = models.FloatField(help_text='New and relapse tuberculosis cases per 100,000 people.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_tuberculosis_country_year'


class HivPrevalenceCountryYear(CountryYear):
    value = models.FloatField(help_text='% of people aged 15 to 49 living with HIV.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_hiv_prevalence_country_year'


class OutOfPocketHealthCountryYear(CountryYear):
    value = models.FloatField(help_text='Out-of-pocket payments, % of current health spending.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_out_of_pocket_health_country_year'


class AlcoholConsumptionCountryYear(CountryYear):
    value = models.FloatField(help_text='Litres of pure alcohol per person aged 15 and over in a year.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_alcohol_consumption_country_year'


class RoadDeathsCountryYear(CountryYear):
    value = models.FloatField(help_text='Deaths from road traffic injuries per 100,000 people.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_road_deaths_country_year'


class DoctorsBedsCountryYear(CountryYear):
    physicians = models.FloatField(null=True, help_text='Physicians per 1,000 people.')
    beds = models.FloatField(null=True, help_text='Hospital beds per 1,000 people.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_doctors_and_beds_country_year'


class WaterSanitationCountryYear(CountryYear):
    water_safe = models.FloatField(null=True, help_text='% of people using safely managed drinking water.')
    water_basic = models.FloatField(null=True, help_text='% of people using at least basic drinking water.')
    sanitation_safe = models.FloatField(null=True, help_text='% of people using safely managed sanitation.')
    sanitation_basic = models.FloatField(null=True, help_text='% of people using at least basic sanitation.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_water_and_sanitation_country_year'


class ChildStuntingCountryYear(CountryYear):
    value = models.FloatField(help_text='% of children under 5 who are too short for their age (modelled estimate).')

    class Meta(CountryYear.Meta):
        db_table = 'geo_child_stunting_country_year'


class UrbanPopulationCountryYear(CountryYear):
    value = models.FloatField(help_text='% of people living in urban areas.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_urban_population_country_year'


class AgeDependencyCountryYear(CountryYear):
    total = models.FloatField(null=True, help_text='People under 15 and over 64 per 100 people aged 15 to 64.')
    old = models.FloatField(null=True, help_text='People over 64 per 100 people aged 15 to 64.')
    over_65 = models.FloatField(null=True, help_text='% of people aged 65 and over.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_age_dependency_country_year'


class RefugeesCountryYear(CountryYear):
    from_country = models.FloatField(null=True, help_text='Refugees from this country, under the UNHCR mandate.')
    in_country = models.FloatField(null=True, help_text='Refugees hosted by this country, under the UNHCR mandate.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_refugees_country_year'


class SchoolEnrolmentCountryYear(CountryYear):
    secondary = models.FloatField(null=True, help_text='Pupils in secondary education, % of the age group (gross, can exceed 100).')
    tertiary = models.FloatField(null=True, help_text='Students in tertiary education, % of the age group (gross, can exceed 100).')

    class Meta(CountryYear.Meta):
        db_table = 'geo_school_enrolment_country_year'


class GreenhouseGasCountryYear(CountryYear):
    per_capita = models.FloatField(null=True, help_text='Tonnes of CO2 equivalent per person.')
    total = models.FloatField(null=True, help_text='Tonnes of CO2 equivalent (the World Bank gives megatonnes; the loader multiplies by a million).')

    class Meta(CountryYear.Meta):
        db_table = 'geo_greenhouse_gas_emissions_country_year'


class TemperatureAnomalyCountryYear(CountryYear):
    value = models.FloatField(help_text='Difference from the 1991 to 2020 average temperature, °C.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_temperature_anomaly_country_year'


class ForestAreaCountryYear(CountryYear):
    value = models.FloatField(help_text='Forest, % of the land area.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_forest_area_country_year'


class EnergyUseCountryYear(CountryYear):
    value = models.FloatField(help_text='Primary energy use, kg of oil equivalent per person.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_energy_use_country_year'


class RenewableEnergyCountryYear(CountryYear):
    value = models.FloatField(help_text='Renewable energy, % of total final energy consumption.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_renewable_energy_country_year'


class ElectricityConsumptionCountryYear(CountryYear):
    value = models.FloatField(help_text='Electric power consumption, kWh per person.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_electricity_consumption_country_year'


class ConsumptionCo2CountryYear(CountryYear):
    value = models.FloatField(help_text='CO2 caused by what the country consumes, tonnes per person.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_consumption_co2_country_year'


class WaterStressCountryYear(CountryYear):
    value = models.FloatField(help_text='Freshwater withdrawn, % of the renewable freshwater available.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_water_stress_country_year'


class GovernanceIndicatorsCountryYear(CountryYear):
    rule_of_law = models.FloatField(null=True, help_text='Rule of law, about -2.5 to 2.5.')
    effectiveness = models.FloatField(null=True, help_text='Government effectiveness, about -2.5 to 2.5.')
    regulation = models.FloatField(null=True, help_text='Regulatory quality, about -2.5 to 2.5.')
    voice = models.FloatField(null=True, help_text='Voice and accountability, about -2.5 to 2.5.')
    stability = models.FloatField(null=True, help_text='Political stability and absence of violence, about -2.5 to 2.5.')
    corruption = models.FloatField(null=True, help_text='Control of corruption, about -2.5 to 2.5.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_governance_indicators_country_year'


class RuleOfLawCountryYear(CountryYear):
    value = models.FloatField(help_text='V-Dem rule of law index, 0 to 1.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_rule_of_law_country_year'


class FreedomOfExpressionCountryYear(CountryYear):
    value = models.FloatField(help_text='V-Dem freedom of expression and alternative sources of information index, 0 to 1.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_freedom_of_expression_country_year'


class ConflictDeathsCountryYear(CountryYear):
    value = models.FloatField(help_text='Deaths in armed conflicts in the country that year, best estimate.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_conflict_deaths_country_year'


class LgbtRightsCountryYear(CountryYear):
    value = models.FloatField(help_text='LGBT+ Policy Index: laws that protect minus laws that discriminate, in points.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_lgbt_rights_country_year'


class WorkingHoursCountryYear(CountryYear):
    value = models.FloatField(help_text='Hours worked per worker in a year.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_working_hours_country_year'


class ArmsImportsCountryYear(CountryYear):
    value = models.FloatField(help_text='Arms imports in SIPRI trend-indicator values, constant 1990 US dollars.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_arms_imports_country_year'


class MinimumWageCountryYear(CountryYear):
    ppp = models.FloatField(null=True, help_text='Statutory monthly minimum wage, in 2021 PPP dollars.')
    usd = models.FloatField(null=True, help_text='Statutory monthly minimum wage, in US dollars.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_minimum_wage_country_year'


class MaddisonGdpPerCapitaCountryYear(CountryYear):
    value = models.FloatField(help_text='GDP per person, international dollars of 2011 (Maddison Project).')

    class Meta(CountryYear.Meta):
        db_table = 'geo_maddison_gdp_per_capita_country_year'


class VoterTurnoutCountryYear(CountryYear):
    value = models.FloatField(help_text='Voters as % of registered voters, in a national election.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_voter_turnout_country_year'


class SchoolingLongRunCountryYear(CountryYear):
    value = models.FloatField(help_text='Average years of schooling of people aged 15 to 64.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_schooling_long_run_country_year'


class CalorieSupplyCountryYear(CountryYear):
    value = models.FloatField(help_text='Food supply per person, kilocalories a day.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_calorie_supply_country_year'


class TotalFactorProductivityCountryYear(CountryYear):
    value = models.FloatField(help_text='Total factor productivity at constant national prices, 2017 = 1.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_total_factor_productivity_country_year'


class FossilFuelProductionCountryYear(CountryYear):
    oil = models.FloatField(null=True, help_text='Oil production, terawatt-hours.')
    coal = models.FloatField(null=True, help_text='Coal production, terawatt-hours.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_fossil_fuel_production_country_year'


class NetMigrationCountryYear(CountryYear):
    value = models.FloatField(help_text='Immigrants minus emigrants, people.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_net_migration_country_year'


class BirthDeathRatesCountryYear(CountryYear):
    births = models.FloatField(null=True, help_text='Births per 1,000 people.')
    deaths = models.FloatField(null=True, help_text='Deaths per 1,000 people.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_birth_death_rates_country_year'


class PopulationGrowthCountryYear(CountryYear):
    value = models.FloatField(help_text='Population growth, % a year.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_population_growth_country_year'


class GniPerCapitaCountryYear(CountryYear):
    value = models.FloatField(help_text='GNI per person, current US dollars, Atlas method.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_gni_per_capita_country_year'


class HouseholdConsumptionCountryYear(CountryYear):
    value = models.FloatField(help_text='Household consumption, % of GDP.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_household_consumption_country_year'


class ExchangeRateCountryYear(CountryYear):
    value = models.FloatField(help_text='Local currency units per US dollar, yearly average.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_exchange_rate_country_year'


class ExportStructureCountryYear(CountryYear):
    fuel = models.FloatField(null=True, help_text='Fuel exports, % of merchandise exports.')
    manufactures = models.FloatField(null=True, help_text='Manufactured exports, % of merchandise exports.')
    food = models.FloatField(null=True, help_text='Food exports, % of merchandise exports.')
    agriculture = models.FloatField(null=True, help_text='Agricultural raw materials, % of merchandise exports.')
    metals = models.FloatField(null=True, help_text='Ores and metals, % of merchandise exports.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_export_structure_country_year'


class CerealYieldCountryYear(CountryYear):
    value = models.FloatField(help_text='Cereal yield, kilograms per hectare.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_cereal_yield_country_year'


class FoodProductionCountryYear(CountryYear):
    value = models.FloatField(help_text='Food production index, 2014 to 2016 = 100.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_food_production_country_year'


class LandUseCountryYear(CountryYear):
    agricultural = models.FloatField(null=True, help_text='Agricultural land, % of land area.')
    arable_per_person = models.FloatField(null=True, help_text='Arable land, hectares per person.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_land_use_country_year'


class TelephonesCountryYear(CountryYear):
    fixed = models.FloatField(null=True, help_text='Fixed telephone lines per 100 people.')
    mobile = models.FloatField(null=True, help_text='Mobile subscriptions per 100 people.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_telephones_country_year'


class AirPassengersCountryYear(CountryYear):
    value = models.FloatField(help_text="Passengers carried by the country's airlines.")

    class Meta(CountryYear.Meta):
        db_table = 'geo_air_passengers_country_year'


class AdultMortalityCountryYear(CountryYear):
    men = models.FloatField(null=True, help_text='Men dying between 15 and 60, per 1,000.')
    women = models.FloatField(null=True, help_text='Women dying between 15 and 60, per 1,000.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_adult_mortality_country_year'


class TerrorismDeathsCountryYear(CountryYear):
    value = models.FloatField(help_text='People killed in terrorist attacks.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_terrorism_deaths_country_year'


class LabourForceParticipationCountryYear(CountryYear):
    value = models.FloatField(help_text='People in the labour force, % of those aged 15 and over.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_labour_force_participation_country_year'


class EmploymentBySectorCountryYear(CountryYear):
    agriculture = models.FloatField(null=True, help_text='Employment in agriculture, % of all employment.')
    industry = models.FloatField(null=True, help_text='Employment in industry, %.')
    services = models.FloatField(null=True, help_text='Employment in services, %.')
    self_employed = models.FloatField(null=True, help_text='Self-employed, % of all employment.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_employment_by_sector_country_year'


class YouthNeetCountryYear(CountryYear):
    value = models.FloatField(help_text='Youth not in employment, education or training, % of those aged 15 to 24.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_youth_neet_country_year'


class PatentsCountryYear(CountryYear):
    residents = models.FloatField(null=True, help_text='Patent applications by residents.')
    non_residents = models.FloatField(null=True, help_text='Patent applications by non-residents.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_patents_country_year'


class MarketCapCountryYear(CountryYear):
    value = models.FloatField(help_text='Market capitalisation of listed domestic companies, % of GDP.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_market_cap_country_year'


class PrisonPopulationCountryYear(CountryYear):
    value = models.FloatField(help_text='Prisoners per 100,000 people.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_prison_population_country_year'


class ArmedForcesCountryYear(CountryYear):
    value = models.FloatField(help_text='Armed forces personnel per 1,000 people.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_armed_forces_country_year'


class PisaCountryYear(CountryYear):
    maths = models.FloatField(null=True, help_text='PISA mean score in mathematics.')
    reading = models.FloatField(null=True, help_text='PISA mean score in reading.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_pisa_country_year'


class SmokingCountryYear(CountryYear):
    total = models.FloatField(null=True, help_text='People aged 15 and over who use tobacco, %.')
    men = models.FloatField(null=True, help_text='Men who use tobacco, %.')
    women = models.FloatField(null=True, help_text='Women who use tobacco, %.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_smoking_country_year'


class TourismCountryYear(CountryYear):
    arrivals = models.FloatField(null=True, help_text='International tourist arrivals.')
    receipts = models.FloatField(null=True, help_text='International tourism receipts, % of total exports.')

    class Meta(CountryYear.Meta):
        db_table = 'geo_tourism_country_year'
