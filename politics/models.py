"""Who governed each country, for which party, and where expert surveys place its parties. The ETL modules in providers/curated/ write these tables.

Political tables start with pol_ (see CLAUDE.md, Data design).
"""

from django.db import models

from geo.models import Country, State


class Party(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE, db_column='iso3', related_name='+')
    abbreviation = models.CharField(max_length=20)
    name = models.CharField(max_length=200)
    color = models.CharField(max_length=7, help_text='Hex colour, from Wikipedia, lightened to read on the dark charts.')
    logo = models.CharField(max_length=200, blank=True, help_text='Path under MEDIA_ROOT, e.g. politics/brazil/pt.svg.')
    logo_source = models.URLField(max_length=500, blank=True)
    logo_licence = models.CharField(max_length=50, blank=True)
    logo_author = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = 'pol_party'
        ordering = ['country', 'abbreviation']
        constraints = [models.UniqueConstraint(fields=['country', 'abbreviation'], name='one_party_per_abbreviation')]
        verbose_name_plural = 'parties'

    def __str__(self):
        return f'{self.abbreviation} ({self.country_id})'


class Administration(models.Model):
    """One stretch in office of one leader under one party. A party change mid-term starts a new row."""

    country = models.ForeignKey(Country, on_delete=models.CASCADE, db_column='iso3', related_name='+')
    leader = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50, help_text='How charts label the leader, e.g. Lula.')
    role = models.CharField(max_length=50, help_text='e.g. President, Acting president, Military junta.')
    party = models.ForeignKey(Party, on_delete=models.SET_NULL, null=True, blank=True, help_text='Empty: no party.')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True, help_text='Empty: still in office.')
    notes = models.CharField(max_length=300, blank=True)
    source_url = models.URLField(max_length=500)

    class Meta:
        db_table = 'pol_administration'
        ordering = ['country', 'start_date']
        constraints = [models.UniqueConstraint(fields=['country', 'start_date'], name='one_administration_per_start')]

    def __str__(self):
        end = f'{self.end_date:%Y}' if self.end_date else 'today'
        return f'{self.leader} ({self.start_date:%Y}–{end})'


class PartyProfile(models.Model):
    """A party as the party compass and the seats in Congress show it. Many never held the presidency, so they are not in pol_party."""

    country = models.ForeignKey(Country, on_delete=models.CASCADE, db_column='iso3', related_name='+')
    key = models.CharField(max_length=30, help_text='Stable id, as in data/politics/<country>/party_profiles.csv.')
    abbreviation = models.CharField(max_length=30, help_text='How the page labels the party, e.g. PT or Novo.')
    name = models.CharField(max_length=200, help_text="The party's own name, in its country's language; party names are never translated.")
    color = models.CharField(max_length=7, help_text='Hex colour, lightened to read on the dark charts.')
    logo = models.CharField(max_length=200, blank=True, help_text='Path under MEDIA_ROOT; empty when no free logo exists.')
    logo_on_dark = models.CharField(max_length=200, blank=True, help_text='A copy of the logo with light ink, for dark grounds, where its own ink is too dark.')
    logo_source = models.URLField(max_length=500, blank=True)
    logo_licence = models.CharField(max_length=50, blank=True)
    logo_author = models.CharField(max_length=200, blank=True)
    position = models.CharField(max_length=60, blank=True, help_text="Where Wikipedia puts the party, e.g. 'centre|centre-right' for a range; empty where it gives none.")
    ideologies = models.CharField(max_length=300, blank=True, help_text="Its main ideologies on Wikipedia, ';'-separated keys of compass.IDEOLOGIES; empty for a group that is not a party.")
    views_source = models.URLField(max_length=500, help_text='The Wikipedia article the position and ideologies come from.')
    merged_into = models.CharField(max_length=100, blank=True, help_text='The party it merged into, if it no longer exists.')
    ended_year = models.PositiveSmallIntegerField(null=True, blank=True)
    congress = models.CharField(max_length=100, blank=True, help_text="The code(s) the houses' open data give the party or its group, ';'-separated where the houses differ.")

    class Meta:
        db_table = 'pol_party_profile'
        ordering = ['country', 'key']
        constraints = [models.UniqueConstraint(fields=['country', 'key'], name='one_party_profile_per_key')]

    def __str__(self):
        return f'{self.abbreviation} ({self.country_id})'


class PartyPosition(models.Model):
    """Where one expert survey places one party: 0 to 10 on the economic axis and on the social axis.

    An inferred place is not the survey's own: tools/party_positions.py estimated it, as `inferred` says.
    """

    party = models.ForeignKey(PartyProfile, on_delete=models.CASCADE, related_name='positions')
    survey = models.CharField(max_length=20, help_text='A key of politics.compass.SURVEYS.')
    name_at_survey = models.CharField(max_length=30, blank=True, help_text='The name the party had then, if it differs (PR, now PL).')
    economic = models.FloatField(help_text='0 left (an active state in the economy) to 10 right (a smaller one).')
    social = models.FloatField(help_text='0 progressive (expanded personal freedoms) to 10 conservative (order, tradition).')
    experts = models.PositiveIntegerField(help_text='The fewest experts behind the place; for a place inferred from the left-right scale, that scale\'s.')
    inferred = models.CharField(max_length=10, blank=True, help_text="Empty for the survey's own place; 'scale' or 'merger' for an inferred one.")
    inferred_from = models.CharField(max_length=100, blank=True, help_text='For a merger, the parties it came from, e.g. DEM, PSL.')
    economic_fit = models.FloatField(null=True, blank=True, help_text="For 'scale', the R² of the line the economic place was read off.")
    social_fit = models.FloatField(null=True, blank=True, help_text="For 'scale', the R² of the line the social place was read off.")

    class Meta:
        db_table = 'pol_party_position'
        ordering = ['survey', 'party']
        constraints = [models.UniqueConstraint(fields=['party', 'survey'], name='one_position_per_party_and_survey')]

    def __str__(self):
        return f'{self.party} in {self.survey}'


