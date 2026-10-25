import csv
import re
import tempfile
from datetime import date
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from geo.models import (Country, EtlLoad, GdpCountryYear, GdpPerCapitaCountryYear, InflationCountryYear,
                        UnemploymentCountryYear)
from metrics.catalog import BY_SLUG
from providers.curated import COUNTRIES, DATA, administrations, parties, party_left_right, party_positions, party_profiles
from providers.tse import elected as tse_elected

from . import compass, comparison, queries, spectrum
from .metrics import GROUPS
from .offices import ROLES
from .models import Administration, Deputy, Elected, Party, Senator

GDP = BY_SLUG['gdp-per-capita']
UNEMPLOYMENT = BY_SLUG['unemployment']


def make_brazil():
    """Three presidencies, the middle one changing party halfway, and one leader serving twice in a row."""
    brazil = Country.objects.create(iso3='BRA', iso2='br', name='Brazil')
    red = Party.objects.create(country=brazil, abbreviation='RED', name='Red Party', color='#e30d33', logo='politics/brazil/red.svg')
    blue = Party.objects.create(country=brazil, abbreviation='BLU', name='Blue Party', color='#0080ff')
    rows = [
        ('Ana Souza', 'Souza', red, '2003-01-01', '2007-01-01'),
        ('Ana Souza', 'Souza', red, '2007-01-01', '2011-01-01'),
        ('Bruno Lima', 'Lima', blue, '2011-01-01', '2013-03-01'),
        ('Bruno Lima', 'Lima', None, '2013-03-01', '2015-01-01'),
        ('Carla Dias', 'Dias', red, '2015-01-01', ''),
    ]
    for leader, short, party, start, end in rows:
        Administration.objects.create(country=brazil, leader=leader, short_name=short, role='President', party=party,
                                      start_date=date.fromisoformat(start),
                                      end_date=date.fromisoformat(end) if end else None)
    return brazil


class OwnedYearsTests(TestCase):
    def test_a_year_belongs_to_whoever_is_in_office_on_1_july(self):
        self.assertEqual(queries.owned_years(date(2003, 1, 1), date(2011, 1, 1)), list(range(2003, 2011)))
        self.assertEqual(queries.owned_years(date(1961, 1, 31), date(1961, 8, 25)), [1961])
        self.assertEqual(queries.owned_years(date(1961, 8, 25), date(1961, 9, 8)), [])
        self.assertEqual(queries.owned_years(date(2016, 8, 31), date(2019, 1, 1)), [2017, 2018])

    def test_an_open_term_runs_to_today(self):
        self.assertEqual(queries.owned_years(date(2023, 1, 1), None)[-1],
                         date.today().year if date.today() >= date(date.today().year, 7, 1) else date.today().year - 1)


