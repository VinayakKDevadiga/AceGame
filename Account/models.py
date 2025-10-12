from django.db import models


class RoomTable(models.Model):
    username   = models.CharField(max_length=100)
    email      = models.EmailField(max_length=100)
    room_id    = models.CharField(max_length=50, unique=True)
    # optional Password, status, etc…
    password = models.CharField(
    max_length=100,
    null=False,
    blank=False,
    default="ILOVEACE"
    )
    # ► Add these timestamp fields:
    created_at = models.DateTimeField(auto_now_add=True)
    passowrd_updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.username} ({self.room_id})"


# from django.db import models
# from django.utils import timezone


# class RoomTable(models.Model):
#     username   = models.CharField(max_length=100)
#     email      = models.EmailField(max_length=100)
#     room_id    = models.CharField(max_length=50, unique=True)
#     password   = models.CharField(
#         max_length=100,
#         null=False,
#         blank=False,
#         default="ILOVEACE"
#     )

#     # ✅ New tracking fields
#     match_played   = models.PositiveIntegerField(default=0)
#     matches_won    = models.PositiveIntegerField(default=0)
#     matches_lost   = models.PositiveIntegerField(default=0)
#     last_match_type = models.CharField(max_length=100, blank=True, null=True)
#     last_result     = models.CharField(max_length=10, blank=True, null=True, choices=[
#         ('win', 'Win'),
#         ('lose', 'Lose'),
#         ('draw', 'Draw'),
#     ])
#     win_rate = models.FloatField(default=0.0)

#     # timestamps
#     created_at = models.DateTimeField(auto_now_add=True)
#     passowrd_updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return f"{self.username} ({self.room_id})"

#     def update_game_result(self, match_type: str, result: str):
#         """
#         Update player stats after a game completes.

#         Args:
#             match_type (str): e.g., "Sokkatte"
#             result (str): one of "win", "lose", or "draw"
#         """
#         self.match_played += 1
#         self.last_match_type = match_type
#         self.last_result = result

#         if result == "win":
#             self.matches_won += 1
#         elif result == "lose":
#             self.matches_lost += 1

#         # Calculate win rate
#         if self.match_played > 0:
#             self.win_rate = round((self.matches_won / self.match_played) * 100, 2)

#         self.save()
