"""World War II, in the conflicts database. Each conflict has its own PostgreSQL schema; this one is ww2.

The ETL modules in providers/ write these tables; the website only reads them.
Nothing here points at geo_country: the states of 1937–1945 are their own dimension, ww2.state.
"""

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import translation
from django.utils.translation import gettext_lazy as _


def ww2(table):
    """The table `table` in the schema ww2. Django quotes the name it gets, so this becomes "ww2"."<table>"."""
    return f'ww2"."{table}'


class Named(models.Model):
    """A name in English, the source language, and in German and Portuguese."""

    name = models.CharField(max_length=200)
    name_de = models.CharField(max_length=200, blank=True)
    name_pt = models.CharField(max_length=200, blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name

    @property
    def local_name(self):
        """The name in the active language, or the English name where there is no translation."""
        return getattr(self, f'name_{translation.get_language()}', '') or self.name


class State(Named):
    """A state or territory as it was in 1937–1945: sovereign states, dominions, colonies, mandates, puppet states."""

    KINDS = {
        'sovereign': _('Sovereign state'),
        'dominion': _('Dominion'),
        'colony': _('Colony'),
        'mandate': _('Mandate'),
        'puppet': _('Puppet state'),
        'occupied': _('Occupied'),
        'exile': _('Government in exile'),
    }

    code = models.CharField(primary_key=True, max_length=12, help_text='Our own code. The flag file is named after it.')
    kind = models.CharField(max_length=10, choices=KINDS)
    ruler = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
                              help_text='Who governed a dominion, colony, mandate, occupied land or puppet state.')
    successors = ArrayField(models.CharField(max_length=2), default=list, blank=True,
                            help_text='ISO 3166-1 alpha-2 codes of the countries on its land today. No link to geo_country.')
    wikidata = models.CharField(max_length=20, blank=True)
    gwcodes = ArrayField(models.PositiveIntegerField(), default=list, blank=True,
                         help_text='Gleditsch–Ward codes of its shapes in CShapes (ww2.border).')
    start = models.DateField(null=True, blank=True, help_text='Empty: it existed before 7 July 1937.')
    end = models.DateField(null=True, blank=True, help_text='Empty: it still existed on 2 September 1945.')
    flag = models.CharField(max_length=200, help_text='Path under MEDIA_ROOT, e.g. conflicts/ww2/flags/de.svg.')
    flag_source = models.URLField(max_length=500, blank=True)
    flag_licence = models.CharField(max_length=50)
    flag_author = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = ww2('state')
        ordering = ['name']


class Side(models.Model):
    """Which side a state fought on, from when to when. A state without a row for a date was not at war then."""

    SIDES = {'allies': _('Allies'), 'axis': _('Axis')}

    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='sides')
    side = models.CharField(max_length=6, choices=SIDES)
    start = models.DateField()
    end = models.DateField(null=True, blank=True, help_text='Empty: until the end of the war.')
    note = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = ww2('state_side')
        ordering = ['state', 'start']


class Deaths(models.Model):
    """One state's deaths in the whole war, from Wikipedia's table "World War II casualties".

    Each count runs from the lowest to the highest estimate; both are the same where the table gives one figure.
    A count is empty where the table gives none, or counts those deaths with another state (see note).
    """

    state = models.OneToOneField(State, on_delete=models.CASCADE, primary_key=True, related_name='deaths')
    label = models.CharField(max_length=100, help_text="The row's name in Wikipedia's table.")
    note = models.CharField(max_length=300, blank=True, help_text='What the row says about borders or inclusions.')
    population = models.PositiveBigIntegerField(null=True, blank=True, help_text='Population on 1 January 1939.')
    military_low = models.PositiveBigIntegerField(null=True, blank=True)
    military_high = models.PositiveBigIntegerField(null=True, blank=True)
    civilian_low = models.PositiveBigIntegerField(
        null=True, blank=True, help_text='Civilians killed by military activity and crimes against humanity.')
    civilian_high = models.PositiveBigIntegerField(null=True, blank=True)
    famine_low = models.PositiveBigIntegerField(null=True, blank=True,
                                                help_text='Civilians killed by war-related famine and disease.')
    famine_high = models.PositiveBigIntegerField(null=True, blank=True)
    total_low = models.PositiveBigIntegerField(null=True, blank=True)
    total_high = models.PositiveBigIntegerField(null=True, blank=True)

    class Meta:
        db_table = ww2('deaths_state')
        verbose_name_plural = 'deaths'