class TenureTests(TestCase):
    def setUp(self):
        self.brazil = make_brazil()

    def test_consecutive_terms_of_one_leader_merge(self):
        tenures = queries.tenures('BRA')
        self.assertEqual([t.short_name for t in tenures], ['Souza', 'Lima', 'Dias'])
        self.assertEqual(tenures[0].years(), list(range(2003, 2011)))
        self.assertEqual(len(tenures[1].periods), 2)

    def test_party_spans_follow_the_owned_years(self):
        lima = queries.tenures('BRA')[1]
        spans = queries.party_spans(lima)
        self.assertEqual([(s['from'], s['to'], s['party']['abbreviation']) for s in spans],
                         [(2010, 2012, 'BLU'), (2012, 2014, '')])
        souza = queries.tenures('BRA')[0]
        self.assertEqual([(s['from'], s['to']) for s in queries.party_spans(souza)], [(2002, 2010)])

    def test_summary_runs_from_the_year_before_the_first_year(self):
        values = {2002: 1000.0, 2005: 1500.0, 2010: 3000.0}
        summary = queries.tenure_summary(queries.tenures('BRA')[0], values, GDP.series[0])
        self.assertEqual((summary['startYear'], summary['endYear']), (2002, 2010))
        self.assertEqual(summary['change'], '200%')
        self.assertEqual(summary['amount'], 200.0)
        self.assertTrue(summary['up'])
        self.assertTrue(summary['good'])

    def test_a_rate_changes_in_points_and_falling_unemployment_is_good(self):
        values = {2010: 8.0, 2014: 6.5}
        summary = queries.tenure_summary(queries.tenures('BRA')[1], values, UNEMPLOYMENT.series[0])
        self.assertEqual(summary['change'], '-1.5%')  # a fall carries a minus sign
        self.assertFalse(summary['up'])
        self.assertEqual(summary['amount'], -1.5)
        self.assertTrue(summary['good'])

    def test_growth_in_gdp_trade_and_health_spending_is_good_in_politics_mode(self):
        from politics.metrics import better
        for slug in ('gdp', 'trade', 'health-spending'):
            metric = BY_SLUG[slug]
            self.assertEqual(metric.series[0].better, '', slug)
            self.assertEqual(better(metric, metric.series[0]), 'higher', slug)

    def test_changes_add_up_per_party_and_per_president(self):
        gdp = BY_SLUG['gdp-per-capita']
        unemployment = BY_SLUG['unemployment']
        brazil = Country.objects.get(iso3='BRA')
        # Souza (red) 2003-2010, Lima (blue, then no party) 2011-2014, Dias (red) 2015-.
        for year, value in [(2002, 100.0), (2010, 400.0), (2014, 400.0), (2016, 484.0)]:
            GdpPerCapitaCountryYear.objects.create(country=brazil, year=year, value=value)
        data = queries.chart_data(gdp, gdp.series[0], brazil)
        red = next(row for row in data['byParty'] if row['party']['abbreviation'] == 'RED')
        # Growth compounds: x4 over 8 years, then x1.21 over 2 years, is x4.84 over 10 years.
        self.assertEqual(red['presidents'], ['Souza', 'Dias'])
        self.assertEqual((red['years'], red['terms']), (10, 2))
        self.assertEqual(red['total']['change'], '384%')
        self.assertEqual(red['perYear']['change'], '17%')
        # Lima ended without a party, so his presidency counts for "No party".
        self.assertIn('No party', [row['party']['name'] for row in data['byParty']])
        for year, value in [(2010, 8.0), (2014, 6.0), (2016, 7.0)]:
            UnemploymentCountryYear.objects.create(country=brazil, year=year, value=value)
        data = queries.chart_data(unemployment, unemployment.series[0], brazil)
        # Rates add up: Lima -2 points over 4 years, -0.5 a year. Lower is better, so he ranks first.
        self.assertEqual(data['byPresident'][0]['shortName'], 'Lima')
        self.assertEqual((data['byPresident'][0]['total']['change'], data['byPresident'][0]['perYear']['change']), ('-2.0%', '-0.5%'))
        self.assertIs(data['byPresident'][0]['perYear']['good'], True)

    def test_a_window_keeps_only_its_years(self):
        gdp = BY_SLUG['gdp-per-capita']
        brazil = Country.objects.get(iso3='BRA')
        for year, value in [(2002, 100.0), (2006, 150.0), (2010, 400.0), (2014, 300.0)]:
            GdpPerCapitaCountryYear.objects.create(country=brazil, year=year, value=value)
        data = queries.chart_data(gdp, gdp.series[0], brazil, window=(2006, 2012))
        souza, lima, dias = data['presidencies']
        # Souza's term started before the window, so it is measured from 2006: 150 to 400.
        self.assertEqual((souza['summary']['startYear'], souza['summary']['change']), (2006, '167%'))
        self.assertIsNone(lima['summary'])  # no data inside 2011-2012
        self.assertTrue(lima['inWindow'])
        self.assertFalse(dias['inWindow'])
        self.assertEqual([row['presidents'] for row in data['byParty']], [['Souza']])

    def test_rising_inflation_is_bad_in_politics_mode_only(self):
        inflation = BY_SLUG['inflation']
        self.assertEqual(inflation.series[0].better, '')
        brazil = Country.objects.get(iso3='BRA')
        InflationCountryYear.objects.create(country=brazil, year=2010, value=5.0)
        InflationCountryYear.objects.create(country=brazil, year=2014, value=6.5)
        data = queries.chart_data(inflation, inflation.series[0], brazil)
        self.assertEqual(data['better'], 'lower')
        self.assertEqual(data['presidencies'][1]['summary']['change'], '1.5%')
        self.assertIs(data['presidencies'][1]['summary']['good'], False)

    def test_only_cc_by_logos_need_a_credit(self):
        brazil = Country.objects.get(iso3='BRA')
        cc_by = Party(country=brazil, abbreviation='PTB', logo='politics/brazil/ptb.svg', logo_licence='CC BY 4.0', logo_author='Ann')
        self.assertEqual(queries.logo_credit(cc_by), 'PTB logo: Ann, CC BY 4.0, Wikimedia Commons')
        for licence in ('Public domain', 'CC0'):
            self.assertEqual(queries.logo_credit(Party(country=brazil, abbreviation='X', logo='x.svg', logo_licence=licence)), '')

    def test_no_summary_without_two_years(self):
        self.assertIsNone(queries.tenure_summary(queries.tenures('BRA')[0], {2010: 5.0}, GDP.series[0]))
        self.assertIsNone(queries.tenure_summary(queries.tenures('BRA')[0], {1990: 5.0}, GDP.series[0]))

    def test_a_change_that_rounds_to_zero_is_no_change(self):
        summary = queries.tenure_summary(queries.tenures('BRA')[1], {2010: 7.0, 2014: 7.01}, UNEMPLOYMENT.series[0])
        self.assertEqual(summary['change'], 'no change')
        self.assertIsNone(summary['up'])
        self.assertIsNone(summary['good'])

    def test_chart_data_starts_the_year_before_the_first_presidency(self):
        for year, value in [(1999, 900.0), (2002, 1000.0), (2010, 3000.0)]:
            GdpPerCapitaCountryYear.objects.create(country=self.brazil, year=year, value=value)
        data = queries.chart_data(GDP, GDP.series[0], self.brazil)
        self.assertEqual(data['points'], [[2002, 1000.0], [2010, 3000.0]])
        self.assertTrue(data['presidencies'][-1]['current'])
        self.assertEqual(data['presidencies'][0]['party']['logo'], '/media/politics/brazil/red.svg')
        self.assertEqual(data['presidencies'][1]['spans'][1]['party']['name'], 'No party')


