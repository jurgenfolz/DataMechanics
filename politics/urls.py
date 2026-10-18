from django.urls import path

from . import views

app_name = 'politics'

urlpatterns = [
    path('', views.politics_index, name='index'),
    path('<slug:slug>/', views.country_page, name='country'),
    path('<slug:slug>/data.json', views.country_data, name='data'),
]
