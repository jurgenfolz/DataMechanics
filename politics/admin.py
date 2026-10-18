from django.contrib import admin

from .models import Administration, Party


@admin.register(Party)
class PartyAdmin(admin.ModelAdmin):
    list_display = ['abbreviation', 'name', 'country', 'color', 'logo_licence']
    list_filter = ['country']


@admin.register(Administration)
class AdministrationAdmin(admin.ModelAdmin):
    list_display = ['leader', 'party', 'role', 'start_date', 'end_date', 'country']
    list_filter = ['country', 'role']