class ViewTests(TestCase):
    def setUp(self):
        self.brazil = make_brazil()
        UnemploymentCountryYear.objects.create(country=self.brazil, year=2010, value=8.0)
        UnemploymentCountryYear.objects.create(country=self.brazil, year=2014, value=6.5)

    def test_index_lists_countries_with_presidents(self):
        response = self.client.get(reverse('politics:index'))
        self.assertContains(response, 'Brazil')
        self.assertContains(response, 'Carla Dias')
        self.assertContains(response, '3 presidents since 2003')

    def test_a_country_led_by_chancellors_says_chancellor(self):
        germany = Country.objects.create(iso3='DEU', iso2='de', name='Germany')
        party = Party.objects.create(country=germany, abbreviation='CDU', name='Christian Democratic Union', color='#6e6e6e')
        for leader, role, start, end in [('Karl Brandt', 'Chancellor', '1999-01-01', '2004-05-01'),
                                         ('Eva Roth', 'Acting chancellor', '2004-05-01', '2004-05-10'),
                                         ('Lena Weber', 'Chancellor', '2004-05-10', '')]:
            Administration.objects.create(country=germany, leader=leader, short_name=leader.split()[-1], role=role, party=party,
                                          start_date=date.fromisoformat(start), end_date=date.fromisoformat(end) if end else None)
        # The acting chancellor stood in; the count leaves her out.
        self.assertContains(self.client.get(reverse('politics:index')), '2 chancellors since 1999')
        response = self.client.get(reverse('politics:country', args=['germany']))
        self.assertContains(response, '<title>Germany by chancellor · Data Mechanics</title>', html=True)
        self.assertContains(response, 'Every metric we have, chancellor by chancellor, since 1999.')
        self.assertContains(response, '>By chancellor</button>')
        # Keys stay English: the view's key is the only 'president' on the page.
        self.assertNotIn('president', response.content.decode().replace('data-view="president"', '').lower())
        roles = [p['role'] for p in self.client.get(reverse('politics:data', args=['germany'])).json()['presidencies']]
        self.assertEqual(roles, ['', 'Acting chancellor', ''])

    def test_country_page_shows_every_politics_metric(self):
        response = self.client.get(reverse('politics:country', args=['brazil']), {'metric': 'unemployment'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['metric'], UNEMPLOYMENT)
        self.assertEqual(response.context['group'], 'Economy')
        for _, slugs in GROUPS:
            for slug in slugs:
                self.assertContains(response, f'data-metric="{slug}"')

    def test_an_unknown_metric_falls_back_to_the_first(self):
        response = self.client.get(reverse('politics:country', args=['brazil']), {'metric': 'nonsense'})
        self.assertEqual(response.context['metric'].slug, GROUPS[0][1][0])

    def test_an_unknown_country_is_404(self):
        self.assertEqual(self.client.get(reverse('politics:country', args=['narnia'])).status_code, 404)

    def test_data_json(self):
        EtlLoad.objects.create(table_name=UNEMPLOYMENT.table, source_name='World Bank', source_url='https://example.org', row_count=2)
        response = self.client.get(reverse('politics:data', args=['brazil']), {'metric': 'unemployment'})
        data = response.json()
        self.assertEqual(data['points'], [[2010, 8.0], [2014, 6.5]])
        self.assertEqual(data['presidencies'][1]['summary']['change'], '-1.5%')
        self.assertEqual(data['source']['name'], 'World Bank')


class ComparisonTests(TestCase):
    def setUp(self):
        self.brazil = make_brazil()
        others = [('RUS', 'ru'), ('IND', 'in'), ('CHN', 'cn'), ('ZAF', 'za')]
        self.brics = [self.brazil] + [Country.objects.create(iso3=iso3, iso2=iso2, name=iso3) for iso3, iso2 in others]

    def unemployment(self, year, values):
        for country, value in zip(self.brics, values):
            UnemploymentCountryYear.objects.create(country=country, year=year, value=value)

    def test_a_group_is_the_average_of_its_members_in_years_when_all_have_data(self):
        self.unemployment(2010, [8.0, 6.0, 4.0, 2.0, 0.0])
        self.unemployment(2014, [6.5, 5.0, 3.0, 1.0])  # South Africa is missing
        self.assertEqual(comparison.values(UNEMPLOYMENT, UNEMPLOYMENT.series[0])['brics'], {2010: 4.0})

    def test_a_total_has_no_comparison(self):
        for country, value in zip(self.brics, [1.0, 2.0, 3.0, 4.0, 5.0]):
            GdpCountryYear.objects.create(country=country, year=2010, value=value)
            GdpCountryYear.objects.create(country=country, year=2014, value=value * 2)
        gdp = BY_SLUG['gdp']
        self.assertEqual(comparison.values(gdp, gdp.series[0]), {})
        data = self.client.get(reverse('politics:data', args=['brazil']), {'metric': 'gdp', 'compare': 'brics'}).json()
        self.assertEqual((data['comparable'], data['comparison']), ([], None))

    def test_the_world_is_the_sources_world_value(self):
        world = Country.objects.create(iso3='WLD', name='World', is_aggregate=True)
        UnemploymentCountryYear.objects.create(country=world, year=2010, value=5.0)
        self.unemployment(2010, [8.0, 6.0, 4.0, 2.0, 0.0])
        self.assertEqual(comparison.values(UNEMPLOYMENT, UNEMPLOYMENT.series[0])['world'], {2010: 5.0})

    def test_each_term_gets_the_groups_change_over_the_same_years(self):
        self.unemployment(2010, [8.0, 6.0, 4.0, 2.0, 0.0])
        self.unemployment(2014, [6.5, 5.0, 3.0, 1.0, 0.0])
        data = self.client.get(reverse('politics:data', args=['brazil']), {'metric': 'unemployment', 'compare': 'brics'}).json()
        self.assertEqual(data['comparison']['short'], 'BRICS')
        self.assertEqual(data['comparison']['compared'], 'compared with BRICS countries')
        # Lima's term runs from 2010 to 2014: Brazil fell 1.5 points, the BRICS average 0.9.
        lima = data['presidencies'][1]['summary']
        self.assertEqual((lima['change'], lima['compare']['change']), ('-1.5%', '-0.9%'))

    def test_the_ranking_gives_each_leaders_end_values_and_lead_over_the_group(self):
        self.unemployment(2010, [8.0, 6.0, 4.0, 2.0, 0.0])
        self.unemployment(2014, [6.5, 5.0, 3.0, 1.0, 0.0])
        data = self.client.get(reverse('politics:data', args=['brazil']), {'metric': 'unemployment', 'compare': 'brics'}).json()
        lima = next(row for row in data['byPresident'] if row['shortName'] == 'Lima')
        self.assertEqual((lima['end']['year'], lima['end']['label'], lima['compareEnd']['label']), (2014, '6.5%', '3.1%'))
        # Lower unemployment is better, so ending 3.4 points above the group is a lead of -3.4.
        self.assertAlmostEqual(lima['lead'], -3.4)

    def test_a_group_without_values_is_not_comparable(self):
        self.unemployment(2010, [8.0, 6.0, 4.0, 2.0, 0.0])
        data = self.client.get(reverse('politics:data', args=['brazil']), {'metric': 'unemployment', 'compare': 'g7'}).json()
        self.assertEqual((data['comparable'], data['comparison']), (['brics'], None))

    def test_no_comparison_leaves_the_group_out(self):
        self.unemployment(2010, [8.0, 6.0, 4.0, 2.0, 0.0])
        self.unemployment(2014, [6.5, 5.0, 3.0, 1.0, 0.0])
        data = self.client.get(reverse('politics:data', args=['brazil']), {'metric': 'unemployment', 'compare': 'none'}).json()
        self.assertIsNone(data['comparison'])
        self.assertNotIn('compare', data['presidencies'][1]['summary'])
        page = self.client.get(reverse('politics:country', args=['brazil']), {'compare': 'none'})
        self.assertContains(page, '<option value="none" selected>No comparison</option>', html=True)

    def test_an_unknown_group_falls_back_to_the_world(self):
        world = Country.objects.create(iso3='WLD', name='World', is_aggregate=True)
        UnemploymentCountryYear.objects.create(country=world, year=2010, value=5.0)
        self.unemployment(2010, [8.0, 6.0, 4.0, 2.0, 0.0])
        data = self.client.get(reverse('politics:data', args=['brazil']), {'metric': 'unemployment', 'compare': 'nato'}).json()
        self.assertEqual(data['comparison']['key'], 'world')
        self.assertEqual(data['comparison']['points'], [[2010, 5.0]])


class CuratedEtlTests(TestCase):
    PARTIES = 'abbreviation,name,color,logo,logo_source,logo_licence,logo_author\nPT,Workers\' Party,#e30d33,politics/brazil/pt.svg,https://commons.wikimedia.org/x,Public domain,\n'
    ADMINISTRATIONS = ('leader,short_name,role,party,start_date,end_date,notes,source_url\n'
                       'Dilma Rousseff,Dilma,President,PT,2011-01-01,2016-08-31,,https://en.wikipedia.org/x\n'
                       'Military junta,Junta,Military junta,,1969-08-31,1969-10-30,,https://en.wikipedia.org/x\n')

    def test_loads_parties_then_administrations(self):
        Country.objects.create(iso3='BRA', iso2='br', name='Brazil')
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'brazil').mkdir()
            (Path(folder) / 'brazil' / 'parties.csv').write_text(self.PARTIES, encoding='utf-8')
            (Path(folder) / 'brazil' / 'administrations.csv').write_text(self.ADMINISTRATIONS, encoding='utf-8')
            sample = {'brazil': 'BRA'}
            with mock.patch.object(parties, 'DATA', Path(folder)), mock.patch.object(administrations, 'DATA', Path(folder)), \
                    mock.patch.object(parties, 'COUNTRIES', sample), mock.patch.object(administrations, 'COUNTRIES', sample):
                parties.run()
                parties.run()
                administrations.run()
                administrations.run()
        self.assertEqual(Party.objects.count(), 1)
        # A party dropped from the file goes too.
        Party.objects.create(country_id='BRA', abbreviation='OLD', name='Old', color='#999999')
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'brazil').mkdir()
            (Path(folder) / 'brazil' / 'parties.csv').write_text(self.PARTIES, encoding='utf-8')
            with mock.patch.object(parties, 'DATA', Path(folder)), mock.patch.object(parties, 'COUNTRIES', {'brazil': 'BRA'}):
                parties.run()
        self.assertEqual(list(Party.objects.values_list('abbreviation', flat=True)), ['PT'])
        self.assertEqual(Administration.objects.count(), 2)
        self.assertEqual(Administration.objects.get(short_name='Dilma').party.abbreviation, 'PT')
        self.assertIsNone(Administration.objects.get(short_name='Junta').party)
        self.assertEqual(EtlLoad.objects.filter(table_name='pol_administration').count(), 2)


