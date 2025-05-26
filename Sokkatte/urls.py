from django.contrib import admin
from django.urls import path, include
from .views import StartGame
urlpatterns = [
    path('', StartGame ,name='Sokkatte_home'),

]
