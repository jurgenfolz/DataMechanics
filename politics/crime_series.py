"""Crime per year in one country, by kind of crime: the Crime group of a Politics page, drawn leader by leader.

Each kind of crime acts as a metric of metrics/catalog.py where Politics mode reads one: a slug, a title, a summary and its measures.
Its values come from pol_crime_year (politics.models.CrimeYear), not from a table of its own.
Only this one country has them, so they have no comparison group and no metric page.
tools/<country>_crime.py writes data/politics/<country>/crime.csv; providers/curated/crime.py loads it.
"""

from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _, pgettext_lazy

from geo.models import EtlLoad, State
from metrics.catalog import Series

from .models import CrimeYear


@dataclass(frozen=True)
class Licence:
    name: str
    url: str


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    updated: str = ''  # the source's own release date
    licence: Licence | None = None  # a licence whose terms ask to be named beside the source


@dataclass(frozen=True)
class Crime:
    """A kind of crime in one country, with its measures (catalog Series, whose fields are pol_crime_year's measures)."""

    key: str  # the `crime` column of pol_crime_year
    title: str
    summary: str
    series: tuple
    source: Source
    states_note: str = ''  # what its map by state says beside the country's note (STATES_NOTE)
    states_source: Source | None = None  # where its figures by state come from, when not from `source`

    @property
    def slug(self):
        """The page's ?metric=: prefixed, so a kind of crime never takes a catalog metric's slug."""
        return f'crime-{self.key}'


def joined(*notes):
    """Notes as one text, in the page's language: the empty ones are left out."""
    notes = [note for note in notes if note]
    return format_lazy(' '.join(['{}'] * len(notes)), *notes) if notes else ''


# ---------- Germany: the Bundeskriminalamt's police crime statistics (PKS), from 1993 ----------
DL_DE = Licence('dl-de/by-2-0', 'https://www.govdata.de/dl-de/by-2-0')
PKS_PAGE = ('https://www.bka.de/DE/AktuelleInformationen/StatistikenLagebilder/PolizeilicheKriminalstatistik/PKS2025/'
            'pksTabellen_Interpretationshilfen/Zeitreihen/zeitreihen_node.html')
# The BKA asks for the report year and the table's version.
PKS_CASES = Source('Bundeskriminalamt, Polizeiliche Kriminalstatistik 2025, Zeitreihe T01 (V1.1)', PKS_PAGE, '2026-04-08', DL_DE)
PKS_SUSPECTS = Source('Bundeskriminalamt, Polizeiliche Kriminalstatistik 2025, Zeitreihen T01 (V1.1), T40 (V1.0), T50 (V1.0)',
                      PKS_PAGE, '2026-04-15', DL_DE)
PKS_LAENDER = Source('Bundeskriminalamt, Polizeiliche Kriminalstatistik 2014–2025, Tabelle 01 Länder (2025: V1.0)',
                     'https://www.bka.de/DE/AktuelleInformationen/StatistikenLagebilder/PolizeilicheKriminalstatistik/'
                     'PKS2025/pksTabellen_Interpretationshilfen/LandFalltabellen/landFalltabellen.html', '2026-03-06', DL_DE)
PKS_VICTIMS = Source('Bundeskriminalamt, Polizeiliche Kriminalstatistik 2025, Zeitreihen T91 (V1.1), T91 OGZ (V1.0), T92 (V1.0)',
                     PKS_PAGE, '2026-04-08', DL_DE)

RATE_NOTE = _('The BKA counts the population on the 2011 census from 2013, and on the 2022 census from 2024. '
              'Each found fewer people, which raised the rates a little: by 1.4% in 2024.')
CLEARANCE_NOTE = _('The share of recorded cases in which the police identified a suspect.')
COMPLETED_NOTE = _('Our calculation: the recorded cases minus the attempts.')


def pks(key, title, summary, note='', better='lower', completed=False, states_note=''):
    """A kind of crime from the PKS's table T01: cases per 100,000 people, cases and the clearance rate, also by Land.
    `note` holds for every measure; `completed` adds the cases without attempts (murder, manslaughter).
    """
    measures = [
        Series('rate', _('Cases per 100,000 people'), 'per_100k', better=better, log_scale=True, short=_('Per 100,000 people'),
               measured_in=pgettext_lazy('measured in', 'cases per 100,000 people'), note=joined(note, RATE_NOTE)),
        Series('cases', _('Recorded cases'), 'count', better=better, log_scale=True, short=_('Cases'),
               measured_in=pgettext_lazy('measured in', 'cases a year'), note=note),
    ]
    if completed:
        measures.append(Series('completed', _('Completed cases, without attempts'), 'count', better=better, log_scale=True,
                               short=_('Completed'), measured_in=pgettext_lazy('measured in', 'cases a year'),
                               note=joined(note, COMPLETED_NOTE)))
    measures.append(Series('clearance', _('Clearance rate'), 'percent', better='higher',
                           measured_in=pgettext_lazy('measured in', '% of cases'), note=joined(note, CLEARANCE_NOTE)))
    return Crime(key, title, summary, tuple(measures), PKS_CASES, states_note, PKS_LAENDER)


CANNABIS = _('Cannabis became partly legal on 1 April 2024, so fewer acts count as offences from that year.')
POLICE_CHECKS = _('Most are found by police checks, so more checks find more: the count says as much about policing '
                  'as about the offence.')

FEW_CASES = _('Most Länder count few cases a year, so a single series can move a rate a lot: 79 of Berlin\'s 111 '
              'murders in 2025 belong to one.')