def _luminance(color):
    channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


class CuratedDataTests(SimpleTestCase):
    """The hand-made files in data/politics/: each country's terms follow one another, and every party is complete."""

    CHART_WELL = '#1d1f21'

    def read(self, folder, name):
        with open(DATA / folder / name, encoding='utf-8') as file:
            return list(csv.DictReader(file))

    def test_terms_follow_one_another(self):
        for folder in COUNTRIES:
            rows = self.read(folder, 'administrations.csv')
            for previous, row in zip(rows, rows[1:]):
                self.assertEqual(previous['end_date'], row['start_date'], f'{folder}: gap or overlap before {row["leader"]}')
            for row in rows:
                if row['end_date']:
                    self.assertLess(date.fromisoformat(row['start_date']), date.fromisoformat(row['end_date']), folder)
                self.assertIn(row['role'], ROLES, f'{folder}: add the role to politics.offices.ROLES')
            self.assertFalse(any(row['end_date'] == '' for row in rows[:-1]), f'{folder}: only the last term may be open')

    def test_every_party_is_known_has_a_logo_file_and_a_readable_colour(self):
        well = _luminance(self.CHART_WELL)
        for folder in COUNTRIES:
            known = {row['abbreviation']: row for row in self.read(folder, 'parties.csv')}
            for row in self.read(folder, 'administrations.csv'):
                self.assertTrue(row['party'] == '' or row['party'] in known, f'{folder}: unknown party {row["party"]}')
            for abbreviation, party in known.items():
                self.assertRegex(party['color'], re.compile(r'^#[0-9a-f]{6}$', re.I), abbreviation)
                contrast = (_luminance(party['color']) + 0.05) / (well + 0.05)
                self.assertGreaterEqual(contrast, 3.2, f'{folder}: {abbreviation} is too dark on the chart')
                if party['logo']:
                    self.assertTrue((Path(settings.MEDIA_ROOT) / party['logo']).is_file(), party['logo'])
                    # Windows cannot check out a file named like a device (PRN, CON, AUX, NUL), whatever its extension.
                    self.assertNotRegex(Path(party['logo']).stem, re.compile(r'^(con|prn|aux|nul|com\d|lpt\d)$', re.I),
                                        f'{party["logo"]}: Windows cannot check out this name')
                    self.assertTrue(party['logo_source'] and party['logo_licence'], f'{folder}: {abbreviation} logo needs its source and licence')


