"""Merchandise exports by kind, % of the total, World Bank indicators TX.VAL.*.ZS.UN. Writes geo_export_structure_country_year."""

from geo.models import ExportStructureCountryYear

from . import api

COLUMNS = {
    'TX.VAL.FUEL.ZS.UN': 'fuel',
    'TX.VAL.MANF.ZS.UN': 'manufactures',
    'TX.VAL.FOOD.ZS.UN': 'food',
    'TX.VAL.AGRI.ZS.UN': 'agriculture',
    'TX.VAL.MMTL.ZS.UN': 'metals',
}


def run():
    return api.load_indicators(ExportStructureCountryYear, COLUMNS)
