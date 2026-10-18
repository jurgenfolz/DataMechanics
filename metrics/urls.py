from django.urls import path

from . import views

app_name = 'metrics'

urlpatterns = [
    path('', views.metric_list, name='list'),
    path('countries.geojson', views.country_shapes, name='shapes'),
    path('<slug:slug>/', views.metric_detail, name='detail'),
    path('<slug:slug>/data.json', views.metric_data, name='data'),
    path('<slug:slug>/data.csv', views.metric_csv, name='csv'),
]
