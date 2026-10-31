from django.urls import path

from . import views

app_name = 'events'

urlpatterns = [
    path('events.json', views.events_json, name='json'),
]