GERMANY = [
    pks('all', _('All recorded offences'),
        _('Every offence the police recorded and handed to the prosecutors, from theft to murder.'),
        joined(CANNABIS, _('Offences against residence and asylum law, which only foreigners can break, are included; '
                           'the next tab leaves them out.'))),
    pks('without-immigration-law', _('Without residence and asylum law'),
        _('Every recorded offence but those against residence and asylum law, which only foreigners can break.'),
        joined(_('The BKA gives this total from 2005.'), CANNABIS)),
    Crime('suspects', _('Suspects'),
          _('The people the police registered as suspects, each once a year, for every offence but those against residence '
            'and asylum law.'),
          (
              Series('suspects', _('Suspects'), 'people', better='lower', log_scale=True,
                     measured_in=pgettext_lazy('measured in', 'people a year'),
                     note=_('The police count each suspect once a year from 2009, so the line starts then.')),
              Series('german', _('German suspects per 100,000 Germans'), 'per_100k', better='lower', log_scale=True,
                     short=_('Germans, per 100,000'), measured_in=pgettext_lazy('measured in', 'suspects per 100,000 people'),
                     note=joined(_('Suspects who live in Germany, aged 8 and over, per 100,000 residents of that age. '
                                   'The line starts in 2013, the first year on the 2011 census.'),
                                 _('From 2024 the population comes from the 2022 census, which counted 0.5% fewer Germans.'))),
              Series('non_german', _('Non-German suspects per 100,000 non-Germans'), 'per_100k', better='lower', log_scale=True,
                     short=_('Non-Germans, per 100,000'), measured_in=pgettext_lazy('measured in', 'suspects per 100,000 people'),
                     note=joined(_('Suspects who live in Germany, aged 8 and over, per 100,000 residents of that age: '
                                   'those who do not live here, such as tourists, are left out. '
                                   'The line starts in 2013, the first year on the 2011 census.'),
                                 _('From 2024 the population comes from the 2022 census, which counted 6% fewer foreign '
                                   'residents than the figures before it. On those, the rate in 2024 would be 4,789 instead '
                                   'of 5,091.'))),
          ),
          PKS_SUSPECTS),
    pks('violent', _('Violent crime'),
        _('Murder, manslaughter, rape and serious sexual assault, robbery, dangerous and serious bodily harm, kidnapping and '
          'hostage taking, as the BKA adds them up.'),
        _('The BKA changed what it adds up slightly in 2017 and 2018, with the new sexual offences law.')),
    Crime('victims', _('Victims of violent crime'),
          _('The people the police recorded as victims of violent crime. A person attacked twice counts twice.'),
          (
              Series('rate', _('Victims per 100,000 people'), 'per_100k', better='lower', log_scale=True,
                     short=_('Per 100,000 people'), measured_in=pgettext_lazy('measured in', 'victims per 100,000 people'),
                     note=RATE_NOTE),
              Series('victims', _('Victims'), 'people', better='lower', log_scale=True,
                     measured_in=pgettext_lazy('measured in', 'victims a year')),
              Series('family', _('Victims of a partner or relative'), 'people', better='lower', log_scale=True,
                     short=_('Of a partner or relative'), measured_in=pgettext_lazy('measured in', 'victims a year'),
                     note=_('Spouses, partners, former partners and relatives. '
                            'The BKA redefined these relationships in 2014, so the line starts then.')),
          ),
          PKS_VICTIMS),
    pks('murder', _('Murder'),
        _('Killing with a motive or means the law names, such as greed or cruelty (§ 211 of the Criminal Code). '
          'Attempts are included.'),
        _('In 2025, 79 cases belong to one series in Berlin, in which a former palliative care doctor is suspected.'),
        completed=True, states_note=FEW_CASES),
    pks('manslaughter', _('Manslaughter'),
        _('Killing without the features of murder, and killing on request (§§ 212, 213 and 216). '
          'Attempts are included, and most cases are attempts.'),
        completed=True, states_note=FEW_CASES),
    pks('rape', _('Rape and serious sexual assault'),
        _('Rape and sexual assault in their especially serious forms (§§ 177 and 178).'),
        _('A law of 2016 made any sexual act against a person\'s will an offence, and changed what the police count in 2017 '
          'and 2018. The years before do not compare, so the line starts in 2018.')),
    pks('sexual-harassment', _('Sexual harassment'),
        _('Touching someone sexually against their will (§ 184i), an offence since November 2016.'),
        _('The line starts in 2017, the first whole year.')),
    pks('child-sexual-abuse', _('Sexual abuse of children'),
        _('Sexual abuse of children under 14 (§§ 176 to 176e).'),
        _('A law of 2021 changed these offences, and the BKA does not compare 2022 with the years before, '
          'so the line starts in 2022.')),
    pks('robbery', _('Robbery'),
        _('Taking something by force or threat, including robbery-like extortion and attacks on drivers.')),
    pks('serious-bodily-harm', _('Dangerous and serious bodily harm'),
        _('Assaults with a weapon or a dangerous tool, by several people together or endangering life, and those that leave '
          'lasting harm (§§ 224 and 226).')),
    pks('bodily-harm', _('Simple bodily harm'),
        _('Assaults without a weapon and without lasting harm (§ 223).')),
    pks('assaults-on-officers', _('Resisting and attacking officers'),
        _('Resisting or attacking the police and others who enforce the law, and related offences against the state\'s '
          'authority.'),
        _('A law of 2017 made attacks on officers an offence of their own, so the line starts in 2018.')),
    pks('theft', _('Theft'),
        _('Every theft, simple and aggravated: shoplifting, burglary, bicycles, cars and more.')),
    pks('burglary', _('Domestic burglary'),
        _('Breaking into homes. Attempts are included, and nearly half the cases are attempts.')),
    pks('car-theft', _('Car theft'),
        _('Theft of cars, vans and lorries, joyriding included.')),
    pks('pickpocketing', _('Pickpocketing'),
        _('Theft from pockets and bags.')),
    pks('fraud', _('Fraud'),
        _('Fraud of every kind (§§ 263 to 265e): goods and services not paid for, online shopping, payment cards and more.'),
        _('A change in how the police count raised the numbers in 1994, so the line starts then. '
          'Fraud run from abroad is not counted.')),
    pks('cybercrime', _('Cybercrime'),
        _('Crimes against computers and data, such as computer fraud, data theft and sabotage.'),
        _('Only crimes committed in Germany are counted, not attacks from abroad or from unknown places. '
          'The line starts in 2016, after changes in how the police count.')),
    pks('criminal-damage', _('Criminal damage'),
        _('Damaging or destroying other people\'s property, graffiti included.')),
    pks('drugs', _('Drug offences'),
        _('Possessing, trading, importing and growing illegal drugs.'),
        joined(POLICE_CHECKS, CANNABIS), better=''),
    pks('immigration-law', _('Residence and asylum law'),
        _('Illegal entry and stay, and other offences against the residence, asylum and free movement laws. '
          'Only foreigners can commit them.'),
        better=''),
    pks('weapons', _('Weapons law'),
        _('Carrying or owning weapons against the Weapons Act.'),
        POLICE_CHECKS, better=''),
]


# ---------- Brazil: death certificates (SIM) from 1979, and police records (Sinesp) from 2015 ----------
# Both are federal data, free to reuse under Decreto 8.777/2016, art. 4.
SIM = Source('Ministério da Saúde, DATASUS, Sistema de Informações sobre Mortalidade (SIM)',
             'http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sim/cnv/ext10uf.def')
PRISONS = Source('Secretaria Nacional de Políticas Penais (Senappen), Infopen, Sisdepen',
                 'https://www.gov.br/senappen/pt-br/servicos/sisdepen')
SINESP = Source('Ministério da Justiça e Segurança Pública, Sinesp VDE, Dados Nacionais de Segurança Pública',
                'https://www.gov.br/mj/pt-br/assuntos/sua-seguranca/seguranca-publica/estatistica/dados-nacionais-1/'
                'base-de-dados-e-notas-metodologicas-dos-gestores-estaduais-sinesp-vde-2022-e-2023', '2026-10-26')

