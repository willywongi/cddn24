import logging
from pathlib import Path

from django.core.management import BaseCommand
from django.db.models import Q
import dramatiq

from album.models import Album
from album.tasks import archive

logger = logging.getLogger("cddn24.album")


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("out_dir_path", help="The folder where to archive album(s).", type=Path)
        parser.add_argument("--signature", help="Archive this single album.")

    def handle(self, *args, **options):
        q = Q(status=Album.Status.FINISHED)
        if options["signature"]:
            q &= Q(signature=options["signature"])
        album_count = Album.objects.filter(q).count()
        g = dramatiq.group(
            [archive.message(album.signature, str(options["out_dir_path"])) for album in Album.objects.filter(q)])
        g.run()
        self.stdout.write(f"Start archiving albums ({album_count}).")
        g.wait(timeout=25_000 * album_count)
        self.stdout.write(self.style.SUCCESS(f"Finished archiving albums in {options['out_dir_path']}."))
