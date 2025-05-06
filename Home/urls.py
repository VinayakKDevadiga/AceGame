from django.contrib import admin
from django.urls import path, include
from . import views
urlpatterns = [
    path('', views.Home ,name='home'),
    path('playgame/', views.Playgame, name='playgame'),

    # Rom page urls
    path('roompage/', views.Playgame, name='roompage'),

]