# What a series counts -> its count's label, short label and unit.
COUNTED = {
    'deaths': (_('Deaths'), _('Deaths'), pgettext_lazy('measured in', 'deaths a year')),
    'victims': (_('Victims'), _('Victims'), pgettext_lazy('measured in', 'victims a year')),
    'cases': (_('Recorded cases'), _('Cases'), pgettext_lazy('measured in', 'cases a year')),
    'vehicles': (_('Vehicles'), _('Vehicles'), pgettext_lazy('measured in', 'vehicles a year')),
    'suspects': (_('Suspects'), _('Suspects'), pgettext_lazy('measured in', 'people a year')),
    'firearms': (_('Firearms seized'), _('Firearms'), pgettext_lazy('measured in', 'firearms a year')),
    'prisoners': (_('Prisoners'), _('Prisoners'), pgettext_lazy('measured in', 'people in prison')),
}
# What it counts and whom its rate divides by -> the rate's label, short label and unit.
RATES = {
    ('deaths', 'all'): (_('Deaths per 100,000 people'), _('Per 100,000 people'),
                        pgettext_lazy('measured in', 'deaths per 100,000 people')),
    ('deaths', 'women'): (_('Deaths per 100,000 women'), _('Per 100,000 women'),
                          pgettext_lazy('measured in', 'deaths per 100,000 women')),
    ('deaths', 'young'): (_('Deaths per 100,000 people aged 15 to 29'), _('Per 100,000 aged 15 to 29'),
                          pgettext_lazy('measured in', 'deaths per 100,000 people aged 15 to 29')),
    ('victims', 'all'): (_('Victims per 100,000 people'), _('Per 100,000 people'),
                         pgettext_lazy('measured in', 'victims per 100,000 people')),
    ('victims', 'women'): (_('Victims per 100,000 women'), _('Per 100,000 women'),
                           pgettext_lazy('measured in', 'victims per 100,000 women')),
    ('cases', 'all'): (_('Cases per 100,000 people'), _('Per 100,000 people'),
                       pgettext_lazy('measured in', 'cases per 100,000 people')),
    ('vehicles', 'all'): (_('Vehicles per 100,000 people'), _('Per 100,000 people'),
                          pgettext_lazy('measured in', 'vehicles per 100,000 people')),
    ('suspects', 'all'): (_('Suspects per 100,000 people'), _('Per 100,000 people'),
                          pgettext_lazy('measured in', 'suspects per 100,000 people')),
    ('firearms', 'all'): (_('Firearms seized per 100,000 people'), _('Per 100,000 people'),
                          pgettext_lazy('measured in', 'firearms per 100,000 people')),
    ('prisoners', 'all'): (_('Prisoners per 100,000 people'), _('Per 100,000 people'),
                           pgettext_lazy('measured in', 'prisoners per 100,000 people')),
}
POPULATION_NOTE = _('Our calculation, with the World Bank\'s population: the UN\'s World Population Prospects.')
DEATHS_NOTE = _('Death certificates are coded with ICD-9 until 1995 and with ICD-10 from 1996. The latest year is '
                'preliminary.')
POLICE_NOTE = _('The line starts in the first year every state sent these figures: before, some sent zeros.')


def counted(key, title, summary, source, what, per='all', note='', rate_note='', better='lower', states_note='',
            extra=(), states_source=None):
    """A kind of crime with a rate per 100,000 people (or women, or people aged 15 to 29) and a count of `what`
    (a key of COUNTED). `rate_note` says whose population the rate divides by; `extra` adds measures after the two.
    """
    label, short, unit = RATES[what, per]
    count_label, count_short, count_unit = COUNTED[what]
    return Crime(key, title, summary, (
        Series('rate', label, 'per_100k', better=better, log_scale=True, short=short, measured_in=unit,
               note=joined(note, rate_note)),
        Series('count', count_label, 'count' if what in ('cases', 'vehicles', 'firearms') else 'people', better=better,
               log_scale=True, short=count_short, measured_in=count_unit, note=note),
        *extra,
    ), source, states_note, states_source)


def brazil(key, title, summary, source, what, per='all', note='', better='lower', states_note=''):
    """A kind of crime in Brazil: its rate (on the World Bank's population) and its count."""
    note = joined(note, {SIM: DEATHS_NOTE, SINESP: POLICE_NOTE}.get(source, ''))
    return counted(key, title, summary, source, what, per, note, POPULATION_NOTE, better, states_note)


HIDDEN = _('Since 2019 many more violent deaths are recorded without saying whether they were homicides, so some '
           'homicides are missing from the count: see Violent deaths of unknown intent.')

BRAZIL = [
    brazil('homicides', _('Homicides'),
           _('Deaths from assault, and from the police and other legal interventions, as death certificates record them.'),
           SIM, 'deaths', note=HIDDEN),
    brazil('firearm-homicides', _('Firearm homicides'),
           _('Deaths from assault with a firearm (ICD-10 X93 to X95). Killings by the police are not included.'),
           SIM, 'deaths', note=joined(_('Before 1996, ICD-9 also counts assaults with explosives.'), HIDDEN)),
    brazil('women-killed', _('Women killed'),
           _('Women and girls who died from assault or legal intervention.'),
           SIM, 'deaths', per='women', note=HIDDEN),
    brazil('femicide', _('Femicide'),
           _('Women killed for being women, as the law has defined femicide since 2015.'),
           SINESP, 'victims', per='women'),
    brazil('women-killed-at-home', _('Women killed at home'),
           _('Women and girls who died from assault in a home, as death certificates record the place.'),
           SIM, 'deaths', per='women'),
    brazil('young-people-killed', _('Young people killed'),
           _('People aged 15 to 29 who died from assault or legal intervention.'),
           SIM, 'deaths', per='young', note=HIDDEN),
    brazil('police-killings', _('Killed by the police'),
           _('People killed by the police and other agents of the state.'),
           SINESP, 'victims'),
    brazil('officers-killed', _('Police officers killed'),
           _('Police officers and other agents of the state who were killed.'),
           SINESP, 'victims'),
    brazil('robbery-murder', _('Robbery with murder'),
           _('Victims killed in a robbery (latrocínio).'),
           SINESP, 'victims'),
    brazil('attempted-homicide', _('Attempted homicide'),
           _('Victims of attempted homicide.'),
           SINESP, 'victims'),
    brazil('rape', _('Rape'),
           _('Victims of rape, including rape of a vulnerable person, such as a child under 14.'),
           SINESP, 'victims',
           note=_('The count follows how many victims report to the police, not only how many rapes there are.')),
    brazil('vehicle-robbery', _('Vehicle robbery'),
           _('Vehicles taken by force or threat.'),
           SINESP, 'cases'),
    brazil('vehicle-theft', _('Vehicle theft'),
           _('Vehicles stolen without force or threat.'),
           SINESP, 'cases'),
    brazil('drug-trafficking', _('Drug trafficking'),
           _('Police reports of drug trafficking.'),
           SINESP, 'cases',
           note=joined(POLICE_CHECKS, _('In 2020 a state left months empty, so the year is missing.')), better=''),
    brazil('firearms-seized', _('Firearms seized'),
           _('Firearms the police seized.'),
           SINESP, 'firearms', note=_('More seizures can mean more weapons, or more police work.'), better=''),
    brazil('prison', _('Prison population'),
           _('People held in prisons and police cells at the end of the year. People under house arrest are not counted.'),
           PRISONS, 'prisoners',
           note=_('From 2020 people in the open regime who stay at home are counted apart, and many prisoners were '
                  'released in the pandemic: the fall that year mixes the two. Police cells are counted unevenly.'),
           better='', states_note=_('By state: the people in each state\'s prisons, without police cells or federal '
                                    'prisons, from 2016.')),
    brazil('unknown-intent', _('Violent deaths of unknown intent'),
           _('Deaths from injuries whose certificate does not say whether they were an accident, a suicide or a homicide.'),
           SIM, 'deaths',
           note=_('They rose from 2019. The Atlas da Violência counts many of them as hidden homicides.'), better=''),
]

