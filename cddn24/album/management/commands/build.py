import logging

from django.core.management import BaseCommand

from album.models import Album
from album.tasks import build_album

logger = logging.getLogger("cddn24.album")


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("seed")
        parser.add_argument("--force", action="store_true", help="Force build even if it already exists")

    def handle(self, *args, **options):
        seed = options["seed"]
        if not Album.objects.filter(seed=seed, request_by__isnull=False).exists():
            raise ValueError("No claimed album found with seed {}".format(seed))
        build_album(seed, force=options["force"])
