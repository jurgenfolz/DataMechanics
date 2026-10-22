"""Reads presidencies and one country's metric values for Politics mode.

A year belongs to the leader in office on 1 July. On the chart, the stretch of line that ends at a year belongs to that
year's leader, in the colour of the party the presidency ended in (static/js/lib/term-chart.js).
A presidency's change runs from the year before its first year to its last year with data.
"""

from dataclasses import dataclass, field
from datetime import date

from django.conf import settings
from django.utils.translation import gettext
from django.utils.text import slugify

from geo.models import Country
from metrics.formatting import change_amount, format_amount, format_value
from metrics.queries import flag_url

from .metrics import better as politics_better
from .models import Administration
from .offices import OFFICES, ROLES, office_key

MIDYEAR = (7, 1)


def owned_years(start, end):
    """The years whose 1 July falls in [start, end). An open end runs to today."""
    end = end or date.today()
    return [year for year in range(start.year, end.year + 1) if start <= date(year, *MIDYEAR) < end]


@dataclass
class Tenure:
    """Consecutive administrations of one leader: one presidency, whatever party changes it holds."""

    leader: str
    short_name: str
    role: str
    periods: list = field(default_factory=list)

    @property
    def start(self):
        return self.periods[0].start_date

    @property
    def end(self):
        return self.periods[-1].end_date

    def years(self):
        return owned_years(self.start, self.end)


def countries():
    """Countries with administrations, for the Politics index."""
    codes = Administration.objects.values_list('country_id', flat=True).distinct()
    return [{'country': c, 'slug': slugify(c.name)} for c in Country.objects.filter(iso3__in=codes)]


def country_by_slug(slug):
    return next((item['country'] for item in countries() if item['slug'] == slug), None)


def tenures(iso3):
    result = []
    for administration in Administration.objects.filter(country_id=iso3).select_related('party'):
        last = result[-1] if result else None
        if last and last.leader == administration.leader and last.end == administration.start_date:
            last.periods.append(administration)
        else:
            result.append(Tenure(administration.leader, administration.short_name, administration.role, [administration]))
    return result


def country_values(metric, series, iso3):
    rows = (metric.model.objects.filter(country_id=iso3).exclude(**{f'{series.field}__isnull': True})
            .values_list('year', series.field))
    return dict(rows)


def tenure_summary(tenure, values, series, better=None, window=None):
    """The values at the start and end of a presidency and the change between them, or None without data.

    `better` is the direction that counts as good ('higher' or 'lower'); it defaults to the series' own.
    `window` (first year, last year) keeps only the presidency's years inside it, as the page's year slider chooses.
    A presidency that starts before the window is measured from the window's first year.
    """
    better = series.better if better is None else better
    owned = in_window(tenure.years(), window)
    years = [year for year in owned if year in values]
    if not years:
        return None
    baseline = owned[0] - 1 if not window else max(owned[0] - 1, window[0])
    baseline_year = baseline if baseline in values else years[0]
    end_year = years[-1]
    if end_year == baseline_year:
        return None
    start, end = values[baseline_year], values[end_year]
    relative = series.log_scale and start > 0
    return {
        'startYear': baseline_year,
        'startValue': start,
        'startLabel': format_value(start, series.unit, compact=True),
        'endYear': end_year,
        'endValue': end,
        'endLabel': format_value(end, series.unit, compact=True),
        # True when the change is in percent of the start (growth that multiplies), as the reel's live count needs to know.
        'relative': relative,
        **change_summary(change_amount(start, end, relative), series.unit, relative, better),
    }


def change_summary(amount, unit, relative, better):
    """How a change reads: its size as text, its direction, and whether that is good for the metric.

    `amount` is signed, in percent when `relative`, else in the unit. It is what the timeline's bars are drawn from.
    A fall's text starts with a minus sign, on top of its down arrow and its colour, which are easy to miss.
    A change too small to show at the unit's precision reads as no change.
    The reel counts changes the same way in the browser (static/js/lib/reel.js, nowLayout): change both together.
    """
    text = format_amount(amount, unit, relative)
    moved = any(digit in text for digit in '123456789')
    if not moved:
        text = gettext('no change')
    elif amount < 0:
        text = f'-{text}'
    return {
        'change': text,
        'amount': float(f'{amount:.6g}') if moved else 0,
        'up': amount > 0 if moved else None,
        'good': None if not better or not moved else (amount > 0) == (better == 'higher'),
    }


def final_party(tenure):
    """The party a presidency ended in: it counts for that party, the same rule that colours the chart."""
    return party_info(tenure.periods[-1].party)


def by_party(tenure):
    party = final_party(tenure)
    return party['name'], {'party': party}


def by_president(tenure):
    return tenure.leader, {'leader': tenure.leader, 'shortName': tenure.short_name}


