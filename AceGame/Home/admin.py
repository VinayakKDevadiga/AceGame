from django.contrib import admin
from .models import GameTable

@admin.register(GameTable)
class RoomTableAdmin(admin.ModelAdmin):
    list_display = ('gamename','created_at','updated_at')
    search_fields = ('gamename','created_at')

   
