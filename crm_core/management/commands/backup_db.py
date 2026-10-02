"""Бэкап SQLite: python manage.py backup_db [--keep 7]."""
import shutil
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Копирует db.sqlite3 в backups/db-YYYYMMDD-HHMMSS.sqlite3"

    def add_arguments(self, parser):
        parser.add_argument("--keep", type=int, default=7, help="Сколько свежих бэкапов хранить")

    def handle(self, *args, **options):
        src = Path(settings.DATABASES["default"].get("NAME", "db.sqlite3"))
        if src.suffix != ".sqlite3" or not src.exists():
            self.stdout.write(self.style.WARNING("Бэкап нужен только для SQLite, пропускаю."))
            return
        dst_dir = Path(settings.BASE_DIR) / "backups"
        dst_dir.mkdir(exist_ok=True)
        dst = dst_dir / f"db-{datetime.now().strftime('%Y%m%d-%H%M%S')}.sqlite3"
        shutil.copy2(src, dst)
        keep = max(options["keep"], 1)
        old = sorted(dst_dir.glob("db-*.sqlite3"))[:-keep]
        for f in old:
            f.unlink()
        self.stdout.write(self.style.SUCCESS(f"Бэкап готов: {dst}"))
