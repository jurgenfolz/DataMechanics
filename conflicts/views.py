"""The Conflicts section: an index of conflicts and one page per conflict. World War II is the first."""

import csv

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.cache import cache_control

from metrics.formatting import units

from . import queries
from .models import Battle, Border, Deaths, Event, State


def index(request):
    return render(request, 'conflicts/index.html', {
        'battles': Battle.objects.count(),
        'states': Deaths.objects.count(),
    })


def world_war_ii(request):
    deaths = queries.deaths()
    border_load = queries.latest_load(Border)
    return render(request, 'conflicts/world_war_ii.html', {
        'deaths': deaths,
        'deaths_load': queries.latest_load(Deaths),
        'battles_load': queries.latest_load(Battle),
        'events_load': queries.latest_load(Event),
        'border_load': border_load,
        'flag_credits': State.objects.exclude(flag_licence__in=['Public domain', 'CC0', 'Data Mechanics']),
        'config': {
            'states': queries.states(),
            'deaths': deaths,
            'battles': queries.battles(),
            'events': queries.events(),
            'first': queries.FIRST.isoformat(),
            'last': queries.LAST.isoformat(),
            'theatres': {key: str(label) for key, label in Battle.THEATRES.items()},
            'bordersUrl': f"{reverse('conflicts:ww2-borders')}?v={int(border_load.loaded_at.timestamp()) if border_load else 0}",
            'units': units(),
            'sources': {'deaths': queries.source(Deaths), 'battles': queries.source(Battle),
                        'borders': queries.source(Border)},
        },
    })


@cache_control(public=True, max_age=86400)
def ww2_borders(request):
    """The borders of 1937–1945. Its address carries the load time, so browsers may keep it for a day."""
    return JsonResponse(queries.borders())


def ww2_deaths_csv(request):
    """Every row of the deaths table, with its source on each row so any extract stays cited."""
    response, writer = _csv('data-mechanics-ww2-deaths.csv')
    source = _source_cells(queries.latest_load(Deaths))
    writer.writerow(['state', 'name', 'population_1939', 'military_low', 'military_high', 'civilian_low',
                     'civilian_high', 'famine_disease_low', 'famine_disease_high', 'total_low', 'total_high', 'note',
                     *SOURCE_COLUMNS])
    for row in Deaths.objects.select_related('state').order_by('state__name'):
        writer.writerow([row.state_id, row.state.name, row.population, row.military_low, row.military_high,
                         row.civilian_low, row.civilian_high, row.famine_low, row.famine_high, row.total_low,
                         row.total_high, row.note, *source])
    return response


def ww2_battles_csv(request):
    """Every battle with its casualties per side. Each row's source is the Wikipedia revision it comes from."""
    response, writer = _csv('data-mechanics-ww2-battles.csv')
    fetched = _source_cells(queries.latest_load(Battle))[-1]
    writer.writerow(['wikidata', 'name', 'theatre', 'start', 'end', 'latitude', 'longitude', 'axis', 'allies',
                     'axis_casualties_low', 'axis_casualties_high', 'allies_casualties_low', 'allies_casualties_high',
                     'winner', 'note', 'source_url', 'fetched_at'])
    for battle in Battle.objects.all():
        writer.writerow([battle.wikidata, battle.name, battle.theatre, battle.start, battle.end, battle.latitude,
                         battle.longitude, ' '.join(battle.axis), ' '.join(battle.allies), battle.axis_low,
                         battle.axis_high, battle.allies_low, battle.allies_high, battle.winner, battle.note,
                         battle.source_url, fetched])
    return response


SOURCE_COLUMNS = ['source', 'source_url', 'source_updated', 'fetched_at']


def _csv(filename):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response, csv.writer(response)


def _source_cells(load):
    """The source columns of a CSV row, from the table's latest load."""
    if not load:
        return [''] * len(SOURCE_COLUMNS)
    return [load.source_name, load.source_url, load.source_updated, load.loaded_at.isoformat()]