# ---------- France: the Interior Ministry's police and gendarmerie records (SSMSI), from 2016 ----------
# Licence Ouverte 2.0: free to reuse, naming the source and its update date.
LICENCE_OUVERTE = Licence('Licence Ouverte 2.0', 'https://www.etalab.gouv.fr/licence-ouverte-open-licence/')
SSMSI = Source('Ministère de l\'Intérieur, SSMSI, bases statistiques de la délinquance enregistrée (juillet 2026) and '
               'base des séries chronologiques (octobre 2026)',
               'https://www.data.gouv.fr/datasets/bases-statistiques-communale-departementale-et-regionale-de-la-'
               'delinquance-enregistree-par-la-police-et-la-gendarmerie-nationales', '2026-10-14', LICENCE_OUVERTE)
PPSMJ = Source('Ministère de la Justice, DGAP, Séries statistiques des personnes placées sous main de justice 1980–2026',
               'https://www.justice.gouv.fr/series-statistiques-personnes-placees-main-justice-1', '2026-02-28')
INSEE_NOTE = _('Our calculation, with INSEE\'s population estimates: the average of 1 January of the year and of the next.')
SSMSI_NOTE = _('The SSMSI\'s own figure for the whole country, from 2016, when it began to compile its bases.')


def france(key, title, summary, what, note='', better='lower', states_note=''):
    """A kind of crime in France: its rate per 100,000 people, on INSEE's population, and its count."""
    return counted(key, title, summary, SSMSI, what, note=joined(note, SSMSI_NOTE), rate_note=INSEE_NOTE, better=better,
                   states_note=states_note)


REPORTING = _('The count follows how many victims report to the police, not only how many crimes there are.')

FRANCE = [
    france('homicides', _('Homicides'),
           _('People killed on purpose, including in terrorist attacks, and deaths from assault.'), 'victims',
           note=_('From 2008 to 2015 the SSMSI\'s corrected national series, which could not set attack victims apart.')),
    france('attempted-homicide', _('Attempted homicide'), _('Victims of attempted homicide.'), 'victims'),
    france('domestic-violence', _('Physical violence in the family'),
           _('Victims of physical violence by a partner, a former partner or a relative, of every age.'), 'victims',
           note=joined(_('The SSMSI redefined these series in 2025, back to 2016, to count victims of every age.'),
                       REPORTING)),
    france('assault', _('Physical violence outside the family'),
           _('Victims of physical violence by someone who is not a partner or a relative.'), 'victims',
           note=joined(_('The SSMSI redefined these series in 2025, back to 2016, to count victims of every age.'),
                       REPORTING)),
    france('sexual-violence', _('Sexual violence'),
           _('Victims of rape, sexual assault and sexual harassment.'), 'victims', note=REPORTING),
    france('armed-robbery', _('Armed robbery'), _('Thefts with a firearm or another weapon, attempts included.'), 'cases'),
    france('robbery', _('Robbery without a weapon'), _('Thefts with violence but without a weapon, attempts included.'),
           'cases'),
    france('theft', _('Theft from people without violence'),
           _('Victims of theft without violence, such as pickpocketing and bag snatching, who made a complaint.'),
           'victims'),
    france('burglary', _('Domestic burglary'),
           _('Break-ins into main and second homes, attempts included.'), 'cases'),
    france('vehicle-theft', _('Vehicle theft'), _('Cars, motorcycles and other vehicles stolen, attempts included.'),
           'vehicles'),
    france('theft-from-vehicles', _('Theft from vehicles'), _('Vehicles broken into to steal what was inside.'), 'vehicles'),
    france('vehicle-parts-theft', _('Theft of vehicle parts'), _('Vehicles whose parts or accessories were stolen.'),
           'vehicles'),
    france('criminal-damage', _('Criminal damage'), _('Damaging or destroying other people\'s property on purpose.'), 'cases'),
    france('drug-use', _('Drug use'),
           _('People the police registered for using illegal drugs, including those who paid a fixed fine.'), 'suspects',
           note=POLICE_CHECKS, better=''),
    france('drug-trafficking', _('Drug trafficking'), _('People the police registered for trafficking drugs.'), 'suspects',
           note=POLICE_CHECKS, better=''),
    france('fraud', _('Fraud'), _('Victims of fraud and of the misuse of payment cards and cheques.'), 'victims',
           note=_('Counted where the victim lives.')),
    counted('prison', _('Prison population'),
            _('People held in prison on 1 January of the following year.'), PPSMJ, 'prisoners',
            note=_('Counted on 1 January of the next year. People under electronic monitoring or otherwise outside prison '
                   'are not included.'),
            rate_note=INSEE_NOTE, better='',
            extra=(Series('occupancy', _('Occupancy'), 'percent', better='lower',
                          measured_in=pgettext_lazy('measured in', '% of the prisons\' capacity'),
                          note=_('Prisoners per 100 places, as the ministry counts the prisons\' capacity.')),)),
]


# ---------- United States: the FBI's estimated crimes, from 1979 ----------
FBI = Source('FBI, Crime Data Explorer, estimated crimes 1979–2025 (Summary Reporting System)',
             'https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/downloads', '2026-08-01')
