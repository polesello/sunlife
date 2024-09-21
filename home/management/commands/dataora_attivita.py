
# management command per associare le offerte ai prodotti

from django.core.management.base import BaseCommand, CommandError
from home.models import Attivita

class Command(BaseCommand):
    
    def handle(self, *args, **options):
        attivita = Attivita.objects.all()
        for a in attivita:
            # combino data e ora in un solo campo
            ora = a.ora and str(a.ora) or '00:00:00'
            a.dataora = str(a.data) + ' ' + ora
            a.save()