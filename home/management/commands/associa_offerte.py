
# management command per associare le offerte ai prodotti

from django.core.management.base import BaseCommand, CommandError
from home.models import Offerta, Cliente, OffertaCliente
from django.db import transaction

class Command(BaseCommand):
    help = 'Associa le offerte ai prodotti'

    def handle(self, *args, **options):
        for offerta in Offerta.objects.all():
            OffertaCliente.objects.create(offerta=offerta, cliente=offerta.cliente)
            print("Offerta {} associata al cliente {}".format(offerta, offerta.cliente))

  