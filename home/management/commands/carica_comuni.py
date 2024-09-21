from django.core.management.base import BaseCommand
from home.models import Comune, Provincia
import csv

class Command(BaseCommand):
    help = 'Carica i comuni italiani'

    def handle(self, *args, **options):
        with open('listacomuni.txt', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')
            for row in reader:
                provincia, created = Provincia.objects.get_or_create(sigla=row['Provincia'])
                comune, created = Comune.objects.get_or_create(nome=row['Comune'], provincia=provincia)
                comune.cap = row['CAP']
                comune.save()
                print('Caricato comune {}'.format(comune))
        
  