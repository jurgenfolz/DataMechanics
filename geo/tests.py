"""ETL tests. Network calls are replaced with small samples shaped like each source's real response."""

from datetime import date
from unittest import mock

from django.test import TestCase

from geo.models import Country, EtlLoad, GdpCountryYear, GovernmentDebtCountryYear, SchoolingCountryYear
from providers import geometry, load
from providers.imf import government_debt
from providers.naturalearth import countries
from providers.undp import composite_indices, schooling
from providers.worldbank import api as worldbank


def make_countries(*codes):
    for code in codes:
        Country.objects.create(iso3=code, iso2=code[:2].lower(), name=code, is_aggregate=code == 'WLD')


class ReplaceTableTests(TestCase):
    def setUp(self):
        make_countries('DEU', 'XKX', 'WLD')

    def test_aliases_unknown_codes_and_load_log(self):
        rows = {('DEU', 2020): {'value': 1.0}, ('KOS', 2020): {'value': 2.0}, ('EUU', 2020): {'value': 3.0}}
        result = load.replace_table(GdpCountryYear, rows, load.Source('Test source', 'https://example.org', 'v1'))
        self.assertEqual(result.rows, 2)
        self.assertEqual(result.skipped_codes, ['EUU'])
        self.assertEqual(GdpCountryYear.objects.get(country_id='XKX').value, 2.0)
        self.assertEqual(EtlLoad.objects.get().row_count, 2)

    def test_replaces_old_rows(self):
        source = load.Source('Test source', 'https://example.org')
        load.replace_table(GdpCountryYear, {('DEU', 2019): {'value': 1.0}}, source)
        load.replace_table(GdpCountryYear, {('DEU', 2020): {'value': 2.0}}, source)
        self.assertEqual(list(GdpCountryYear.objects.values_list('year', flat=True)), [2020])


class WorldBankTests(TestCase):
    def test_fetch_indicator_skips_missing_values(self):
        response = [
            {'page': 1, 'pages': 1, 'lastupdated': '2026-10-08'},
            [
                {'countryiso3code': 'DEU', 'date': '2025', 'value': 5.0},
                {'countryiso3code': 'DEU', 'date': '2024', 'value': None},
                {'countryiso3code': '', 'date': '2025', 'value': 9.0},
            ],
        ]
        with mock.patch('providers.http.get_json', return_value=response):
            values, updated = worldbank.fetch_indicator('NY.GDP.MKTP.CD')
        self.assertEqual(values, {('DEU', 2025): 5.0})
        self.assertEqual(updated, '2026-10-08')

    def test_refuses_a_second_page(self):
        with mock.patch('providers.http.get_json', return_value=[{'pages': 2}, []]):
            with self.assertRaises(ValueError):
                worldbank.fetch_indicator('NY.GDP.MKTP.CD')


class ImfTests(TestCase):
    def test_drops_projection_years(self):
        make_countries('JPN')
        this_year = date.today().year
        values = {'values': {'GGXWDG_NGDP': {'JPN': {str(this_year - 1): 230.0, str(this_year): 232.0}}}}
        meta = {'indicators': {'GGXWDG_NGDP': {'source': 'World Economic Outlook (October 2026)'}}}
        with mock.patch('providers.http.get_json', side_effect=[values, meta]):
            government_debt.run()
        self.assertEqual(list(GovernmentDebtCountryYear.objects.values_list('year', flat=True)), [this_year - 1])
        self.assertEqual(EtlLoad.objects.get().source_name, 'IMF, World Economic Outlook (October 2026)')


class UndpTests(TestCase):
    CSV = 'iso3,country,mys_2022,mys_2023,eys_2023,hdi_2023\nNOR,Norway,13.1,13.2,18.8,0.970\nZZK.WORLD,World,,8.8,12.8,0.756\n'

    def test_reads_wide_columns_into_rows(self):
        with mock.patch('providers.http.get_text', return_value=self.CSV):
            rows = composite_indices.read_columns(['mys', 'eys'])
        self.assertEqual(rows[('NOR', 2023)], {'mys': 13.2, 'eys': 18.8})
        self.assertEqual(rows[('NOR', 2022)], {'mys': 13.1, 'eys': None})

    def test_schooling_maps_world_alias(self):
        make_countries('NOR', 'WLD')
        with mock.patch('providers.http.get_text', return_value=self.CSV):
            schooling.run()
        self.assertEqual(SchoolingCountryYear.objects.get(country_id='WLD', year=2023).mean_years, 8.8)


class NaturalEarthTests(TestCase):
    def test_straight_lines_lose_their_middle_points(self):
        line = [[0, 0], [1, 0.001], [2, 0], [2, 2], [0, 0]]
        self.assertEqual(geometry.douglas_peucker(line, 0.05), [[0, 0], [2, 0], [2, 2], [0, 0]])

    def test_tiny_countries_keep_a_shape(self):
        islet = {'type': 'Polygon', 'coordinates': [[[0, 0], [0.001, 0], [0.001, 0.001], [0, 0]]]}
        self.assertEqual(len(geometry.simplify(islet, 0.05, 2)['coordinates']), 1)

    def test_names_and_codes(self):
        feature = {
            'properties': {'ISO_A3_EH': '-99', 'ADM0_A3': 'KOS', 'ISO_A2_EH': 'XK', 'NAME': 'Kosovo',
                           'NAME_LONG': 'Kosovo', 'CONTINENT': 'Europe', 'SUBREGION': 'Southern Europe'},
            'geometry': {'type': 'Polygon', 'coordinates': [[[20, 42], [21, 42], [21, 43], [20, 42]]]},
        }
        country = countries._country(feature, own_codes={'KOS'})
        self.assertEqual((country.iso3, country.iso2, country.name), ('XKX', 'xk', 'Kosovo'))

    def test_territories_never_take_their_countrys_code(self):
        territory = {
            'properties': {'ISO_A3_EH': 'AUS', 'ADM0_A3': 'ATC', 'ISO_A2_EH': 'AU', 'NAME': 'Ashmore and Cartier Is.',
                           'NAME_LONG': 'Ashmore and Cartier Islands', 'CONTINENT': 'Oceania', 'SUBREGION': 'Australia and New Zealand'},
            'geometry': {'type': 'Polygon', 'coordinates': [[[123, -12], [123.1, -12], [123.1, -12.1], [123, -12]]]},
        }
        self.assertEqual(countries._country(territory, own_codes={'AUS', 'ATC'}).iso3, 'ATC')


class OwidTests(TestCase):
    CSV = 'entity,code,year,emissions_total_per_capita\nNorway,NOR,2024,7.5\nAsia,,2024,4.1\nWorld,OWID_WRL,2024,4.7\nNorway,NOR,2023,\n'

    def test_reads_columns_skips_regions_and_blanks(self):
        from providers.owid import grapher
        with mock.patch('providers.http.get_text', return_value=self.CSV):
            rows = grapher.read_chart('co-emissions-per-capita', {'emissions_total_per_capita': 'per_capita'})
        self.assertEqual(rows, {('NOR', 2024): {'per_capita': 7.5}, ('OWID_WRL', 2024): {'per_capita': 4.7}})
