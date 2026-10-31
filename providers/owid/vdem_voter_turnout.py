"""Voter turnout in national elections, % of registered voters, V-Dem via Our World in Data. Writes geo_voter_turnout_country_year."""

from geo.models import VoterTurnoutCountryYear

from . import grapher

CHARTS = {
    'voter-turnout-of-registered-voters': {'turnout_vdem': 'value'},
}


def run():
    return grapher.load_charts(VoterTurnoutCountryYear, CHARTS)
