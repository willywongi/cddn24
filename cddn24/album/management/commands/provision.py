import logging
import random

from django.core.management import BaseCommand
from django.db import IntegrityError

from album.models import Album

logger = logging.getLogger("cddn24.album")


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("count", type=int)

    def handle(self, *args, **options):
        count = options["count"]
        created = 0
        while created < count:
            for seed in random.sample(range(100_000, 999_999), k=count):
                try:
                    Album.objects.create(seed=seed)
                except IntegrityError:
                    logger.debug("Skipping album w/ seed=%s (already provisioned)", seed)
                    continue
                else:
                    created += 1
        logger.info("Provisioned %s album(s)", count)