FBI_NOTE = _('Our calculation, with the population the FBI divides by.')
ESTIMATES = _('The FBI estimates the crimes of the police agencies that did not report. Since 2021 the police report '
              'through a new system, and fewer agencies reported in 2021, so that year\'s figures rest more on estimates.')
RAPE_2013 = _('In 2013 the FBI widened what counts as rape, to any penetration without consent, of anyone.')


def usa(key, title, summary, note='', better='lower'):
    """A kind of crime in the United States: offences known to the police, their rate and count, nation and states."""
    return counted(key, title, summary, FBI, 'cases', note=joined(note, ESTIMATES), rate_note=FBI_NOTE, better=better)


UNITED_STATES = [
    usa('violent', _('Violent crime'),
        _('Murder, rape, robbery and aggravated assault, as the FBI adds them up.'),
        note=joined(RAPE_2013, _('The total counts rape by the old definition until 2012 and by the new one from 2013.'))),
    usa('homicides', _('Murder'),
        _('Murder and non-negligent manslaughter: the wilful killing of one person by another, as the police record it.'),
        note=_('The 2001 figure leaves out the victims of the September 11 attacks.')),
    usa('rape', _('Rape'),
        _('Penetration without the consent of the victim, the FBI\'s definition since 2013.'),
        note=joined(RAPE_2013, _('The line starts in 2013; the older series is in the next tab.'))),
    usa('rape-legacy', _('Rape, old definition'),
        _('Forcible rape of a woman, the FBI\'s definition until 2016.'),
        note=joined(RAPE_2013, _('The FBI stopped counting by the old definition after 2016.'))),
    usa('robbery', _('Robbery'), _('Taking something by force or threat of force.')),
    usa('aggravated-assault', _('Aggravated assault'),
        _('An attack to inflict severe injury, usually with a weapon.')),
    usa('property', _('Property crime'), _('Burglary, larceny-theft and motor vehicle theft, as the FBI adds them up.')),
    usa('burglary', _('Burglary'), _('Unlawful entry to commit a theft or another crime, attempts included.')),
    usa('larceny', _('Larceny-theft'),
        _('Theft without force or fraud: shoplifting, pickpocketing, bicycles, things taken from cars and more.')),
    usa('vehicle-theft', _('Motor vehicle theft'), _('Cars, trucks and motorcycles stolen, attempts included.')),
]

# ---------- Italy: crimes reported by the police, from Istat, from 2006 ----------
CC_BY = Licence('CC BY 4.0', 'https://creativecommons.org/licenses/by/4.0/')
ISTAT = Source('Istat, Delitti denunciati dalle forze di polizia all\'autorità giudiziaria (Ministero dell\'Interno data)',
               'https://esploradati.istat.it/databrowser/#/it/dw/categories/IT1,DATAWAREHOUSE,1.0/JUS/JUS_PS', '2026-04-15', CC_BY)
ISTAT_VICTIMS = Source('Istat, Autori e vittime dei delitti denunciati dalle forze di polizia',
                       'https://esploradati.istat.it/databrowser/#/it/dw/categories/IT1,DATAWAREHOUSE,1.0/JUS/JUS_PS',
                       '2025-12-19', CC_BY)
DAP = Source('Ministero della Giustizia, Dipartimento dell\'amministrazione penitenziaria, Detenuti presenti 1991–2026',
             'https://www.giustizia.it/giustizia/it/mg_1_14_1.page?contentId=SST165666', '2026-06-30')
ISTAT_POPULATION = _('Our calculation, with Istat\'s residents on 1 January: the average of the year and of the next.')
SDI = _('The police enter crimes in the Interior Ministry\'s system as they record them; Istat extracts them a few months '
        'after the year ends. The years before 2004 were counted on paper and do not compare.')


def italy(key, title, summary, note='', better='lower', states_note=''):
    """A kind of crime in Italy: crimes reported by the police to the courts, Istat's rate and the count, by province."""
    return counted(key, title, summary, ISTAT, 'cases', note=joined(note, SDI), rate_note=ISTAT_POPULATION, better=better,
                   states_note=states_note)


ITALY = [
    italy('all', _('All reported crimes'), _('Every crime the police reported to the courts, from theft to murder.')),
    italy('homicides', _('Homicides'), _('People killed on purpose, attempts not included.')),
    italy('attempted-homicide', _('Attempted homicide'), _('Attempts to kill someone.')),
    counted('women-killed', _('Women killed'), _('Women and girls killed on purpose, as the police recorded the victims.'),
            ISTAT_VICTIMS, 'victims', per='women', rate_note=POPULATION_NOTE,
            note=_('Istat gives the victims of homicide by sex from 2007.')),
    italy('sexual-violence', _('Sexual violence'), _('Rape and sexual assault, as the law has defined them since 1996.'),
          note=REPORTING),
    italy('bodily-harm', _('Bodily harm'), _('Injuring someone on purpose (lesioni dolose).'), note=REPORTING),
    italy('battery', _('Battery'), _('Hitting someone without leaving an injury (percosse).'), note=REPORTING),
    italy('threats', _('Threats'), _('Threatening someone with harm (minacce).'), note=REPORTING),
    italy('robbery', _('Robbery'), _('Taking something by force or threat, anywhere.')),
    italy('street-robbery', _('Street robbery'), _('Robberies on the public road.')),
    italy('theft', _('Theft'), _('Every theft, from pickpocketing to car theft.')),
    italy('burglary', _('Domestic burglary'), _('Thefts from homes.')),
    italy('pickpocketing', _('Pickpocketing'), _('Thefts by sleight of hand, from pockets and bags.')),
    italy('bag-snatching', _('Bag snatching'), _('Thefts by snatching something from a person (scippi).')),
    italy('shop-theft', _('Shop theft'), _('Thefts from shops and businesses.')),
    italy('car-theft', _('Car theft'), _('Cars stolen.')),
    italy('extortion', _('Extortion'), _('Forcing someone to pay or hand something over by threat.')),
    italy('fraud', _('Fraud'), _('Swindles and computer fraud (truffe e frodi informatiche).')),
    italy('criminal-damage', _('Criminal damage'), _('Damaging other people\'s property on purpose.')),
    italy('drugs', _('Drug offences'), _('Offences against the drug law, from possession for sale to trafficking.'),
          note=POLICE_CHECKS, better=''),
    italy('mafia-association', _('Mafia association'),
          _('Belonging to a mafia-type organisation (article 416-bis of the Criminal Code).'),
          note=_('Found by investigations, so the count says as much about police work as about the mafias.'), better=''),
    counted('prison', _('Prison population'), _('People held in prison on 31 December.'), DAP, 'prisoners',
            note=_('Counted on 31 December. The ministry allows reuse of its figures for non-commercial ends.'),
            rate_note=ISTAT_POPULATION, better=''),
]