class CompassDataTests(SimpleTestCase):
    """The party compass's files: every party is complete, and every position belongs to a known party and survey."""

    def read(self, name):
        with open(DATA / 'brazil' / name, encoding='utf-8') as file:
            return list(csv.DictReader(file))

    def test_every_party_profile_is_complete(self):
        well = _luminance(CuratedDataTests.CHART_WELL)
        for party in self.read('party_profiles.csv'):
            # A party without a free logo shows its abbreviation; one with a logo names its source and licence.
            if party['logo']:
                self.assertTrue((Path(settings.MEDIA_ROOT) / party['logo']).is_file(), party['logo'])
                self.assertTrue(party['logo_source'] and party['logo_licence'], party['key'])
                self.assertNotRegex(Path(party['logo']).stem, re.compile(r'^(con|prn|aux|nul|com\d|lpt\d)$', re.I))
            if party['logo_on_dark']:
                self.assertTrue((Path(settings.MEDIA_ROOT) / party['logo_on_dark']).is_file(), party['logo_on_dark'])
            self.assertGreaterEqual((_luminance(party['color']) + 0.05) / (well + 0.05), 3.2, f"{party['key']} is too dark")
            for end in party['position'].split('|'):
                self.assertIn(end, compass.POSITIONS, party['key'])
            for term in party['ideologies'].split(';'):
                self.assertIn(term, compass.IDEOLOGIES, party['key'])
            self.assertTrue(party['views_source'].startswith('https://en.wikipedia.org/wiki/'))

    def test_every_position_has_its_party_and_survey_on_the_scales(self):
        keys = {party['key'] for party in self.read('party_profiles.csv')}
        rows = self.read('positions.csv')
        for row in rows:
            self.assertIn(row['party'], keys)
            self.assertIn(row['survey'], compass.SURVEYS)
            self.assertTrue(0 <= float(row['economic']) <= 10 and 0 <= float(row['social']) <= 10, row)
            self.assertIn(row['inferred'], ('', 'scale', 'merger'), row)
            if row['inferred'] != 'merger':
                self.assertGreater(int(row['experts']), 4, row)
        # Each survey places a party once, and shows every relevant party, measured or inferred.
        self.assertEqual(len(rows), len({(row['survey'], row['party']) for row in rows}))
        for survey in compass.SURVEYS:
            self.assertIn('uniao', {row['party'] for row in rows if row['survey'] == survey})

    def test_party_names_are_the_parties_own(self):
        # One name per party, in its own language: the file has no English name beside it.
        self.assertNotIn('name_original', self.read('party_profiles.csv')[0])
        names = {party['key']: party['name'] for party in self.read('party_profiles.csv')}
        self.assertEqual(names['pt'], 'Partido dos Trabalhadores')

    def test_every_left_right_score_has_its_party_on_the_scale(self):
        keys = {party['key'] for party in self.read('party_profiles.csv')}
        rows = self.read('left_right.csv')
        for row in rows:
            self.assertIn(row['party'], keys)
            self.assertTrue(0 <= float(row['score']) <= 10, row)
            self.assertGreater(int(row['experts']), 100, row)
        self.assertEqual(len(rows), len({row['party'] for row in rows}))
        self.assertEqual(next(row for row in rows if row['party'] == 'prd')['inferred_from'], 'PTB, Patriota')


