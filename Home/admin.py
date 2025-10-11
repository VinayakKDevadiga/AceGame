from django.contrib import admin
from .models import GameTable, CompletedGame, PlayerStats

@admin.register(GameTable)
class RoomTableAdmin(admin.ModelAdmin):
    list_display = ('gamename','created_at','updated_at')
    search_fields = ('gamename','created_at')

@admin.register(CompletedGame)
class CompletedGameAdmin(admin.ModelAdmin):
    list_display = ('room_id', 'selected_game','game_completed_players_list',  'created_at')
    search_fields = ('room_id', 'selected_game__gamename', 'game_completed_players_list')

@admin.register(PlayerStats)
class PlayerStatsAdmin(admin.ModelAdmin):
    list_display = ('username', 'number_of_games_played', 'number_of_games_won')
    search_fields = ('username', 'number_of_games_played', 'number_of_games_won')

   
