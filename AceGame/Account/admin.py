from django.contrib import admin
from .models import RoomTable

@admin.register(RoomTable)
class RoomTableAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'room_id', 'password','created_at','passowrd_updated_at')
    search_fields = ('username', 'email', 'room_id')

   