# ---------- United Kingdom: England and Wales, the police's recorded crime from 2002, through the ONS ----------
OGL = Licence('Open Government Licence v3.0', 'https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/')
ONS_RECORDED = Source('Office for National Statistics, Crime in England and Wales: appendix tables, year ending June 2026, '
                      'Table A5a (police recorded crime from the Home Office)',
                      'https://www.ons.gov.uk/peoplepopulationandcommunity/crimeandjustice/datasets/'
                      'crimeinenglandandwalesappendixtables', '2026-10-22', OGL)
ONS_KNIFE = Source('Office for National Statistics, Offences involving the use of weapons: data tables, year ending '
                   'March 2026, Table 21 (police recorded crime from the Home Office)',
                   'https://www.ons.gov.uk/peoplepopulationandcommunity/crimeandjustice/datasets/'
                   'offencesinvolvingtheuseofweaponsdatatables', '2026-10-22', OGL)
ONS_HOMICIDE = Source('Office for National Statistics, Appendix tables: homicide in England and Wales, year ending March '
                      '2025, Table 1 (Home Office Homicide Index)',
                      'https://www.ons.gov.uk/peoplepopulationandcommunity/crimeandjustice/datasets/'
                      'appendixtableshomicideinenglandandwales', '2026-02-05', OGL)
MOJ = Source('Ministry of Justice, Offender management statistics quarterly: January to March 2026, annual prison '
             'population, Table 1.A.3',
             'https://www.gov.uk/government/statistics/offender-management-statistics-quarterly-january-to-march-2026',
             '2026-07-30', OGL)
ONS_NOTE = _('Our calculation, with the ONS\'s mid-year estimate of England and Wales for the year\'s first calendar year.')
FISCAL_NOTE = _('England and Wales only. The police count years from April to March: a year here is the one most of '
                'its months fall in.')
RECORDING = _('Nothing before 2002 compares, when a national recording standard began. '
              'After an inspection in 2014 the police recorded crimes more fully, which raised violence, sexual and '
              'public order offences from then on.')


def england(key, title, summary, note='', better='lower', source=ONS_RECORDED):
    """A kind of crime in England and Wales: the police\'s recorded offences, their rate and count."""
    return counted(key, title, summary, source, 'cases', note=joined(note, FISCAL_NOTE), rate_note=ONS_NOTE, better=better)


UNITED_KINGDOM = [
    england('all', _('All recorded crime'),
            _('Every offence the police recorded, except fraud and computer misuse, which are counted apart.'), RECORDING),
    england('homicides', _('Homicide'),
            _('Murder, manslaughter and infanticide, as the Home Office\'s Homicide Index still records them once the '
              'courts have ruled.'),
            _('The index gives the offences still recorded as homicide from 1967, by calendar year until 1996. '
              'Single events weigh on some years: Harold Shipman\'s 173 victims in 2002, Hillsborough\'s 96 in 2016.'),
            source=ONS_HOMICIDE),
    england('violence', _('Violence against the person'),
            _('Every offence against the person, from harassment to murder, with or without injury.'), RECORDING),
    england('violence-with-injury', _('Violence with injury'), _('Assaults and woundings that left an injury.'), RECORDING),
    england('sexual-offences', _('Sexual offences'), _('Rape and every other sexual offence.'), joined(RECORDING, REPORTING)),
    england('rape', _('Rape'), _('Rape, as the Sexual Offences Act 2003 defines it since May 2004.'),
            joined(RECORDING, REPORTING)),
    england('knife', _('Knife crime'),
            _('Selected offences in which a knife or a sharp instrument was used: homicide, attempted murder, threats to '
              'kill, assaults, robbery, rape and sexual assault.'),
            _('The line starts in 2019, when a new method of counting began. '
              'The Metropolitan Police corrected its counting from April 2024 without revising earlier years.'),
            source=ONS_KNIFE),
    england('robbery', _('Robbery'), _('Taking something by force or threat of force.'), RECORDING),
    england('theft', _('Theft offences'), _('Every theft, from shoplifting to burglary and vehicle theft.'), RECORDING),
    england('burglary', _('Burglary'), _('Breaking into homes and other buildings.'), RECORDING),
    england('vehicle-offences', _('Vehicle offences'), _('Vehicles stolen, broken into or interfered with.'), RECORDING),
    england('theft-from-person', _('Theft from the person'), _('Pickpocketing and bag snatching.'), RECORDING),
    england('bicycle-theft', _('Bicycle theft'), _('Bicycles stolen.'), RECORDING),
    england('shoplifting', _('Shoplifting'), _('Thefts from shops.'), RECORDING),
    england('criminal-damage', _('Criminal damage and arson'), _('Damaging or burning other people\'s property.'), RECORDING),
    england('drugs', _('Drug offences'), _('Possessing, supplying and trafficking illegal drugs.'),
            joined(POLICE_CHECKS, RECORDING), better=''),
    england('weapons', _('Possession of weapons'), _('Carrying knives, firearms and other weapons.'),
            joined(POLICE_CHECKS, RECORDING), better=''),
    england('public-order', _('Public order offences'),
            _('Riot, violent disorder, affray and causing fear, alarm or distress.'),
            joined(RECORDING, _('From May 2023 the police no longer record causing harassment, alarm or distress, about '
                                'an eighth of these offences before.')), better=''),
    counted('prison', _('Prison population'),
            _('People in prison in England and Wales: the average of the twelve month-end counts of the year.'), MOJ,
            'prisoners', note=_('England and Wales only.'), rate_note=ONS_NOTE, better=''),
]

# ---------- Austria: the Bundeskriminalamt's police crime statistics (PKS), from 2010 ----------
# The Bundeskriminalamt allows reuse with the source named, for non-commercial ends (its Impressum).
BK = Source('Bundeskriminalamt, Polizeiliche Kriminalstatistik: Kriminalitätsbericht – Statistik und Analyse 2010–2023, '
            'PKS 2024 and 2025', 'https://www.bundeskriminalamt.at/501/', '2026-03-31')
STATISTIK_AUSTRIA = Source('Statistik Austria, Verurteilungsstatistik, Verurteilungen nach ausgewählten Abschnitten des '
                           'StGB seit 1947',
                           'https://www.statistik.at/statistiken/bevoelkerung-und-soziales/kriminalitaet-und-sicherheit/'
                           'verurteilungs-und-wiederverurteilungsstatistik', '2026-06-02', CC_BY)
AUSTRIA_NOTE = _('Our calculation, with Statistik Austria\'s population at the start of the year: the average of the year '
                 'and of the next. The Bundeskriminalamt\'s own rates divide by another date\'s population.')
