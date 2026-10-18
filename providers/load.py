"""Writes one fact table and logs the load. Every ETL module ends by calling replace_table()."""

from dataclasses import dataclass

from django.db import transaction

from geo.models import Country, EtlLoad

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

    with transaction.atomic():
        model.objects.all().delete()
        model.objects.bulk_create(objects, batch_size=5000)
        EtlLoad.objects.create(
            table_name=model._meta.db_table,
            source_name=source.name,
            source_url=source.url,
            source_updated=source.updated,
            row_count=len(objects),
        )
    return LoadResult(rows=len(objects), skipped_codes=sorted(skipped))
