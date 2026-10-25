from django.urls import path

from . import views

app_name = 'conflicts'

urlpatterns = [
    path('', views.index, name='index'),
    path('world-war-ii/', views.world_war_ii, name='ww2'),
    path('world-war-ii/borders.geojson', views.ww2_borders, name='ww2-borders'),
    path('world-war-ii/deaths.csv', views.ww2_deaths_csv, name='ww2-deaths-csv'),
    path('world-war-ii/battles.csv', views.ww2_battles_csv, name='ww2-battles-csv'),
]