class CompassAndCongressTests(TestCase):
    def setUp(self):
        make_brazil()
        party_profiles.run()
        party_positions.run()
        party_left_right.run()
        for i, party in enumerate(['PT'] * 3 + ['PL'] * 4 + ['PSOL'] + ['']):
            Deputy.objects.create(country_id='BRA', member_id=str(i), name=f'Deputy {i}', party=party, state='SP')
        # Two senators stay after the election, one leaves; two new ones join, one coded as the court codes it.
        for i, (party, ends) in enumerate([('PT', 2031), ('PL', 2031), ('MDB', 2027)]):
            Senator.objects.create(country_id='BRA', member_id=str(i), name=f'Senator {i}', party=party, state='SP', term_ends=ends)

    def test_the_compass_is_a_tab_of_the_country_page(self):
        response = self.client.get(reverse('politics:country', args=['brazil']), {'tab': 'compass'})
        self.assertEqual(response.context['tab'], 'compass')
        self.assertContains(response, 'data-tab="compass"')
        compass_data = response.context['compass']
        self.assertEqual([survey['key'] for survey in compass_data['surveys']], ['prepps', 'ches', 'gps'])
        prepps = {p['party']: p for p in compass_data['positions']['prepps']}
        self.assertEqual(prepps['pt']['inferred'], '')
        self.assertEqual(prepps['uniao']['note'], 'Inferred, not measured: the average of DEM, PSL, which merged into it.')
        self.assertTrue(prepps['pcdob']['note'].startswith('Inferred, not measured: estimated from where'))
        self.assertEqual(next(p for p in compass_data['positions']['ches'] if p['party'] == 'pl')['then'], 'Called PR when this survey asked.')
        self.assertEqual(compass_data['parties']['dem']['ended'], 'Merged into União Brasil in 2022.')
        self.assertEqual(compass_data['parties']['psb']['position'], 'Centre to centre-left')

    def test_congress_seats_run_from_left_to_right(self):
        response = self.client.get(reverse('politics:country', args=['brazil']), {'tab': 'congress'})
        self.assertEqual(response.context['tab'], 'congress')
        chamber = response.context['congress']['houses'][0]['terms'][0]
        self.assertEqual(chamber['members'], 9)
        # PSOL before PT before PL, by the left-right scale; the deputy without a party last, not classified.
        self.assertEqual([(p['abbreviation'], p['seats'], p['bloc']) for p in chamber['parties']],
                         [('PSOL', 1, 'left'), ('PT', 3, 'left'), ('PL', 4, 'right'), ('No party', 1, 'none')])
        # No election loaded: no next term.
        self.assertEqual(response.context['congress']['starts'], '')

    def test_the_next_term_is_the_elected_and_the_senators_who_stay(self):
        today = date.today()  # an election today always takes office in the future
        for i, (house, party) in enumerate([('chamber', 'PCDOB'), ('chamber', 'PL'), ('senate', 'PCDOB'), ('senate', 'NOVO')]):
            Elected.objects.create(country_id='BRA', member_id=str(i), name=f'Elected {i}', party=party, state='SP',
                                   house=house, elected_on=today)
        data = self.client.get(reverse('politics:country', args=['brazil']), {'tab': 'congress'}).context['congress']
        self.assertEqual(data['starts'][-4:], str(today.year + 1))
        chamber, senate = ({t['key']: t for t in house['terms']} for house in data['houses'])
        # The court's PCDOB is the Chamber's PCdoB: one party, matched without regard to case.
        self.assertEqual([(p['abbreviation'], p['seats']) for p in chamber['next']['parties']], [('PCdoB', 1), ('PL', 1)])
        self.assertEqual([(p['abbreviation'], p['seats']) for p in senate['next']['parties']], [('PCdoB', 1), ('PT', 1), ('Novo', 1), ('PL', 1)])
        self.assertEqual(len(senate['next']['sources']), 2)
        # Today's seats belong to the legislature that ends as the next one begins; each runs four years.
        year = today.year + 1
        self.assertEqual(chamber['now']['period']['years'], f'{year - 4}–{year}')
        self.assertEqual(chamber['next']['period']['years'], f'{year}–{year + 4}')


