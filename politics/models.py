"""Who governed each country, and for which party. The ETL modules in providers/curated/ write these tables.

Political tables start with pol_ (see CLAUDE.md, Data design).
"""

from django.db import models

from geo.models import Country


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
