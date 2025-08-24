from django.contrib import admin
from django.urls import path, include
from Sokkatte.views import StartGame
app_name='sokkatte_app'
urlpatterns = [
    path('', StartGame ,name='Sokkatte'),
    # http://localhost:8000/Sokkatte/test168SW

]
