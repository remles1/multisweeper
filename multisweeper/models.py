from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class PlayerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    elo_rating = models.IntegerField(default=1000)

    def __str__(self):
        return f"{self.user.username}'s Profile (Elo: {self.elo_rating})"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_player_profile(sender, instance, created, **kwargs):
    if created:
        PlayerProfile.objects.create(user=instance)