STGB_2016 = _('A reform of the Criminal Code in 2016 split some offences into misdemeanours and felonies; both are added up.')
PKS_NOTE = _('From the yearly Kriminalitätsbericht to 2023; the PKS brochures give 2024 and 2025 for some kinds only.')
CLEARANCE_AT = _('The share of cases in which the police identified a suspect, as the Bundeskriminalamt gives it.')


def pks_at(key, title, summary, note='', better='lower', clearance=True, completed=False, states_note=''):
    """A kind of crime in Austria: cases per 100,000 people, cases and the clearance rate, by Bundesland where given.
    `completed` adds the cases without attempts (murder).
    """
    measures = [
        Series('rate', _('Cases per 100,000 people'), 'per_100k', better=better, log_scale=True, short=_('Per 100,000 people'),
               measured_in=pgettext_lazy('measured in', 'cases per 100,000 people'), note=joined(note, PKS_NOTE, AUSTRIA_NOTE)),
        Series('cases', _('Recorded cases'), 'count', better=better, log_scale=True, short=_('Cases'),
               measured_in=pgettext_lazy('measured in', 'cases a year'), note=joined(note, PKS_NOTE)),
    ]
    if completed:
        measures.append(Series('completed', _('Completed cases, without attempts'), 'count', better=better, log_scale=True,
                               short=_('Completed'), measured_in=pgettext_lazy('measured in', 'cases a year'),
                               note=joined(note, COMPLETED_NOTE)))
    if clearance:
        measures.append(Series('clearance', _('Clearance rate'), 'percent', better='higher',
                               measured_in=pgettext_lazy('measured in', '% of cases'), note=joined(note, CLEARANCE_AT)))
    return Crime(key, title, summary, tuple(measures), BK, states_note)


def convictions(key, title, summary, note=''):
    """Convictions by Austria\'s courts in a group of offences, since 1947: per 100,000 people and the count."""
    breaks = _('The Criminal Code of 1975 regrouped the offences, diversion kept many adults out of court from 2000, '
               'and from 2012 the courts themselves name the decisive offence: each changed the counts.')
    return Crime(key, title, summary, (
        Series('convictions_rate', _('Convictions per 100,000 people'), 'per_100k', better='', log_scale=True,
               short=_('Per 100,000 people'), measured_in=pgettext_lazy('measured in', 'convictions per 100,000 people'),
               note=joined(note, breaks, AUSTRIA_NOTE)),
        Series('convictions', _('Convictions'), 'count', better='', log_scale=True,
               measured_in=pgettext_lazy('measured in', 'convictions a year'), note=joined(note, breaks)),
    ), STATISTIK_AUSTRIA)


AUSTRIA = [
    pks_at('total', _('All recorded offences'),
           _('Every offence the police recorded, under the Criminal Code and every other law.')),
    pks_at('violent-crime', _('Violent crime'),
           _('Murder, bodily harm, robbery, rape and other violent offences, as the Bundeskriminalamt adds them up.'),
           _('The brochures give this total from 2016.')),
    pks_at('murder', _('Murder'), _('Murder (§ 75 of the Criminal Code), attempts included: most cases are attempts.'),
           STGB_2016, completed=True),
    pks_at('assault', _('Bodily harm'), _('Injuring someone on purpose (§ 83).')),
    pks_at('serious-assault', _('Serious bodily harm'), _('Injuries that are serious or leave lasting harm (§ 84).'), STGB_2016),
    pks_at('coercion', _('Coercion'), _('Forcing someone to do or suffer something by force or threat (§ 105).')),
    pks_at('threat', _('Dangerous threats'), _('Threatening someone to frighten them (§ 107).')),
    pks_at('rape', _('Rape'), _('Rape (§ 201).'), REPORTING),
    pks_at('robbery', _('Robbery'), _('Taking something by force or threat, plain and aggravated (§§ 142 and 143).')),
    pks_at('property-crime', _('Property crime'),
           _('Theft, burglary, fraud and other offences against property, as the Bundeskriminalamt adds them up.'),
           _('The brochures give this total from 2016.')),
    pks_at('theft', _('Theft'), _('Simple theft (§ 127).')),
    pks_at('burglary', _('Burglary'), _('Theft by breaking in, anywhere (§ 129).'), STGB_2016),
    pks_at('home-burglary', _('Burglary of homes'), _('Break-ins into flats and houses, attempts included.'),
           _('The brochures give this from 2016.'), clearance=False),
    pks_at('vehicle-theft', _('Vehicle theft'), _('Cars and other motor vehicles stolen.'),
           _('The brochures give this from 2016.')),
    pks_at('fraud', _('Fraud'), _('Fraud, plain and serious (§§ 146 and 147).')),
    pks_at('computer-fraud', _('Computer fraud'), _('Fraud by manipulating data processing (§ 148a).')),
    pks_at('internet-fraud', _('Internet fraud'), _('Fraud committed over the internet, as the Bundeskriminalamt counts it.'),
           _('The brochures give this from 2016.')),
    pks_at('cybercrime', _('Cybercrime'), _('Attacks on computers and data, in the narrow sense.'),
           _('The brochures give this from 2016.')),
    pks_at('criminal-damage', _('Criminal damage'), _('Damaging other people\'s property (§§ 125 and 126).')),
    pks_at('drugs', _('Drug offences'), _('Offences against the Narcotic Substances Act (SMG).'),
           joined(POLICE_CHECKS, _('From 2010 to 2013 the Kriminalitätsbericht\'s figures, by Land; from 2016 the '
                                   'brochure\'s, for the whole country. 2014 and 2015 are missing.')), better=''),
    convictions('convictions', _('Convictions'), _('People convicted by the courts, for any offence.')),
    convictions('convictions-violent', _('Convictions for violent offences'),
                _('Convictions for offences against life and limb.')),
    convictions('convictions-property', _('Convictions for property offences'),
                _('Convictions for offences against other people\'s property.')),
    convictions('convictions-sexual', _('Convictions for sexual offences'),
                _('Convictions for offences against sexual integrity and self-determination.'),
                _('Called offences against morality until May 2004.')),
]

CRIMES = {'DEU': GERMANY, 'BRA': BRAZIL, 'FRA': FRANCE, 'USA': UNITED_STATES, 'ITA': ITALY, 'GBR': UNITED_KINGDOM,
          'AUT': AUSTRIA}  # country code -> its kinds of crime, in the order of the page's tabs

