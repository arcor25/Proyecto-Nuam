from django.core.management.base import BaseCommand

from config.mongo import crear_indices, obtener_db


class Command(BaseCommand):
    help = "Verifica la conexión con MongoDB y crea los índices de las colecciones."

    def handle(self, *args, **options):
        obtener_db().command("ping")
        crear_indices()
        self.stdout.write(self.style.SUCCESS("MongoDB conectado e índices creados."))