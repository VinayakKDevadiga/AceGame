from django.db import models

# Create your models here.
class GameTable(models.Model):
    gamename   = models.CharField(max_length=100)
      
    # ► Add these timestamp fields:
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.gamename}"
    
class PlayerStats(models.Model):
    username = models.CharField(max_length=100)
    number_of_games_played = models.IntegerField(default=0)
    number_of_games_won = models.IntegerField(default=0)
    number_of_games_lost = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.username} - Played: {self.number_of_games_played}, Won: {self.number_of_games_won}"

# # from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField, JSONField  # Use JSONField for complex data

class CompletedGame(models.Model):
    room_id = models.CharField(max_length=100)
    selected_game = models.CharField(max_length=100)
    owner = models.CharField(max_length=100)
    players = ArrayField(models.CharField(max_length=100), default=list)
    players_connected_list = models.JSONField(default=dict)
    players_card_list = models.JSONField(default=dict)
    played_card_list = models.JSONField(default=list)
    game_completed_players_list = ArrayField(models.CharField(max_length=100), default=list)

    # Game progress
    starting_player = models.CharField(max_length=100)
    current_player = models.CharField(max_length=100)
    status = models.CharField(max_length=50)
    card_distributed_flag = models.BooleanField(default=False)

    # Misc flags and info
    duplicate_owner_login = models.BooleanField(default=False)
    card_problem = models.JSONField(default=dict)
    current_round = models.JSONField(default=dict)
    cardList = ArrayField(models.CharField(max_length=10), default=list)
    gamelist = ArrayField(models.CharField(max_length=100), default=list)

    # Meta info
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.selected_game} ({self.room_id})"
