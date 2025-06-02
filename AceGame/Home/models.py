from django.db import models

# Create your models here.
class GameTable(models.Model):
    gamename   = models.CharField(max_length=100)
      
    # ► Add these timestamp fields:
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.gamename}"