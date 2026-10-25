"""Writes one table and logs the load. Every ETL module ends by calling replace_table() or replace_rows()."""

from dataclasses import dataclass

from django.db import router, transaction

from geo.models import Country, EtlLoad, table_name

WORLD = 'WLD'

# Codes some sources use for countries or aggregates we already know under another code.
_ALIASES = {
    'KOS': 'XKX',  # Kosovo: Natural Earth, UNDP
    'UVK': 'XKX',  # Kosovo: IMF
    'WBG': 'PSE',  # West Bank and Gaza: IMF
    'OWID_KOS': 'XKX',  # Kosovo: Our World in Data
    'OWID_WRL': WORLD,
    'ZZK.WORLD': WORLD,  # UNDP
    'WEOWORLD': WORLD,  # IMF
}


def country_code(code):
    """The code geo_country uses for a source's country or aggregate code."""
    return _ALIASES.get(code, code)


@dataclass
class Source:
    name: str
    url: str
    updated: str = ''


@dataclass
class LoadResult:
    rows: int
    skipped_codes: list[str]


def replace_table(model, rows, source):
    """Replace every row of a fact table in one transaction.

    rows maps (code, year) to a dict of field values.
    Codes are normalised with country_code(); codes not in geo_country (mostly regional aggregates) are skipped.
    """
    known = set(Country.objects.values_list('iso3', flat=True))
    objects, skipped = [], set()
    for (code, year), fields in rows.items():
        iso3 = country_code(code)
        if iso3 not in known:
            skipped.add(code)
            continue
        objects.append(model(country_id=iso3, year=year, **fields))
    return LoadResult(rows=replace_rows(model, objects, source), skipped_codes=sorted(skipped))


def replace_rows(model, objects, source):
    """Replace every row of a table with `objects` in one transaction, log the load, and return the row count.

    The table may live in another database (the conflicts tables do); the log always goes to etl_load.
    """
    with transaction.atomic(using=router.db_for_write(model)), transaction.atomic():
        model.objects.all().delete()
        model.objects.bulk_create(objects, batch_size=5000)
        log_load(model, source, len(objects))
    return len(objects)


def log_load(model, source, rows):
    """Record in etl_load that `rows` rows of the model's table were loaded from `source`."""
    EtlLoad.objects.create(
        table_name=table_name(model),
        source_name=source.name,
        source_url=source.url,
        source_updated=source.updated,
        row_count=rows,
    )
