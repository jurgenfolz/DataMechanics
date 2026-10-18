from django.test import TestCase
from django.urls import reverse

from geo.models import Country, EtlLoad, GdpPerCapitaCountryYear, UnemploymentCountryYear

from . import queries, search
from .catalog import BY_SLUG, METRICS
from .formatting import UNITS, format_change, format_value


class CatalogTests(TestCase):
    def test_every_series_is_a_column_of_its_table(self):
        for metric in METRICS:
            columns = {field.name for field in metric.model._meta.get_fields()}
            for series in metric.series:
                self.assertIn(series.field, columns, metric.slug)
                self.assertIn(series.unit, UNITS, metric.slug)
                self.assertIn(series.better, ('', 'higher', 'lower'), metric.slug)

    def test_tags_follow_the_claude_md_shape(self):
        for metric in METRICS:
            self.assertLessEqual(len(metric.tags.subcategories), 4, metric.slug)
            self.assertLessEqual(len(metric.tags.granularity), 3, metric.slug)
            self.assertTrue(metric.table.startswith('geo_') and metric.table.endswith('_country_year'))

    def test_slugs_are_unique(self):
        self.assertEqual(len(BY_SLUG), len(METRICS))


class FormattingTests(TestCase):
    def test_units(self):
        self.assertEqual(format_value(30_770_000_000_000, 'usd'), '$30.8 tn')
        self.assertEqual(format_value(1_463_865_525, 'people'), '1.46 bn')
        self.assertEqual(format_value(4.83, 'percent'), '4.8%')
        self.assertEqual(format_value(0.9134, 'index'), '0.913')
        self.assertEqual(format_value(None, 'index'), '–')
        self.assertEqual(format_value(37_790_000_000, 'tonnes_total'), '37.8 bn t')
        self.assertEqual(format_value(2.312, 'per_woman'), '2.31 per woman')
        self.assertEqual(format_value(-1_234_567, 'people'), '-1.23 m')

    def test_changes(self):
        self.assertEqual(format_change(8.0, 6.5, 'percent'), '1.5 pp')
        self.assertEqual(format_change(1000, 3000, 'usd', relative=True), '200%')
        self.assertEqual(format_change(1000, 1053, 'usd', relative=True), '5.3%')
        self.assertEqual(format_change(70.1, 73.4, 'years'), '3.3 yrs')
        self.assertEqual(format_change(12.0, 10.5, 'per_1000'), '1.5')


class SearchTests(TestCase):
    def test_every_word_must_match(self):
        # Metrics named after GDP come first; those measured as a share of GDP (debt, tax, trade...) follow.
        slugs = [m.slug for m in search.find('gdp')]
        self.assertEqual(slugs[:3], ['gdp', 'gdp-per-capita', 'gdp-growth'])
        self.assertIn('government-debt', slugs)
        self.assertEqual([m.slug for m in search.find('gdp person')], ['gdp-per-capita'])
        self.assertEqual(search.find('no such thing'), [])

    def test_category_filter(self):
        self.assertTrue(all(m.tags.category == 'Economy' for m in search.find(category='Economy')))


def load_sample():
    """Three countries and World, two years of GDP per capita and unemployment."""
    for iso3, iso2, name in [('LUX', 'lu', 'Luxembourg'), ('IRL', 'ie', 'Ireland'), ('IND', 'in', 'India')]:
        Country.objects.create(iso3=iso3, iso2=iso2, name=name)
    Country.objects.create(iso3='WLD', name='World', is_aggregate=True)
    for model, rows in [
        (GdpPerCapitaCountryYear, {'LUX': (138e3, 147e3), 'IRL': (113e3, 132e3), 'IND': (2.5e3, 2.7e3), 'WLD': (13.6e3, 14.4e3)}),
        (UnemploymentCountryYear, {'LUX': (5.5, 6.0), 'IRL': (4.3, 4.4), 'IND': (4.2, 4.1), 'WLD': (5.0, 4.8)}),
    ]:
        for iso3, (previous, latest) in rows.items():
            model.objects.create(country_id=iso3, year=2024, value=previous)
            model.objects.create(country_id=iso3, year=2025, value=latest)
        EtlLoad.objects.create(table_name=model._meta.db_table, source_name='World Bank, World Development Indicators',
                               source_url='https://data.worldbank.org/', source_updated='2026-10-08', row_count=8)


class QueryTests(TestCase):
    def setUp(self):
        load_sample()

    def test_ranking_is_highest_first_without_world(self):
        top = queries.ranking(BY_SLUG['gdp-per-capita'])
        self.assertEqual([row['iso3'] for row in top['rows']], ['LUX', 'IRL', 'IND'])
        self.assertEqual((top['year'], top['world'], top['count']), (2025, '$14.4 k', 3))
        self.assertTrue(top['rows'][0]['flag'].endswith('/flags/4x3/lu.svg'))

    def test_chart_data_aligns_values_with_years(self):
        metric = BY_SLUG['gdp-per-capita']
        data = queries.chart_data(metric, metric.series[0])
        self.assertEqual(data['years'], [2024, 2025])
        self.assertEqual(data['values']['IND'], [2500.0, 2700.0])
        self.assertEqual((data['world'], data['mapYear'], data['better']), ('WLD', 2025, 'higher'))
        self.assertEqual(data['countries']['WLD']['name'], 'World')


class ViewTests(TestCase):
    def setUp(self):
        load_sample()

    def test_metric_page_names_its_source(self):
        response = self.client.get(reverse('metrics:detail', args=['gdp-per-capita']))
        self.assertContains(response, 'World Bank, World Development Indicators')
        self.assertContains(response, 'Highest values, 2025')

    def test_data_json_picks_a_series(self):
        response = self.client.get(reverse('metrics:data', args=['population']) + '?series=death_rate')
        self.assertEqual(response.json()['field'], 'death_rate')

    def test_csv_carries_the_source_on_every_row(self):
        response = self.client.get(reverse('metrics:csv', args=['unemployment']))
        lines = response.content.decode().strip().splitlines()
        self.assertEqual(lines[0], 'iso3,country,year,value,source,source_url,source_updated,fetched_at')
        self.assertEqual(len(lines), 9)
        self.assertTrue(all('World Bank' in line for line in lines[1:]))

    def test_unknown_metric_is_404(self):
        self.assertEqual(self.client.get('/metrics/nope/').status_code, 404)

    def test_search_page(self):
        response = self.client.get('/metrics/?q=unemployment')
        self.assertContains(response, 'Unemployment rate')
        self.assertContains(response, 'Where is unemployment highest?')
        self.assertContains(self.client.get('/metrics/?q=zzz'), 'No metric matches')

    def test_shapes_endpoint(self):
        Country.objects.filter(iso3='LUX').update(geometry={'type': 'MultiPolygon', 'coordinates': []})
        features = self.client.get(reverse('metrics:shapes')).json()['features']
        self.assertEqual([f['properties']['iso3'] for f in features], ['LUX'])


class HomeTests(TestCase):
    def test_home_without_data(self):
        self.assertEqual(self.client.get('/').status_code, 200)

    def test_home_with_data(self):
        load_sample()
        response = self.client.get('/')
        self.assertContains(response, 'The world in numbers')
        self.assertContains(response, '<h2 class="slide__title"><a href="/metrics/gdp-per-capita/">GDP per capita</a></h2>', html=True)
        self.assertContains(response, 'Where is output per person highest?')
        self.assertNotContains(response, 'Biggest movers')
        self.assertContains(response, 'About the author')
        self.assertContains(response, 'https://www.linkedin.com/in/klausjfolz/')