def grouped_changes(items, series, better, key):
    """The presidencies' changes added up per group (a party, a president): in total and as an average per year.

    `items` are (tenure, summary) pairs; `key(tenure)` names a tenure's group and gives what the group shows.
    Only years with data count. Growth that multiplies (series on a log scale, like GDP) compounds: the total multiplies
    the presidencies' changes and the average is the yearly rate that gives the total. Other changes add up, and the
    average divides the total by the years.
    """
    relative = series.log_scale and all(summary['startValue'] > 0 for _, summary in items)
    groups = {}
    for tenure, summary in items:
        name, shows = key(tenure)
        group = groups.setdefault(name, {**shows, 'presidents': [], 'parties': [], 'terms': 0, 'years': 0,
                                         'ratio': 1.0, 'sum': 0.0})
        if tenure.short_name not in group['presidents']:
            group['presidents'].append(tenure.short_name)
        party = final_party(tenure)
        if party not in group['parties']:
            group['parties'].append(party)
        group['terms'] += 1
        group['years'] += summary['endYear'] - summary['startYear']
        group['ratio'] *= summary['endValue'] / summary['startValue'] if relative else 1
        group['sum'] += summary['endValue'] - summary['startValue']
    rows = []
    for group in groups.values():
        ratio, total_years = group.pop('ratio'), group['years']
        total = (ratio - 1) * 100 if relative else group['sum']
        per_year = (ratio ** (1 / total_years) - 1) * 100 if relative else group['sum'] / total_years
        del group['sum']
        rows.append({**group, 'total': change_summary(total, series.unit, relative, better),
                     'perYear': change_summary(per_year, series.unit, relative, better)})
    # Best first: the highest average per year, or the lowest where lower is better.
    rows.sort(key=lambda row: row['perYear']['amount'], reverse=better != 'lower')
    return rows


def party_spans(tenure):
    """The stretches of a presidency's line in one party's colour: from the year before the first owned year to the last."""
    spans = []
    for period in tenure.periods:
        years = owned_years(period.start_date, period.end_date)
        if not years:
            continue
        party = party_info(period.party)
        if spans and spans[-1]['party'] == party:
            spans[-1]['to'] = years[-1]
        else:
            spans.append({'from': years[0] - 1, 'to': years[-1], 'party': party})
    return spans


def in_window(years, window):
    """The years inside window (first, last); all of them without a window."""
    return [year for year in years if not window or window[0] <= year <= window[1]]


def chart_data(metric, series, country, window=None):
    """Everything the country page draws for one series. `window` limits the presidents' changes and rankings to
    those years; the chart's line always has every year."""
    direction = politics_better(metric, series)
    items = tenures(country.iso3)
    first_year = next((t.years()[0] for t in items if t.years()), None)
    values = country_values(metric, series, country.iso3)
    presidencies = [{
        'leader': tenure.leader,
        'shortName': tenure.short_name,
        'role': str(ROLES[tenure.role].label),
        'start': tenure.start.isoformat(),
        'end': tenure.end.isoformat() if tenure.end else None,
        'current': tenure.end is None,
        'party': party_info(tenure.periods[0].party),
        'spans': party_spans(tenure),
        'summary': tenure_summary(tenure, values, series, direction, window),
        'inWindow': bool(in_window(tenure.years(), window)),
    } for tenure in items]
    with_data = [(tenure, p['summary']) for tenure, p in zip(items, presidencies) if p['summary']]
    return {
        'field': series.field, 'label': series.label, 'unit': series.unit, 'better': direction, 'note': str(series.note),
        'measuredIn': str(series.measured_in),
        'byParty': grouped_changes(with_data, series, direction, by_party),
        'byPresident': grouped_changes(with_data, series, direction, by_president),
        'country': country.local_name,
        # Years before the first presidency would have no colour, so the line starts the year before it.
        'points': sorted([year, value] for year, value in values.items() if first_year and year >= first_year - 1),
        'presidencies': presidencies,
    }


def party_info(party):
    """What the page shows for a party; leaders without a party get a neutral grey."""
    if party is None:
        return {'abbreviation': '', 'name': gettext('No party'), 'color': '#999999', 'logo': '', 'credit': ''}
    return {
        'abbreviation': party.abbreviation,
        'name': party.name,
        'color': party.color,
        'logo': f'{settings.MEDIA_URL}{party.logo}' if party.logo else '',
        'credit': logo_credit(party),
    }


def logo_credit(party):
    """The credit a party's logo needs wherever it is shown, or '' when its licence asks for none (public domain, CC0)."""
    if not party.logo or not party.logo_licence.startswith('CC BY'):
        return ''
    return gettext('%(party)s logo: %(author)s, %(licence)s, Wikimedia Commons') % {
        'party': party.abbreviation, 'author': party.logo_author, 'licence': party.logo_licence}


def summary_card(country):
    """The Politics index card for one country."""
    items = tenures(country.iso3)
    current = items[-1]
    office = office_key(items)
    # Leaders who held the office, not those who only stood in for a few days (Germany: 10 chancellors, not Scheel too).
    count = len({t.leader for t in items if ROLES[t.role].office == office and not ROLES[t.role].acting})
    return {
        'country': country,
        'slug': slugify(country.name),
        'flag': flag_url(country.iso3, country.iso2, '1x1'),
        'current': current,
        'party': party_info(current.periods[-1].party),
        'leaders': OFFICES[office].count % {'count': count, 'year': items[0].start.year},
    }
