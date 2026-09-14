import math
import time

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, connection


class Command(BaseCommand):
    help = "Aguarda PostgreSQL por um período limitado, sem exibir credenciais."

    def add_arguments(self, parser):
        parser.add_argument("--timeout", type=float, default=30)

    def handle(self, *args, **options):
        timeout = options["timeout"]
        if not math.isfinite(timeout) or timeout <= 0:
            raise CommandError("O timeout deve ser positivo e finito.")
        deadline = time.monotonic() + timeout
        while True:
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                self.stdout.write("PostgreSQL disponível.")
                return
            except DatabaseError:
                connection.close()
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise CommandError("PostgreSQL indisponível após o prazo de espera.") from None
                time.sleep(min(1, remaining))
