"""The six Worldwide Governance Indicators, World Bank. Writes geo_governance_indicators_country_year."""

from geo.models import GovernanceIndicatorsCountryYear

from . import api

COLUMNS = {
    'GOV_WGI_RL.EST': 'rule_of_law',
    'GOV_WGI_GE.EST': 'effectiveness',
    'GOV_WGI_RQ.EST': 'regulation',
    'GOV_WGI_VA.EST': 'voice',
    'GOV_WGI_PV.EST': 'stability',
    'GOV_WGI_CC.EST': 'corruption',
}


def run():
    return api.load_indicators(GovernanceIndicatorsCountryYear, COLUMNS, database=api.WGI)
