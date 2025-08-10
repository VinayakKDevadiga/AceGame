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
