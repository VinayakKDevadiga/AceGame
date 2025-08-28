from django.contrib import admin
from django.urls import path, include
from . import views
urlpatterns = [
    path('', views.Home ,name='home'),

    # Rom page urls
    path('createroom/', views.CreateRoom, name='createroom'),
    path('joinroom/', views.Join_room, name='join_room'),
    path('waitforplayers/', views.Waitforplayers, name='waitforplayers'),

    # Game page
    path('gamepage/', views.Gamepage, name='gamepage'),
    path('rulepage/', views.Rulepage, name='rulepage'),

    # jwt get user
    path("getuser/", views.get_user, name="current_user"),

]
