from datetime import date
from unittest import mock

from django.test import TestCase
from django.urls import reverse

from geo.models import Country, EtlLoad
from pages.tests import LanguageTestCase
from providers import CONFLICT_MODULES, MODULES
from providers.curated import ww2_battles
from providers.load import Source, replace_rows
from providers.wikipedia import ww2_deaths

from . import queries
from .models import Battle, Border, Deaths, Event, Side, State
from .routers import ConflictsRouter

BOTH = {'default', 'conflicts'}


def make_state(code, name=None, **fields):
    return State.objects.create(code=code, name=name or code.upper(), kind='sovereign', flag=f'conflicts/ww2/flags/{code}.svg',
                                flag_licence='Public domain', **fields)


class RouterTests(TestCase):
    def test_conflicts_live_in_their_own_database(self):
        router = ConflictsRouter()
        self.assertEqual(router.db_for_read(State), 'conflicts')
        self.assertIsNone(router.db_for_read(Country))
        self.assertTrue(router.allow_migrate('conflicts', 'conflicts'))
        self.assertFalse(router.allow_migrate('default', 'conflicts'))
        self.assertFalse(router.allow_migrate('conflicts', 'geo'))

    def test_table_names_carry_the_schema(self):
        self.assertEqual(State._meta.db_table, 'ww2"."state')


class LoadTests(TestCase):
    databases = BOTH

    def test_the_weekly_refresh_leaves_world_war_ii_alone(self):
        self.assertFalse(set(MODULES) & set(CONFLICT_MODULES))
        self.assertTrue(all('ww2' in module for module in CONFLICT_MODULES))

    def test_replace_rows_logs_the_schema_and_table(self):
        make_state('de')
        replace_rows(Side, [Side(state_id='de', side='axis', start=date(1939, 9, 1))], Source('Test', 'https://example.org'))
        self.assertEqual(Side.objects.count(), 1)
        self.assertEqual(EtlLoad.objects.get().table_name, 'ww2.state_side')

    def test_battles_refuse_an_unknown_state(self):
        make_state('de')
        row = {'qid': 'Q1', 'name': 'B', 'name_de': '', 'name_pt': '', 'theatre': 'east', 'start': '1941-01-01',
               'end': '1941-01-02', 'lat': '50', 'lon': '30', 'axis': 'de', 'allies': 'xx', 'axis_low': '1',
               'axis_high': '2', 'allies_low': '', 'allies_high': '', 'winner': 'none', 'source': 'https://example.org',
               'note': ''}
        with mock.patch.object(ww2_battles, 'ww2_rows', return_value=[row]), self.assertRaisesMessage(ValueError, 'xx'):
            ww2_battles.run()


class WikipediaTableTests(TestCase):
    databases = BOTH

    HTML = '''<table class="wikitable sortable sticky-header"><tbody>
      <tr><th>Country</th><th>Population</th><th>Military</th><th>Civilian</th><th>Famine</th><th>Total</th></tr>
      <tr><td><b><span class="flagicon"></span> <a>Poland</a></b> (within 1939 borders)<sup class="reference">[1]</sup></td>
        <td>34,849,000<sup>[2]</sup></td><td>240,000</td><td>5,620,000 to<br>5,820,000</td><td></td><td>5,900,000 to 6,000,000</td></tr>
      <tr><td><b>Austria</b> (Unified with Germany)</td><td>6,653,000</td><td colspan="2">Included with Germany</td><td></td><td></td></tr>
    </tbody></table><table class="wikitable sortable"><tr><td><b>Other table</b></td><td>1</td></tr></table>'''

    def test_rows_cells_and_notes(self):
        rows = ww2_deaths.parse_table(self.HTML)
        self.assertEqual([row['label'] for row in rows], ['Poland', 'Austria'])
        self.assertEqual(rows[0]['note'], 'within 1939 borders')
        self.assertEqual(rows[0]['civilian'], '5,620,000 to 5,820,000')
        self.assertEqual(rows[1]['military'], 'Included with Germany')
        self.assertEqual(rows[1]['civilian'], 'Included with Germany')

    def test_estimates(self):
        estimate = ww2_deaths.estimate
        self.assertEqual(estimate('30,000'), (30000, 30000))
        self.assertEqual(estimate('2,000,000 to 3,750,000+'), (2000000, 3750000))
        self.assertEqual(estimate('319,200 to 341,000 Italian nationals and c. 20,000 Africans'), (319200, 341000))
        self.assertEqual(estimate('407,300 (250,000 died in the European theater)'), (407300, 407300))
        self.assertEqual(estimate('1,100 (included with the U.K. & Canada)'), (None, None))
        self.assertEqual(estimate('NA'), (None, None))
        self.assertEqual(estimate(''), (None, None))

    def test_an_unknown_row_stops_the_load(self):
        html = self.HTML.replace('Poland', 'Atlantis')
        with mock.patch('providers.http.get_json', return_value={'parse': {'text': html}}), \
                self.assertRaisesMessage(ValueError, 'Atlantis'):
            ww2_deaths.run()