# The title of the map under a kind of crime's chart. Each country's regions take their own word.
STATES_TITLE = {
    'DEU': pgettext_lazy('Germany', 'By state'),
    'BRA': pgettext_lazy('Brazil', 'By state'),
    'FRA': _('By département'),
    'USA': pgettext_lazy('United States', 'By state'),
    'ITA': _('By province'),
    'AUT': pgettext_lazy('Austria', 'By state'),
}
# What one state is called, over the table's column of states, and the state in the middle, where the map's colours turn.
STATE_WORDS = {
    'DEU': (pgettext_lazy('Germany', 'State'), pgettext_lazy('Germany', 'Median state')),
    'BRA': (pgettext_lazy('Brazil', 'State'), pgettext_lazy('Brazil', 'Median state')),
    'FRA': (_('Département'), _('Median département')),
    'USA': (pgettext_lazy('United States', 'State'), pgettext_lazy('United States', 'Median state')),
    'ITA': (_('Province'), _('Median province')),
    'AUT': (pgettext_lazy('Austria', 'State'), pgettext_lazy('Austria', 'Median state')),
}
# What the map says of the states' numbers.
STATES_NOTE = {
    'DEU': _('A Land counts the crimes committed in it, and many suspects and victims live elsewhere: commuters and '
             'visitors raise the rates of the city-states, Berlin, Hamburg and Bremen, as the BKA points out. '
             'From 2024 the rates are on the 2022 census, which alone moved a Land\'s rate by between −1.9% and +3.3%. '
             'A case solved in a later year counts as solved then, so a Land with few cases can show a clearance rate '
             'above 100%.'),
    'BRA': _("A state's rate divides by IBGE's projection of its people (Revisão 2024), which starts in 2000. "
             'Deaths count in the state where the victim lived, police records in the state that recorded them.'),
    'FRA': _('A département counts the crimes recorded in it, except fraud, counted where the victim lives. '
             'Paris and other places with many visitors and commuters get higher rates for it. '
             'The five overseas départements are drawn in a column west of Brittany, not to scale.'),
    'USA': _('The FBI estimates each state\'s crimes from the agencies that reported. In 2021 many agencies in some '
             'states, among them California, Florida, New York and Pennsylvania, did not report, so those estimates rest '
             'on less. Only limited data were available for Florida and North Dakota in 2025.'),
    'ITA': _('A province counts the crimes recorded in it. Istat keeps Sardinia\'s four provinces at their borders of '
             '2001, so the map draws them that way, and Cagliari\'s rate counts Sud Sardegna\'s people.'),
    'AUT': _('A Land counts the crimes recorded in it: visitors and commuters raise Vienna\'s rates. '
             'The Länder come from each year\'s Kriminalitätsbericht, to 2023; the 2024 and 2025 totals from the '
             'brochures.'),
}

# What the page says of a country's crime numbers as a whole, under the chart.
ABOUT = {
    'DEU': _('The police count a crime when they hand the case to the prosecutors, so a year holds some crimes committed '
             'earlier. They count only the crimes they learn of: many are never reported. '
             'Traffic offences and offences against the state are counted elsewhere.'),
    'BRA': _('Deaths come from death certificates, which the Ministry of Health collects, by where the victim lived. '
             'The police series come from the states\' police records, which the Ministry of Justice collects. '
             'Both count only what is recorded.'),
    'FRA': _('The series come from the records of the police and the gendarmerie, which the Interior Ministry\'s '
             'statistical service compiles since 2016. They count only what is recorded: many crimes are never reported, '
             'and a change in how people report moves the lines. Prisoners come from the Ministry of Justice.'),
    'USA': _('The series are the FBI\'s estimates of the crimes known to the police, built from what the local police '
             'agencies report each year. They count only what is recorded: many crimes are never reported.'),
    'ITA': _('The series are the crimes the police reported to the courts, which Istat publishes from the Interior '
             'Ministry\'s system. They count only what is recorded: many crimes are never reported. '
             'Prisoners come from the Ministry of Justice.'),
    'GBR': _('The series cover England and Wales: Scotland and Northern Ireland count crime under their own rules, so '
             'the United Kingdom has no single figure. They are the offences the police recorded, which the Home Office '
             'collects and the ONS publishes. They count only what is recorded: many crimes are never reported, and how '
             'fully the police record changed over the years.'),
    'AUT': _('The series are the offences the police recorded, from the Bundeskriminalamt\'s yearly reports. '
             'They count only what is recorded: many crimes are never reported. Convictions come from Statistik Austria.'),
}


def metrics(country):
    """The country's kinds of crime that have data, in the order of CRIMES; none while settings.CRIME_TAB is off."""
    if not settings.CRIME_TAB:
        return []
    found = set(CrimeYear.objects.filter(country=country).values_list('crime', flat=True).distinct())
    return [crime for crime in CRIMES.get(country.iso3, []) if crime.key in found]


def values(crime, series, country):
    """One measure of one kind of crime in the whole country, by year: {year: value}."""
    rows = CrimeYear.objects.filter(country=country, state=None, crime=crime.key, measure=series.field)
    return dict(rows.values_list('year', 'value'))


def state_flag(code):
    """The address of a state's flag, media/flags/states/<code>.svg, or None where the site has none.
    Brazil's come from Wikimedia Commons (data/politics/brazil/state_flags.csv, tools/brazil_state_flags.py).
    """
    path = Path(settings.MEDIA_ROOT) / 'flags' / 'states' / f'{code}.svg'
    return f'{settings.MEDIA_URL}flags/states/{code}.svg' if path.exists() else None


def states(crime, series, country):
    """One measure of one kind of crime by state, as the map under its chart draws it; None where there are no states.

    `values` maps a state's code to its value in each of `years` (None where missing), as the world map's data does,
    and `countries` names each state, with its flag where the site has one.
    """
    rows = list(CrimeYear.objects.filter(country=country, crime=crime.key, measure=series.field, state__isnull=False)
                .values_list('state_id', 'year', 'value'))
    if not rows:
        return None
    years = sorted({year for _, year, _ in rows})
    values = {state.code: [None] * len(years) for state in State.objects.filter(country=country)}
    for code, year, value in rows:
        values[code][years.index(year)] = value
    return {
        'title': str(STATES_TITLE.get(country.iso3, '')),
        'stateLabel': str(STATE_WORDS[country.iso3][0]),
        'median': str(STATE_WORDS[country.iso3][1]),
        'years': years,
        'values': values,
        'countries': {state.code: {'name': state.local_name, 'flag': state_flag(state.code)}
                      for state in State.objects.filter(country=country)},
        'note': str(joined(STATES_NOTE.get(country.iso3, ''), crime.states_note)),
    }


def load(crime, source=None):
    """What the page cites for a kind of crime: its own source (or `source`), with the date pol_crime_year was last loaded.

    An unsaved EtlLoad, so the page's source line reads it like any metric's load. None before the first load.
    """
    source = source or crime.source
    last = EtlLoad.objects.filter(table_name=CrimeYear._meta.db_table).first()
    if last is None:
        return None
    return EtlLoad(table_name=last.table_name, source_name=source.name, source_url=source.url,
                   source_updated=source.updated, row_count=0, loaded_at=last.loaded_at)
