from django.core.management.base import BaseCommand
import subprocess
import json


class Command(BaseCommand):
    def handle(self, *args, **options):


        model_names = [

'sito.Azienda',
'sito.Gruppo',
'sito.InformazioneUtente',
'sito.DatoCliente',
'sito.Segnalazione',
'sito.TipoRichiesta',
'sito.Cliente',
'sito.CartellaDocumenti',
'sito.DocumentoCliente',
'sito.Persona',
'sito.Marchio',
'sito.CondizioneMarchio',
'sito.CondizioneCliente',
'sito.ValutazioneCliente',
'sito.CondizioneParticolareCliente',
'sito.CondizioneGruppo',
'sito.CondizioneData',
'sito.FirmaNewsletter',
'sito.Newsletter',
'sito.DestinatarioNewsletter',
'sito.AllegatoNewsletter',
'sito.Offerta',
'sito.RigoOfferta',
'sito.Listino',
'sito.Prodotto',
'sito.Agente',
'sito.TipoAttivita',
'sito.Attivita',
 ]
        
        all_data = []
        for model_name in model_names:
            print(model_name)
            # carica in una variabile il contenuto di dumpdata

            output = subprocess.check_output(['python', 'manage.py', 'dumpdata', '--natural-primary', '--natural-foreign', model_name])
            data = json.loads(output)

            # Aggiustamenti
            for d in data:
                if model_name.lower() == 'calendario.registrazioneattivita':
                    d['fields']['valutazione'] = bool(d['fields']['valutazione'])
                if model_name.lower() == 'report.reportraccolte':
                    d['fields']['id_produttore'] = d['fields']['id_produttore'] or ''
                if model_name.lower() == 'portale.segnalazione':
                    d['fields']['servizio_priorita'] = d['fields']['servizio_priorita'] or None

            all_data.extend(data)
            print(len(data))
        with open('sunlife.json', 'w') as file:
            file.write(json.dumps(all_data, indent=4))
                       

        

        
