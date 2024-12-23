from pathlib import Path

from django.db import models
from django.conf import settings
from django.core.validators import validate_email
import nanoid


def create_default_signature():
    return nanoid.generate()


class AlbumManager(models.Manager):
    def claim(self, email):
        try:
            album = self.get(request_by=email)
        except Album.DoesNotExist:
            album = self.filter(request_by__isnull=True).first()
            album.request_by = email
            album.save()
        return album


class Album(models.Model):
    objects = AlbumManager()

    class Status(models.TextChoices):
        IDLE = "IDLE", "IDLE"
        RUNNING = "RUNNING", "RUNNING"
        FINISHED = "FINISHED", "FINISHED"

    signature = models.TextField(null=False, default=create_default_signature)
    seed = models.PositiveBigIntegerField(null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.TextField(choices=Status.choices, default=Status.IDLE)
    error = models.TextField(null=True)
    request_by = models.TextField(null=True, validators=[validate_email])

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['signature'], name='unique_signature'),
            models.UniqueConstraint(fields=['seed'], name='unique_seed'),
        ]

    def get_base_path(self):
        base_path = Path(settings.MEDIA_ROOT) / f"album_{self.seed}"
        base_path.mkdir(exist_ok=True)
        return base_path

    @property
    def path(self):
        return Path(settings.MEDIA_ROOT) / f"album_{self.seed}"

    def __str__(self):
        return f"<seed:{self.seed} request_by:{self.request_by}>"
