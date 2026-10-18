from django.contrib import admin

from .models import Country, EtlLoad


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ['name', 'iso3', 'iso2', 'continent', 'is_aggregate']
    list_filter = ['continent', 'is_aggregate']
    search_fields = ['name', 'iso3']
    exclude = ['geometry']


@admin.register(EtlLoad)
class EtlLoadAdmin(admin.ModelAdmin):
    list_display = ['table_name', 'source_name', 'row_count', 'source_updated', 'loaded_at']
    list_filter = ['table_name']
