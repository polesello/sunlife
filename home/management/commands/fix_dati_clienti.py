from django.core.management.base import BaseCommand, CommandError
from home.models import Cliente

import json

class Command(BaseCommand):
    help = 'campo altro da str a JSON'

    def handle(self, *args, **options):
        for cliente in Cliente.objects.all():
            if cliente.altro:
                if not isinstance(cliente.altro, dict):
                    cliente.altro = json.loads(cliente.altro)
                    cliente.save()
                    print("Cliente {} aggiornato".format(cliente))
  