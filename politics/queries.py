"""Reads presidencies and one country's metric values for Politics mode.

A year belongs to the leader in office on 1 July. On the chart, the stretch of line that ends at a year takes the colour
of that year's leader. A presidency's change runs from the year before its first year to its last year with data.
"""

from dataclasses import dataclass, field
from datetime import date

from django.conf import settings
from django.utils.translation import gettext, gettext_lazy as _
from django.utils.text import slugify

from geo.models import Country
from metrics.formatting import format_change, format_value
from metrics.queries import flag_url

from .models import Administration

MIDYEAR = (7, 1)

# Roles as written in data/politics/<country>/administrations.csv, and how the page names them.
ROLES = {
    'President': _('President'),
    'Acting president': _('Acting president'),
    'President (military rule)': _('President (military rule)'),
    'Military junta': _('Military junta'),
}


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


def tenure_summary(tenure, values, series):
    """The values at the start and end of a presidency and the change between them, or None without data."""
    owned = tenure.years()
    years = [year for year in owned if year in values]
    if not years:
        return None
    baseline_year = owned[0] - 1 if owned[0] - 1 in values else years[0]
    end_year = years[-1]
    if end_year == baseline_year:
        return None
    start, end = values[baseline_year], values[end_year]
    change = format_change(start, end, series.unit, relative=series.log_scale)
    moved = any(digit in change for digit in '123456789')
    return {
        'startYear': baseline_year,
        'startValue': start,
        'startLabel': format_value(start, series.unit, compact=True),
        'endYear': end_year,
        'endValue': end,
        'endLabel': format_value(end, series.unit, compact=True),
        'change': change if moved else gettext('no change'),
        'up': end > start if moved else None,
        'good': None if not series.better or not moved else (end > start) == (series.better == 'higher'),
    }


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


def chart_data(metric, series, country):
    items = tenures(country.iso3)
    first_year = next((t.years()[0] for t in items if t.years()), None)
    values = country_values(metric, series, country.iso3)
    presidencies = [{
        'leader': tenure.leader,
        'shortName': tenure.short_name,
        'role': str(ROLES.get(tenure.role, tenure.role)),
        'start': tenure.start.isoformat(),
        'end': tenure.end.isoformat() if tenure.end else None,
        'current': tenure.end is None,
        'party': party_info(tenure.periods[0].party),
        'spans': party_spans(tenure),
        'summary': tenure_summary(tenure, values, series),
    } for tenure in items]
    return {
        'field': series.field, 'label': series.label, 'unit': series.unit, 'better': series.better,
        'country': country.local_name,
        # Years before the first presidency would have no colour, so the line starts the year before it.
        'points': sorted([year, value] for year, value in values.items() if first_year and year >= first_year - 1),
        'presidencies': presidencies,
    }


def party_info(party):
    """What the page shows for a party; leaders without a party get a neutral grey."""
    if party is None:
        return {'abbreviation': '', 'name': gettext('No party'), 'color': '#999999', 'logo': ''}
    return {
        'abbreviation': party.abbreviation,
        'name': party.name,
        'color': party.color,
        'logo': f'{settings.MEDIA_URL}{party.logo}' if party.logo else '',
    }


def summary_card(country):
    """The Politics index card for one country."""
    items = tenures(country.iso3)
    current = items[-1]
    return {
        'country': country,
        'slug': slugify(country.name),
        'flag': flag_url(country.iso3, country.iso2, '1x1'),
        'current': current,
        'party': party_info(current.periods[-1].party),
        'since': items[0].start.year,
        'count': len({t.leader for t in items if 'president' in t.role.lower()}),
    }