class Legislator(models.Model):
    """A member of one house of a country's parliament, with the party its source's data gives."""

    country = models.ForeignKey(Country, on_delete=models.CASCADE, db_column='iso3', related_name='+')
    member_id = models.CharField(max_length=20, help_text="The source's own id for the member.")
    name = models.CharField(max_length=200)
    party = models.CharField(max_length=60, help_text="The party's or group's code in the source's data, e.g. PL; empty for none.")
    state = models.CharField(max_length=2, help_text='The state the member represents, e.g. SP.')

    class Meta:
        abstract = True
        ordering = ['country', 'name']

    def __str__(self):
        return f'{self.name} ({self.party or "no party"})'


class Deputy(Legislator):
    class Meta(Legislator.Meta):
        db_table = 'pol_deputy'
        verbose_name_plural = 'deputies'


class Senator(Legislator):
    term_ends = models.PositiveSmallIntegerField(null=True, blank=True, help_text="The year the seat's term ends, e.g. 2031: a Brazilian senator sits for eight years. Empty where the house has no fixed terms, like Austria's Bundesrat.")

    class Meta(Legislator.Meta):
        db_table = 'pol_senator'


class Elected(Legislator):
    """A member elected to one house in the last general election, who takes office on 1 February of the next year."""

    house = models.CharField(max_length=10, help_text='A key of politics.congress.HOUSES.')
    elected_on = models.DateField()

    class Meta(Legislator.Meta):
        db_table = 'pol_elected'
        verbose_name_plural = 'elected'


class PartyLeftRight(models.Model):
    """Where political scientists place a party on one left-right scale, from 0, the far left, to 10, the far right."""

    party = models.OneToOneField(PartyProfile, on_delete=models.CASCADE, related_name='left_right')
    score = models.FloatField(help_text='The mean of the experts who placed the party.')
    experts = models.PositiveIntegerField(help_text='How many experts placed it; for a merger, the fewest behind its parties.')
    inferred_from = models.CharField(max_length=100, blank=True, help_text='For a party formed after the survey by a merger, the parties whose average it takes, e.g. PTB, Patriota.')

    class Meta:
        db_table = 'pol_party_left_right'
        ordering = ['score']

    def __str__(self):
        return f'{self.party}: {self.score:.2f}'



class NationalityPopulation(models.Model):
    """The people of each nationality living in a country on 31 December of a year.

    The row without a nationality is every foreign national together, the stateless and the unknown included.
    """

    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='+', help_text='The country they live in.')
    nationality = models.ForeignKey(Country, on_delete=models.CASCADE, null=True, blank=True, related_name='+',
                                    help_text='Empty for every foreign national together.')
    year = models.PositiveSmallIntegerField()
    source_name = models.CharField(max_length=100, help_text="The nationality's name in the source.")
    population = models.PositiveIntegerField()

    class Meta:
        db_table = 'pol_population_nationality'
        ordering = ['country', '-population']

    def __str__(self):
        return f'{self.country_id} {self.year}: {self.source_name}'


class Suspects(models.Model):
    """Crime suspects the police registered in one year, by nationality and kind of offence.

    The police count a suspect once for each kind of offence: one suspected of theft and of fraud counts in both.
    The row without a nationality is every foreign national together.
    """

    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='+', help_text='The country whose police counted them.')
    nationality = models.ForeignKey(Country, on_delete=models.CASCADE, null=True, blank=True, related_name='+',
                                    help_text='Empty for every foreign national together.')
    year = models.PositiveSmallIntegerField()
    offence = models.CharField(max_length=6, help_text='The key of the police crime statistics, e.g. 510000 for fraud; ------ is every offence.')
    suspects = models.PositiveIntegerField()

    class Meta:
        db_table = 'pol_suspects_nationality_offence'
        verbose_name_plural = 'suspects'

    def __str__(self):
        return f'{self.country_id} {self.year} {self.offence}: {self.nationality_id or "foreign"}'


class CrimeYear(models.Model):
    """One measure of one kind of crime in a country, or in one of its states, in one year: recorded cases, cases per
    100,000 people, and the like. A row without a state is the whole country.

    politics/crime_series.py names each country's kinds of crime and measures, and their sources.
    """

    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='+')
    state = models.ForeignKey(State, on_delete=models.CASCADE, null=True, blank=True, related_name='+',
                              help_text='Empty for the whole country.')
    year = models.PositiveSmallIntegerField()
    crime = models.CharField(max_length=40, help_text="The kind of crime: a key of the country's list in politics/crime_series.py.")
    measure = models.CharField(max_length=20, help_text="What is counted: a series field of that kind of crime, e.g. cases or rate.")
    value = models.FloatField()

    class Meta:
        db_table = 'pol_crime_year'
        constraints = [models.UniqueConstraint(fields=['country', 'state', 'crime', 'measure', 'year'], nulls_distinct=False,
                                               name='pol_crime_year_unique')]

    def __str__(self):
        return f'{self.country_id} {self.year} {self.crime} {self.measure}: {self.value}'