class Battle(Named):
    """A battle or campaign, with its casualties on each side: killed, wounded, missing and captured."""

    THEATRES = {
        'west': _('Western Europe'),
        'east': _('Eastern Front'),
        'mediterranean': _('Mediterranean and Africa'),
        'asia': _('China and Southeast Asia'),
        'pacific': _('Pacific'),
    }
    WINNERS = {'allies': _('Allied victory'), 'axis': _('Axis victory'), 'none': _('Inconclusive')}

    wikidata = models.CharField(max_length=20, unique=True)
    theatre = models.CharField(max_length=13, choices=THEATRES)
    start = models.DateField()
    end = models.DateField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    axis = ArrayField(models.CharField(max_length=12), help_text='Codes in ww2.state of the side with Germany, Italy or Japan.')
    allies = ArrayField(models.CharField(max_length=12), help_text='Codes in ww2.state of the other side.')
    axis_low = models.PositiveIntegerField(null=True, blank=True)
    axis_high = models.PositiveIntegerField(null=True, blank=True)
    allies_low = models.PositiveIntegerField(null=True, blank=True)
    allies_high = models.PositiveIntegerField(null=True, blank=True)
    winner = models.CharField(max_length=6, choices=WINNERS)
    source_url = models.URLField(max_length=500, help_text='The Wikipedia revision the casualties come from.')
    note = models.CharField(max_length=500, blank=True, help_text='What the casualty figures include.')
    image = models.CharField(max_length=200, blank=True, help_text='Path under MEDIA_ROOT, e.g. conflicts/ww2/battles/Q38789.jpg.')
    image_source = models.URLField(max_length=500, blank=True, help_text='The Commons file page.')
    image_licence = models.CharField(max_length=50, blank=True)
    image_author = models.CharField(max_length=300, blank=True)

    @property
    def region(self):
        """The region tab a battle belongs to: Europe (with Africa) or Asia (with the Pacific)."""
        return 'asia' if self.theatre in ('asia', 'pacific') else 'europe'

    class Meta:
        db_table = ww2('battle')
        ordering = ['start', 'name']


class Event(Named):
    """A dated event of the war, shown on the timeline: an invasion, a pact, a surrender, a bombing."""

    KINDS = {'war': _('War'), 'diplomacy': _('Diplomacy'), 'crime': _('Crimes'), 'bombing': _('Bombing')}
    REGIONS = {'europe': _('Europe and Africa'), 'asia': _('Asia and the Pacific'), 'world': _('Whole war')}

    date = models.DateField()
    kind = models.CharField(max_length=9, choices=KINDS)
    region = models.CharField(max_length=6, choices=REGIONS, default='world',
                              help_text='The region tab that shows the event; world shows under every tab.')
    wikidata = models.CharField(max_length=20, blank=True)
    source_url = models.URLField(max_length=500)

    class Meta:
        db_table = ww2('event')
        ordering = ['date', 'name']


class Border(models.Model):
    """A shape from CShapes 2.0 that was valid during part of 1937–1945, simplified for a world map.

    CShapes draws borders as the law saw them: occupations during the war are not in it.
    """

    gwcode = models.PositiveIntegerField()
    name = models.CharField(max_length=100, help_text="CShapes' English name.")
    start = models.DateField()
    end = models.DateField()
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
                              help_text='The state this shape is. Empty for a colony that has no row in ww2.state.')
    ruler = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
                              help_text='Who governed a colony that has no row in ww2.state (data/ww2/territories.csv).')
    geometry = models.JSONField(help_text='GeoJSON MultiPolygon.')

    class Meta:
        db_table = ww2('border')
        ordering = ['gwcode', 'start']