class SpectrumTests(SimpleTestCase):
    def test_the_authors_bands_join_into_three_blocs(self):
        cases = {1.5: ('far-left', 'left'), 1.51: ('left-wing', 'left'), 3.0: ('left-wing', 'left'),
                 3.01: ('centre-left', 'centre'), 4.49: ('centre-left', 'centre'), 4.5: ('centre', 'centre'),
                 5.5: ('centre', 'centre'), 5.51: ('centre-right', 'centre'), 7.0: ('centre-right', 'centre'),
                 7.01: ('right-wing', 'right'), 8.5: ('right-wing', 'right'), 8.51: ('far-right', 'right'), 10: ('far-right', 'right')}
        for score, expected in cases.items():
            self.assertEqual(spectrum.band(score), expected, score)


class TseTests(SimpleTestCase):
    def test_only_the_elected_deputies_and_senators_count(self):
        row = {'SQ_CANDIDATO': '1', 'NM_URNA_CANDIDATO': 'A', 'SG_PARTIDO': 'PT', 'SG_UF': 'SP', 'DT_ELEICAO': '04/10/2026'}
        rows = [{**row, 'DS_CARGO': cargo, 'DS_SIT_TOT_TURNO': result} for cargo, result in [
            ('DEPUTADO FEDERAL', 'ELEITO POR QP'), ('DEPUTADO FEDERAL', 'ELEITO POR MÉDIA'), ('DEPUTADO FEDERAL', 'SUPLENTE'),
            ('SENADOR', 'ELEITO'), ('SENADOR', 'NÃO ELEITO'), ('GOVERNADOR', 'ELEITO'), ('DEPUTADO ESTADUAL', 'ELEITO POR QP')]]
        found = tse_elected.elected(rows)
        self.assertEqual([member.house for member in found], ['chamber', 'chamber', 'senate'])
        self.assertEqual(found[0].elected_on, date(2026, 10, 4))
