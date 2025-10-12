from django.contrib import admin
from django.urls import path, include
from . import views
urlpatterns = [
    path('', views.Home ,name='home'),
    path('playgame/', views.Playgame, name='playgame'),

    # Rom page urls
    path('createroom/', views.CreateRoom, name='createroom'),
    path('joinroom/', views.Join_room, name='join_room'),
    path('waitforplayers/', views.Waitforplayers, name='waitforplayers'),

    # Game page
    path('gamepage/', views.Gamepage, name='gamepage'),
    path('rulepage/', views.Rulepage, name='rulepage'),
    path('winner_page/', views.Game_Over, name='winner_page'),
    path('player-stats/', views.player_stats_view, name='player-stats'),
    path('privacy-policy/', views.Privacy_Policy, name='privacy-policy'),
    path('sokkate-rules/', views.Sokkate_Rules, name='sokkate-rules'),
    path('About/', views.About, name='About'),
    # jwt get user
    path("getuser/", views.get_user, name="current_user"),

]
