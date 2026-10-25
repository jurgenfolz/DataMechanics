"""What the World War II page reads from the conflicts database: reshaping only, the ETL did the rest."""

from datetime import date
from urllib.parse import parse_qs, urlsplit

from django.conf import settings
from django.utils.formats import date_format

from geo.models import EtlLoad, table_name
from metrics.formatting import format_value

from .models import Battle, Border, Deaths, Event, Side, State

FIRST, LAST = date(1937, 7, 7), date(1945, 9, 2)


def latest_load(model):
    return EtlLoad.objects.filter(table_name=table_name(model)).first()


def source(model):
    """The source line of a chart, as the page's scripts and templates show it."""
    load = latest_load(model)
    if not load:
        return None
    return {'name': load.source_name, 'url': load.source_url, 'updated': load.source_updated,
            'fetched': date_format(load.loaded_at, 'SHORT_DATE_FORMAT')}


def flag_url(state):
    return f'{settings.MEDIA_URL}{state.flag}'


def states():
    """Every state by code: its name, flag, kind, ruler and the sides it fought on, with their dates."""
    sides = {}
    for side in Side.objects.all():
        sides.setdefault(side.state_id, []).append([side.side, side.start.isoformat(),
                                                    side.end.isoformat() if side.end else None])
    return {
        state.code: {
            'name': state.local_name,
            'flag': flag_url(state),
            'kind': str(State.KINDS[state.kind]),
            'ruler': state.ruler_id,
            'sides': sides.get(state.code, []),
        }
        for state in State.objects.all()
    }


def deaths():
    """Every row of Wikipedia's table, for the chart's tooltips and "Show the numbers"."""
    return [
        {
            'code': row.state_id,
            'name': row.state.local_name,
            'flag': flag_url(row.state),
            'population': row.population,
            'military': [row.military_low, row.military_high],
            'civilian': [row.civilian_low, row.civilian_high],
            'famine': [row.famine_low, row.famine_high],
            'total': [row.total_low, row.total_high],
            'share': _share(row),
            'note': row.note,
            'text': {
                'population': format_value(row.population, 'people') if row.population else '–',
                'military': range_text(row.military_low, row.military_high),
                'civilian': range_text(row.civilian_low, row.civilian_high),
                'famine': range_text(row.famine_low, row.famine_high),
                'total': range_text(row.total_low, row.total_high),
                'share': range_text(*_share(row), unit='percent'),
            },
        }
        for row in Deaths.objects.select_related('state').order_by('-total_high', 'state__name')
    ]


def range_text(low, high, unit='people'):
    """A range as the site writes values: "4.44 m–5.32 m", one value when both ends agree, an en dash when empty."""
    if low is None:
        return '–'
    if high is None or high == low:
        return format_value(low, unit)
    return f'{format_value(low, unit)}–{format_value(high, unit)}'


def _share(row):
    """Deaths as a percentage of the 1939 population, lowest and highest estimate."""
    if not row.population or row.total_low is None:
        return [None, None]
    return [round(100 * row.total_low / row.population, 2), round(100 * (row.total_high or row.total_low) / row.population, 2)]


def battles():
    return [
        {
            'id': battle.wikidata,
            'name': battle.local_name,
            'theatre': battle.theatre,
            'start': battle.start.isoformat(),
            'end': battle.end.isoformat(),
            'at': [battle.longitude, battle.latitude],
            'axis': battle.axis,
            'allies': battle.allies,
            'axisCasualties': [battle.axis_low, battle.axis_high],
            'alliesCasualties': [battle.allies_low, battle.allies_high],
            'winner': battle.winner,
            'region': battle.region,
            'source': battle.source_url,
            'wiki': article_url(battle.source_url),
            'image': f'{settings.MEDIA_URL}{battle.image}' if battle.image else '',
            'imageCredit': image_credit(battle),
            'text': {
                'dates': _dates_text(battle.start, battle.end),
                'axis': range_text(battle.axis_low, battle.axis_high),
                'allies': range_text(battle.allies_low, battle.allies_high),
                'winner': str(Battle.WINNERS[battle.winner]),
                'theatre': str(Battle.THEATRES[battle.theatre]),
            },
        }
        for battle in Battle.objects.all()
    ]


def _dates_text(start, end):
    """A battle's dates for a table: "Aug 1937 – Nov 1937", or one date for a battle of one day."""
    if start == end:
        return date_format(start, 'DATE_FORMAT')
    return f"{date_format(start, 'YEAR_MONTH_FORMAT')} – {date_format(end, 'YEAR_MONTH_FORMAT')}"


def events():
    return [
        {
            'date': event.date.isoformat(), 'kind': event.kind, 'region': event.region, 'name': event.local_name,
            'source': event.source_url, 'wiki': article_url(event.source_url),
            'text': {'kind': str(Event.KINDS[event.kind]), 'date': date_format(event.date, 'DATE_FORMAT')},
        }
        for event in Event.objects.all()
    ]


def article_url(permalink):
    """The article a Wikipedia permalink (index.php?title=...&oldid=...) points at, at its current revision."""
    query = parse_qs(urlsplit(permalink).query)
    return f"https://en.wikipedia.org/wiki/{query['title'][0]}" if query.get('title') else permalink


def image_credit(battle):
    """The credit a battle's picture asks for: nothing when it is in the public domain, else its author and licence."""
    if not battle.image or battle.image_licence.lower().startswith(('public domain', 'cc0')):
        return ''
    return f'{battle.image_author} ({battle.image_licence})' if battle.image_author else battle.image_licence


def borders():
    """The shapes of 1937–1945 as GeoJSON.

    Each feature is valid from `start` to `end`.
    Its `state` is the state of ww2.state it is, or its `ruler` the state that governed it.
    """
    return {
        'type': 'FeatureCollection',
        'features': [
            {
                'type': 'Feature',
                'properties': {'id': border.pk, 'gwcode': border.gwcode, 'name': border.name,
                               'start': border.start.isoformat(), 'end': border.end.isoformat(),
                               'state': border.state_id, 'ruler': border.ruler_id},
                'geometry': border.geometry,
            }
            for border in Border.objects.all()
        ],
    }
