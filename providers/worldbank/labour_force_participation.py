"""Labour force participation, % of people aged 15 and over (ILO modelled), World Bank indicator SL.TLF.CACT.ZS. Writes geo_labour_force_participation_country_year."""

from geo.models import LabourForceParticipationCountryYear

from . import api

COLUMNS = {
    'SL.TLF.CACT.ZS': 'value',
}


def run():
    return api.load_indicators(LabourForceParticipationCountryYear, COLUMNS)