class LinkTests(TestCase):
    def test_article_url_drops_the_revision(self):
        self.assertEqual(queries.article_url('https://en.wikipedia.org/w/index.php?title=Battle_of_Kursk&oldid=12'),
                         'https://en.wikipedia.org/wiki/Battle_of_Kursk')
        self.assertEqual(queries.article_url('https://example.org/'), 'https://example.org/')


class PageTests(LanguageTestCase):
    databases = BOTH

    def setUp(self):
        make_state('de', 'Germany', name_de='Deutschland')
        make_state('su', 'Soviet Union')
        Side.objects.create(state_id='su', side='allies', start=date(1941, 6, 22))
        Deaths.objects.create(state_id='de', label='Germany', population=69_300_000, military_low=4_440_000,
                              military_high=5_318_000, total_low=6_900_000, total_high=7_400_000)
        Battle.objects.create(wikidata='Q38789', name='Battle of Stalingrad', theatre='east', start=date(1942, 7, 17),
                              end=date(1943, 2, 2), latitude=48.7, longitude=44.5, axis=['de'], allies=['su'],
                              axis_low=800_000, axis_high=1_500_000, allies_low=1_129_619, allies_high=1_347_214,
                              winner='allies', source_url='https://en.wikipedia.org/w/index.php?oldid=1')
        Event.objects.create(date=date(1939, 9, 1), kind='war', name='Germany invades Poland', source_url='https://example.org')
        Border.objects.create(gwcode=255, name='Germany', start=date(1938, 9, 30), end=date(1945, 5, 7), state_id='de',
                              geometry={'type': 'MultiPolygon', 'coordinates': []})
        EtlLoad.objects.create(table_name='ww2.deaths_state', source_name='Wikipedia, "World War II casualties"',
                               source_url='https://en.wikipedia.org/w/index.php?oldid=1381850968', row_count=1)

    def test_index_links_to_world_war_ii(self):
        response = self.client.get(reverse('conflicts:index'))
        self.assertContains(response, reverse('conflicts:ww2'))

    def test_world_war_ii_page(self):
        response = self.client.get(reverse('conflicts:ww2'))
        self.assertContains(response, 'Neil Halloran')
        self.assertContains(response, 'Battle of Stalingrad')
        self.assertContains(response, 'oldid=1381850968')
        self.assertContains(response, '6.9 m–7.4 m')

    def test_names_follow_the_language(self):
        response = self.client.get('/de/conflicts/world-war-ii/')
        self.assertContains(response, 'Deutschland')

    def test_borders(self):
        data = self.client.get(reverse('conflicts:ww2-borders')).json()
        self.assertEqual(data['features'][0]['properties']['state'], 'de')

    def test_csv_downloads_carry_their_source(self):
        deaths = self.client.get(reverse('conflicts:ww2-deaths-csv')).content.decode()
        self.assertIn('Wikipedia, ""World War II casualties""', deaths)
        battles = self.client.get(reverse('conflicts:ww2-battles-csv')).content.decode()
        self.assertIn('https://en.wikipedia.org/w/index.php?oldid=1', battles)
