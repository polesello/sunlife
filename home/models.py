
from wagtail.fields import StreamField, RichTextField
from wagtail.admin.panels import (
    FieldPanel, HelpPanel, InlinePanel, MultiFieldPanel, MultipleChooserPanel,
    TabbedInterface, ObjectList, FieldRowPanel,
)

from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet
from wagtail.search import index

from modelcluster.models import ClusterableModel
from wagtail.models import PreviewableMixin, RevisionMixin

from wagtail.models import Orderable
from modelcluster.fields import ParentalKey

from wagtail_color_panel.edit_handlers import NativeColorPanel

from django.utils.html import format_html
from django.urls import reverse

from django.contrib.auth.models import User
    
from django.db import models
from django import forms
from datetime import datetime, date

import json
from decimal import Decimal
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        # 👇️ if passed in object is instance of Decimal
        # convert it to a string
        if isinstance(obj, Decimal):
            return str(obj)
        # 👇️ otherwise use the default behavior
        return json.JSONEncoder.default(self, obj)
    

TIPI_VALORI = (
    ('C', 'Testo breve'),
    ('T', 'Testo lungo'),
    ('N', 'Numero'),
    ('D', 'Data'),
    ('I', 'Immagine'),
    ('B', 'Sì/No'),
)

 

class Gruppo(models.Model):
    nome = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='loghi', blank=True)
    ordine = models.IntegerField(blank=True, default=0)
    is_progettista = models.BooleanField("Progettisti?", help_text="Seleziona per mostrare date e note anziché condizioni di sconto.", default=False)
    is_privato = models.BooleanField("Privati?", help_text="Gruppo contenente privati anziché aziende.", default=False)
    users = models.ManyToManyField(User, verbose_name='Visibile agli utenti')
    parent = models.ForeignKey('self', blank=True, null=True, verbose_name="Contenuto nel gruppo", related_name='sottogruppi', on_delete=models.CASCADE) # Macrogruppo
    visibile = models.BooleanField("Visibile?", help_text="Va mostrato nel form di ricerca clienti?", default=True)


    def __str__(self):
        return self.nome

    @property 
    def totale_clienti(self):
        return self.clienti.count()
                
    class Meta:
        verbose_name_plural = "Gruppi"
        ordering = ['ordine', 'nome']

        

class InformazioneUtente(models.Model):
    """Proprietà varie dell'azienda amministratrice"""
    codice = models.CharField(max_length=100)
    nome = models.CharField(max_length=255)
    tipo = models.CharField(max_length=1, choices=TIPI_VALORI, default='C')
    valore_char = models.CharField(max_length=255, blank=True, verbose_name="Testo breve")
    valore_text = RichTextField(blank=True, null=True, verbose_name="Testo lungo")
    valore_image = models.ImageField(upload_to='info_utente', blank=True, verbose_name="Immagine")
    valore_boolean = models.BooleanField(verbose_name="Sì/No")

    def get_absolute_url(self):
        return '/info_utente/%d' % self.id
    
    def __str__(self):
        return '%s - %s' % (self.nome, self.tipo)
                
    class Meta:
        verbose_name_plural = "Informazioni utente"
        ordering = ['nome']


class DatoCliente(models.Model):
    """Dati aggiuntivi del cliente, da salvare in JSON nel campo "altro" in Cliente"""
    codice = models.CharField(max_length=100)
    nome = models.CharField(max_length=255)
    tipo = models.CharField(max_length=1, choices=TIPI_VALORI, default='C')
    ordine = models.IntegerField(default=10)
    visibile = models.BooleanField(default=True)
    obbligatorio = models.BooleanField(default=False)
    
    def __str__(self):
        return self.nome
                
    class Meta:
        verbose_name = "Dato aggiuntivo cliente"
        verbose_name_plural = "Dati aggiuntivi cliente"
        ordering = ['ordine']
        

class Segnalazione(models.Model):
    """Da dove arriva questo cliente?"""
    nome = models.CharField(max_length=100)
    
    def __str__(self):
        return self.nome

    class Meta:
        verbose_name_plural = "Fonti di segnalazione"
        ordering = ['nome']

class TipoRichiesta(models.Model):
    """Richieste possibili per un cliente (es. impianto radiante, stufa pellet)"""
    nome = models.CharField(max_length=100)
    
    def __str__(self):
        return self.nome

    class Meta:
        ordering = ('nome',)
        verbose_name = "Tipo di richiesta"
        verbose_name_plural = "Tipi di richiesta"


class Cliente(index.Indexed, ClusterableModel):
    ragsoc = models.CharField('Ragione sociale', max_length=200)
    indirizzo = models.CharField(verbose_name='Via e n.', max_length=200, blank=True)
    cap = models.CharField('CAP', blank=True, max_length=5)
    citta = models.CharField('Città', blank=True, max_length=200)
    provincia = models.CharField(blank=True, max_length=2)
    stato = models.CharField(max_length=100, default='Italia')
    lat = models.FloatField("Latitudine", blank=True, null=True, default=0)
    lng = models.FloatField("Longitudine", blank=True, null=True, default=0)

    telefono = models.CharField(max_length=20, blank=True)
    fax = models.CharField(max_length=20, blank=True)
    email = models.EmailField(max_length=100, blank=True)
    pec = models.EmailField(max_length=100, blank=True)
    sdi = models.CharField('SDI', max_length=7, blank=True)
    piva = models.CharField('Partita IVA', max_length=11, blank=True)
    cf = models.CharField('Codice fiscale', max_length=16, blank=True)

    banca = models.CharField(max_length=100, blank=True)
    iban = models.CharField('IBAN', max_length=27, blank=True)
    segnalazione = models.ForeignKey(Segnalazione, blank=True, null=True, help_text="Da chi è stato ricevuto questo contatto?", on_delete=models.SET_NULL)
    note = models.TextField('Note', blank=True, null=True)
    note_private = models.TextField('Note private', blank=True, null=True)
    gruppo = models.ForeignKey(Gruppo, blank=True, null=True, on_delete=models.SET_NULL, related_name='clienti')
    data = models.DateField(verbose_name="Data inserimento", default=datetime.now, blank=True, null=True)
    richieste = models.ManyToManyField(TipoRichiesta, blank=True)
    
    inizio_lavori = models.DateField(verbose_name="Previsione inizio lavori", blank=True, null=True)
    data_installazione = models.DateField(blank=True, null=True)
    ditta_installatrice = models.CharField(max_length=200, blank=True)

    altro = models.JSONField(blank=True, null=True, verbose_name="Altri dati")
    users = models.ManyToManyField(User, verbose_name='Visibile agli utenti')

    # TEMPORANEO, solo per importare i dati
    # updated = models.DateTimeField(default=datetime.now)

    # GIUSTO 
    updated = models.DateTimeField(auto_now=True)

    anagrafica_panels = [
        FieldPanel('ragsoc'),
        MultiFieldPanel([
            FieldRowPanel([
                FieldPanel('indirizzo'),
                FieldPanel('citta'),
            ]),
            FieldRowPanel([
                FieldPanel('cap'),
                FieldPanel('provincia'),
                FieldPanel('stato'),
            ]),

        ], heading="Indirizzo"),
        InlinePanel('indirizzi', heading='Indirizzi aggiuntivi', label="Indirizzo", classname="collapsed"),        
        FieldRowPanel([
            FieldPanel('telefono'), 
            FieldPanel('email'),
            FieldPanel('pec'),
        ], heading="Contatti"),
        FieldRowPanel([
            FieldPanel('piva'),
            FieldPanel('cf'),
        ]),
        FieldRowPanel([
            FieldPanel('banca'),
            FieldPanel('iban'),
        ]),
    ]

    offerte_panels = [
        MultipleChooserPanel('offerte_cliente', chooser_field_name='offerta', label="Offerte"),
    ]

    attivita_panels = [
        InlinePanel('persone', label="Persone"),
        InlinePanel('attivita', label="Attività"),
    ]

    documenti_panels = [
        InlinePanel('documenti', label="Documenti personali"),
        InlinePanel('documenti_prodotto', label="Specifiche prodotto"),
    ]


    altro_panels = [
        FieldRowPanel([
            FieldPanel('segnalazione'),
            FieldPanel('gruppo'),
        ]),
        FieldPanel('richieste', widget=forms.CheckboxSelectMultiple, classname="collapsed"),
        FieldRowPanel([
            FieldPanel('inizio_lavori'),
            FieldPanel('data_installazione'),
            FieldPanel('ditta_installatrice'),
        ], heading="Installazione", classname="collapsed"),
        FieldPanel('note'),
        FieldPanel('note_private'),
        FieldPanel('altro'),
        FieldPanel('users', widget=forms.CheckboxSelectMultiple),
        FieldPanel('data'),
    ]


    edit_handler = TabbedInterface([
        ObjectList(anagrafica_panels, heading='Anagrafica'),
        ObjectList(attivita_panels, heading='Contatti e attività'),
        ObjectList(offerte_panels, heading='Offerte'),
        ObjectList(documenti_panels, heading='Documenti'),
        ObjectList(altro_panels, heading='Altro'),
    ])

    search_fields = [
        index.AutocompleteField('ragsoc'),
        index.SearchField('ragsoc'),
        index.AutocompleteField('citta', null=True),
        index.SearchField('citta'),
        index.SearchField('indirizzo'),
        index.SearchField('piva'),
        index.SearchField('cf'),
        index.SearchField('telefono'),
        index.SearchField('email'),
        index.SearchField('persone__nome'),
        index.SearchField('persone__telefono'),


    ]
    
    def __str__(self):
        return self.ragsoc

    def to_json(self):
        """Aggiunge "Altri dati" al JSON"""
        json_value = super().to_json()
        value = json.loads(json_value)
        value['altri_dati'] = self.altri_dati
        return json.dumps(value, cls=DecimalEncoder)


    @property
    def altri_dati(self):
   
        dati_cliente = []
        if self.altro:
            fields = DatoCliente.objects.filter(visibile=True)
            for field in fields:
                if field.codice in self.altro and self.altro[field.codice] not in ('', None):
                    dati_cliente.append({'label':field.nome, 'value':self.altro[field.codice], 'type':field.tipo})
        return dati_cliente


    @property
    def token(self):
        from hashlib import sha1

        SECRET = 'Che caldo che fa!'
        return sha1((str(self.pk) + SECRET).encode('utf-8')).hexdigest()


    def start_url(self):
        return format_html('<a target="_blank" href="{}">Start</a>', reverse('home:cliente_start', args=[self.pk, self.token]))
    
    def send_token(self, request):
        from django.urls import reverse
        print('Invio token a %s' % self.email)
        start_url =  request.build_absolute_uri(reverse('home:cliente_start', args=[self.pk, self.token]))
        print(start_url)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clienti"
        ordering = ['ragsoc']
        permissions = (
            ("view_client_private_note", "Vedere le note private del cliente"),
        )

    def link_mappa(self):
        address = "%s %s" % (self.indirizzo, self.citta)

        if self.provincia:
            address += ' %s' % self.provincia.upper()
        return "http://maps.google.it?q=%s" % address

    def geoRefCliente(self):
        from urllib import quote_plus, urlopen
        import json
        
        GEOREF_URL = 'http://maps.googleapis.com/maps/api/geocode/json?address=%s,%s,%s+IT&sensor=false'
        coords = {}
# Geocoding e salvataggio delle coordinate
#        url = GEOREF_URL % (quote_plus(self.citta), quote_plus(self.indirizzo))

# 1.8.2013 - Encoding dei parametri, altrimenti "Fossò" dà errore

        if self.citta:
            url = GEOREF_URL % (quote_plus(unicode(self.citta).encode('utf-8')), quote_plus(unicode(self.indirizzo).encode('utf-8')), quote_plus(unicode(self.provincia).encode('utf-8')))
            json_result = json.load(urlopen(url))

            try:
                if json_result['status'] == 'OK':
                    if json_result['results']:
                        coords = json_result['results'][0]['geometry']['location']
            except KeyError:
                pass
        
        return coords
    
    @property
    def cf_piva(self):
        return self.cf or self.piva

    @property
    def indirizzo_completo(self):
        return "%s %s (%s)" % (self.indirizzo, self.citta, self.provincia)   

    @property
    def luogo_data(self):
        from django.template.defaultfilters import date as date_filter
        return "%s, %s" % (self.citta, date_filter(date.today(), 'j F Y').lower())





class DatiAbitazione(models.Model):
    """Dati dell'abitazione del cliente"""
    cliente = ParentalKey(Cliente, related_name='dati_abitazione')
    totale_interni = models.IntegerField(blank=True, null=True, verbose_name="N° totali interni")
    anno_costruzione = models.IntegerField(blank=True, null=True, verbose_name="Anno costruzione")
    climatizzatore = models.BooleanField("Climatizzatore", default=False, null=True)
    n_foglio = models.CharField("N° foglio", max_length=10, blank=True)
    n_mappale = models.CharField("N° mappale", max_length=10, blank=True)
    n_subalterno = models.CharField("N° subalterno", max_length=10, blank=True)
    mq_riscaldati = models.IntegerField("M² riscaldati", blank=True, null=True)
    potenza_caldaia = models.IntegerField("Potenza nominale vecchia caldaia", blank=True, null=True)
    rendimento_caldaia = models.IntegerField("Rendimento vecchia caldaia", blank=True, null=True)
    
    def __str__(self):
        return "%s" % self.cliente

    class Meta:
        verbose_name = "Dati abitazione"
        verbose_name_plural = "Dati abitazione"







class OffertaCliente(Orderable, models.Model):
  cliente = ParentalKey(Cliente, related_name='offerte_cliente')
  offerta = models.ForeignKey('home.Offerta', related_name='+', on_delete=models.CASCADE)







class DocumentoCliente(models.Model):
    cliente = ParentalKey('Cliente', related_name='documenti')
    nome = models.CharField(max_length=255, blank=True)
    file = models.FileField(upload_to='documenti')
    data_aggiornamento = models.DateTimeField(auto_now=True)
    privato = models.BooleanField(default=False, help_text="Non visibile all'utente nella sua area privata")
    preview = models.ImageField(upload_to='previews', blank=True, null=True)
    installatore = models.BooleanField(default=False, help_text="Documento per installatori")

    def create_preview(self):
        from PIL import Image
        import os
        from io import BytesIO
        from django.core.files.uploadedfile import InMemoryUploadedFile

        if self.file:
            # if it's an image, create a thumbnail
            if self.is_image():
                img = Image.open(self.file)
                img = img.convert('RGB')
                img.thumbnail((200, 200))
                thumb_io = BytesIO()
                img.save(thumb_io, format='JPEG')
                thumb_file = InMemoryUploadedFile(thumb_io, None, self.file.name, 'image/jpeg', thumb_io.tell(), None)
                self.preview.save(self.file.name, thumb_file, save=True)
            # if it's a pdf, create a preview
            elif self.content_type == 'application/pdf':
                from wand.image import Image as WImage
                img = WImage(filename=self.file.path + '[0]')
                img.format = 'jpeg'
                # create temporary file
                tmp = BytesIO()
                img.save(file=tmp)
                self.preview.save(self.file.name + '.jpg', tmp, save=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.preview:
            self.create_preview()

    @property
    def content_type(self):
        import magic
        mime = magic.Magic(mime=True)
        return mime.from_file(self.file.path)
    
    def is_image(self):
        IMAGE_MIME_TYPES = ['image/jpeg', 'image/png', 'image/gif']
        return self.content_type in IMAGE_MIME_TYPES
    
    class Meta:
        verbose_name = "Documento cliente"
        verbose_name_plural = "Documenti cliente"




class Persona(models.Model):
    nome = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.CharField(max_length=100, blank=True)
    mansione = models.CharField(max_length=100, blank=True)
    ordine = models.IntegerField(blank=True, default=0)
    cliente = ParentalKey(Cliente, on_delete=models.CASCADE, related_name='persone')
    
    panels = [
        FieldRowPanel([
            FieldPanel('nome'),
            FieldPanel('mansione'),
        ]),
        FieldRowPanel([
            FieldPanel('telefono'),
            FieldPanel('email'),
        ]),
    ]
    
    def __str__(self):
        return '%s | %s' % (self.nome, self.cliente)

    class Meta:
        verbose_name_plural = "Persone"
        ordering = ['ordine']


class DocumentoProdotto(Orderable):
    document = models.ForeignKey('wagtaildocs.Document', on_delete=models.CASCADE, related_name='+')
    cliente = ParentalKey('Cliente', related_name='documenti_prodotto')


    class Meta:
        verbose_name = "Documento prodotto"
        verbose_name_plural = "Documenti prodotto"




class Marchio(models.Model):
    nome = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='loghi', blank=True)
    ordine = models.IntegerField(blank=True, default=0)
    
    def __str__(self):
        return self.nome

    class Meta:
        verbose_name_plural = "Marchi"
        ordering = ['ordine']


class CondizioneMarchio(models.Model):
    """Condizione di vendita disponibile per un certo marchio"""
    marchio = models.ForeignKey(Marchio, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    valore = models.TextField(max_length=255, blank=True, null=True, help_text='Valore predefinito')
    ordine = models.IntegerField(blank=True, default=0)
    separato = models.BooleanField("Separato?", default=False)
    lungo = models.BooleanField("Testo lungo?")

    def __str__(self):
        return "%s: %s" % (self.marchio, self.nome)

    class Meta:
        verbose_name_plural = "Condizioni marchio"
        ordering = ['marchio', 'ordine', 'nome']
        unique_together = ('nome', 'marchio')


class CondizioneCliente(models.Model):
    """Condizione di vendita da praticare a un certo cliente"""
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    condizione = models.ForeignKey(CondizioneMarchio, on_delete=models.CASCADE)
    valore = models.CharField(max_length=255, blank=True)
    
    def __str__(self):
        return "%s | %s" % (self.cliente, self.condizione)

    def get_absolute_url(self):
        return '%s/condizionemarchio/%d/condizionecliente/%d' % (self.cliente.get_absolute_url(), self.condizione.id, self.id)

    class Meta:
        verbose_name_plural = "Condizioni cliente"
        unique_together = ('cliente', 'condizione')
        ordering = ['cliente', 'condizione']
        


class ValutazioneCliente(models.Model):
    """Valutazione della qualità di un certo cliente per un certo marchio"""
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    marchio = models.ForeignKey(Marchio, on_delete=models.CASCADE)
    valore = models.IntegerField(default=0)
    
    def __str__(self):
        return u"%s - %s: %s" % (self.cliente, self.marchio, u'★' * self.valore)
        
    class Meta:
        verbose_name_plural = "Valutazioni clienti"
        unique_together = ('cliente', 'marchio')
        ordering = ['cliente', 'marchio']





class CondizioneParticolareCliente(models.Model):
    """Condizione di vendita specifica per un certo cliente"""
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    marchio = models.ForeignKey(Marchio, on_delete=models.CASCADE)
    nome = models.CharField(max_length=255)
    valore = models.CharField(max_length=255, blank=True)
    
    def __str__(self):
        return "%s | %s" % (self.cliente, self.marchio)

    def get_absolute_url(self):
        return '%s/condizionecliente/%d' % (self.cliente.get_absolute_url(), self.id)

    class Meta:
        verbose_name_plural = "Condizioni particolare cliente"
        unique_together = ('cliente', 'marchio', 'nome')
        ordering = ['cliente', 'marchio']



class CondizioneGruppo(models.Model):
    """Condizione di vendita da praticare ai clienti di un certo gruppo"""
    gruppo = models.ForeignKey(Gruppo, on_delete=models.CASCADE)
    condizione = models.ForeignKey(CondizioneMarchio, on_delete=models.CASCADE)
    valore = models.CharField(max_length=255)
    
    def __str__(self):
        return "%s | %s: %s" % (self.gruppo.nome, self.condizione.marchio.nome, self.condizione.nome)
        
    class Meta:
        verbose_name_plural = "Condizioni gruppo"
        unique_together = ('gruppo', 'condizione')
        ordering = ['gruppo', 'condizione']


class CondizioneData(models.Model):
    """Data di aggiornamento delle condizioni di un cliente per un certo marchio"""
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    marchio = models.ForeignKey(Marchio, on_delete=models.CASCADE)
    data = models.DateField(default=datetime.now)
    note = models.TextField('note', blank=True, null=True)
    
    def __str__(self):
        return "%s | %s | %s" % (self.cliente, self.marchio, self.data.strftime('%d-%m-%Y'))

    def get_absolute_url(self):
        return '%s/marchio/%d/condizionedata/%s' % (self.cliente.get_absolute_url(), self.marchio.id, self.id)

    class Meta:
        verbose_name_plural = "Data condizioni"
        unique_together = ('cliente', 'marchio', 'data')
        ordering = ['cliente', 'marchio', 'data']
        

        

class FirmaNewsletter(models.Model):
    """Firma per newsletter"""
    nome = models.CharField(max_length=255)
    testo = RichTextField()
    
    def __str__(self):
        return self.nome  

    class Meta:
        verbose_name_plural = "Firme newsletter"
        ordering = ['nome']
        
   

        
class Newsletter(models.Model):
    """Newsletter da spedire a un gruppo di contatti"""

    SENDERS = (
        ('info@sunlifegroup.it', 'info@sunlifegroup.it'),
        ('info@lazzarirappresentanze.it', 'info@lazzarirappresentanze.it'),
    )
    mittente_nome = models.CharField('Nome mittente', max_length=255, blank=True)
    mittente_email = models.EmailField('Email mittente', choices=SENDERS)
    oggetto = models.CharField(max_length=255)
    testo = RichTextField(blank=True, null=True)
    firma = models.ForeignKey(FirmaNewsletter, blank=True, null=True, on_delete=models.SET_NULL)
    
#includi_allegati
    link_allegati = models.BooleanField(verbose_name="Allegati pesanti?", default=True, help_text="Seleziona per NON inviare gli allegati nella mail, verrà inserito un link (utile nel caso di allegati molto pesanti).")
    data_aggiornamento = models.DateTimeField(auto_now=True)
    data_spedizione = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        if self.data_spedizione:
            return "%s | spedita il %s" % (self.oggetto, self.data_spedizione.strftime('%d-%m-%Y'))
        else:
            return "%s | agg. il %s | DA SPEDIRE" % (self.oggetto, self.data_aggiornamento.strftime('%d-%m-%Y'))  

    def get_absolute_url(self):
        return '/newsletter/%d' % self.id


    def add_linked_files(self, request):
        from django.template.defaultfilters import filesizeformat
        if self.allegati.all():
            allegati_html = "<h2>Allegati</h2>"
            for all in self.allegati.all():
                allegati_html += '<p><a href="https://%s%s">%s</a> <span style="color:#999">(%s)</span></p>' % (request.get_host(), all.file_obj.url, all.get_filename(), filesizeformat(all.file_obj.size))    
            self.testo += allegati_html
            

    class Meta:
        verbose_name_plural = "Newsletter"
        ordering = ['-data_aggiornamento']


        

class DestinatarioNewsletter(models.Model):
    """Destinatari di una newsletter"""
    email = models.EmailField(blank=True)
    cliente = models.ForeignKey(Cliente, blank=True, null=True, on_delete=models.SET_NULL)
    persona = models.ForeignKey(Persona, blank=True, null=True, on_delete=models.SET_NULL)
    newsletter = models.ForeignKey(Newsletter, related_name='destinatari', on_delete=models.CASCADE)

    def __str__(self):
        email = self.email
        if self.cliente:
            email = self.cliente.email
        if self.persona:
            email = self.persona.email
        return "%s --> %s" % (email, self.newsletter)

    def get_absolute_url(self):
        return '/destinatarionewsletter/%d' % self.id

    class Meta:
        verbose_name_plural = "Destinatari newsletter"
        ordering = ['newsletter', 'cliente__ragsoc', 'persona__nome', 'email']
        unique_together = ('newsletter', 'email', 'cliente', 'persona')
        

class AllegatoNewsletter(models.Model):
    """Allegati a una newsletter"""
    file_obj = models.FileField('File', upload_to='newsletter')
    newsletter = models.ForeignKey(Newsletter, related_name='allegati', on_delete=models.CASCADE)

    def get_filename(self):
        return self.file_obj.name.replace('newsletter/', '')

    def __str__(self):
        return "%s @ %s" % (self.file_obj.url, unicode(self.newsletter))

    class Meta:
        verbose_name_plural = "Allegati newsletter"
        ordering = ['-newsletter']


class Banca(models.Model):
    nome = models.CharField(max_length=100)
    iban = models.CharField(max_length=50)
    
    def __str__(self):
        return self.nome

    class Meta:
        verbose_name_plural = "Banche"
        ordering = ['nome']

        
#
# Gestione offerte
#



from wagtail.admin.forms import WagtailAdminModelForm
class OffertaAdminForm(WagtailAdminModelForm):
    """Limita la scelta degli indirizzi al cliente selezionato"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['indirizzo'].queryset = Indirizzo.objects.filter(cliente=self.instance.cliente)

    
class Offerta(index.Indexed, Orderable, PreviewableMixin, RevisionMixin, ClusterableModel):

    PERCENTUALI_CESSIONE = (
        (0, 'Nessuna'),
        (50, '50%'),
        (65, '65%'),
    )

    BANCHE = (
        (0, 'Non mostrare'),
        (1, 'Banca di Cividale'),
        (2, 'Unicredit'),
    )

    """Dati principali di un'offerta"""
    titolo = models.CharField(max_length=100, verbose_name="Titolo")
    numero_documento = models.CharField(max_length=50, verbose_name="N. offerta")
    confermata = models.BooleanField(default=False)
    cessione_credito_perc = models.IntegerField(verbose_name="Cessione credito", choices=PERCENTUALI_CESSIONE, default=0)
    data = models.DateField(default=datetime.now)
    cliente = ParentalKey(Cliente, related_name='offerte', on_delete=models.CASCADE)
    validita = models.IntegerField('Validità', default=30, blank=True, null=True, help_text="Validità dell’offerta in giorni")
    termine_consegna = models.IntegerField(blank=True, null=True)
    destinazione = models.TextField(blank=True, null=True, verbose_name="Consegna/Destinazione")
    indirizzo = models.ForeignKey('home.Indirizzo', blank=True, null=True, on_delete=models.SET_NULL, related_name='+')
    spedizione = models.CharField(verbose_name='Modalità spedizione', max_length=50, blank=True)
    pagamento = models.TextField(blank=True, null=True)
    agevolazione = models.TextField(verbose_name="Agevolazione fiscale", blank=True, null=True)
    mostra_banca = models.IntegerField(help_text="Mostrare le proprie coordinate bancarie?", default=1, choices=BANCHE)
    banca = models.ForeignKey(Banca, blank=True, null=True, on_delete=models.SET_NULL)
    nascondi_sconti = models.BooleanField(help_text="Nella stampa, nascondi gli sconti, mostrando solo i prezzi netti", default=False)
    nascondi_prezzi = models.BooleanField(help_text="Nella stampa, nascondi i singoli prezzi, mostrando solo i totali", default=False)
    nascondi_codici = models.BooleanField(help_text="Nella stampa, nascondi i codici degli articoli", default=False)
    mostra_totale = models.BooleanField(verbose_name="Mostra totale lordo", help_text="Mostra anche il totale al lordo della detrazione fiscale", default=False)
    esclusioni = models.TextField(blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    note_admin = models.TextField(blank=True, null=True, verbose_name="Note private")
    modello_presentazione = models.ForeignKey('home.ModelloPresentazioneOfferta', blank=True, null=True, on_delete=models.SET_NULL, related_name='+')
    presentazione = RichTextField(verbose_name="Testo di presentazione", blank=True, null=True)
    visibile = models.BooleanField(default=False, verbose_name="Visibile al cliente?")
    docs_da_firmare = models.ManyToManyField('home.DocumentoCompilato', blank=True, verbose_name="Documenti da firmare")

    content_panels = [
        FieldPanel('titolo'),
        FieldRowPanel([ 
            FieldPanel('cliente'),
            FieldPanel('visibile'),
            FieldPanel('numero_documento'),
        ]),


        FieldRowPanel([ 
            FieldPanel('data'),
            FieldPanel('validita'),
            FieldPanel('termine_consegna'),
        ]),

        FieldRowPanel([ 
            FieldPanel('indirizzo'),
            FieldPanel('spedizione'),
        ]),
        FieldRowPanel([ 
            FieldPanel('pagamento'),
            FieldPanel('agevolazione'),
        ]),

        FieldRowPanel([ 
            FieldPanel('cessione_credito_perc'),
            FieldPanel('mostra_banca'),
            FieldPanel('nascondi_sconti'),
            FieldPanel('nascondi_prezzi'),
            FieldPanel('mostra_totale'),
        ]),



        FieldPanel('esclusioni'),
        FieldPanel('note'),
        FieldPanel('note_admin'),

        FieldPanel('confermata'),


    ]

    presentation_panels = [
        FieldPanel('modello_presentazione'),
        FieldPanel('presentazione', classname="full"),
    ]

    allegati_panels = [
        FieldPanel('docs_da_firmare', widget=forms.CheckboxSelectMultiple),
        InlinePanel('allegati', label="Allegati"),
    ]

    rows_panels = [
        InlinePanel('righe', label="Righe"),
    ]

    edit_handler = TabbedInterface([
        ObjectList(content_panels, heading='Dati generali'),
        ObjectList(rows_panels, heading='Righe'),
        ObjectList(presentation_panels, heading='Presentazione'),
        ObjectList(allegati_panels, heading='Allegati'),
    ])

    search_fields = [
        index.SearchField('titolo'),
        index.AutocompleteField('titolo', null=True),
        index.SearchField('cliente__ragsoc'),
        index.AutocompleteField('cliente__ragsoc', null=True),
    ]

    base_form_class = OffertaAdminForm

    def get_preview_template(self, request, mode_name):
        return "home/offerta.html"
      
    class Meta:
        verbose_name_plural = "Offerte"
        ordering = ['-data']
        permissions = (
            ("view_offer_private_note", "Vedere le note private delle offerte"),
        )


    # def to_json(self):
    #     import json
    #     from datetime import date

    #     data = {
    #         'titolo': self.titolo,
    #         'numero_documento': self.numero_documento,
    #         'data': self.data.strftime('%d-%m-%Y'),
    #         'validita': self.validita,
    #         'termine_consegna': self.termine_consegna,
    #         'destinazione': self.destinazione,
    #         'spedizione': self.spedizione,
    #         'pagamento': self.pagamento,
    #         'agevolazione': self.agevolazione,
    #         'mostra_banca': self.mostra_banca,
    #         'banca': self.banca.nome if self.banca else '',
    #         'cessione_credito_perc': self.cessione_credito_perc,
    #         'nascondi_sconti': self.nascondi_sconti,
    #         'nascondi_prezzi': self.nascondi_prezzi,
    #         'mostra_totale': self.mostra_totale,
    #         'esclusioni': self.esclusioni,
    #         'note': self.note,
    #         'note_admin': self.note_admin,
    #         'confermata': self.confermata,
    #         'cliente': self.cliente.ragsoc,
    #         'righe': [r.to_json() for r in self.righe.all()],
    #         'allegati': [a.to_json() for a in self.allegati.all()],
    #     }

    #     return data#json.dumps(data, ensure_ascii=False, cls=DecimalEncoder)


    def __str__(self):
        return "%s del %s" % (self.titolo, self.data.strftime('%d.%m.%Y'))


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.numero_documento = datetime.now().strftime('%H%M%d%m%Y')

    @property
    def riepilogo(self):
        from collections import defaultdict

        totale_imponibile = totale_iva = totale_offerta = max_sconti = 0
    # Calcolo riepilogo IVA
        riepilogo_iva_dict = defaultdict(int)
        riepilogo_iva = []
        max_sconti = 0

        for rigo in self.righe.all():
            if rigo.sconto1:
                max_sconti = max(max_sconti, 1)
            if rigo.sconto2:
                max_sconti = max(max_sconti, 2)
            if rigo.sconto3:
                max_sconti = max(max_sconti, 3)
            if rigo.sconto4:
                max_sconti = max(max_sconti, 4)
            
            aliquota = rigo.aliquota_iva
            riepilogo_iva_dict[aliquota] += rigo.prezzo_totale

        aliquote = riepilogo_iva_dict.keys()
     #   aliquote.sort(lambda x,y:cmp(x.isdigit() and int(x) or 0, y.isdigit() and int(y) or 0))
     #   aliquote.reverse()

        totali = {}
        for aliquota in aliquote:
            try:
                aliquota_int = int(aliquota)
            except:
                aliquota_int = 0
            rigo_iva = {'aliquota':aliquota, 'imponibile':riepilogo_iva_dict[aliquota], 'iva':riepilogo_iva_dict[aliquota] * aliquota_int / 100}
            riepilogo_iva.append(rigo_iva)
            totale_imponibile += rigo_iva['imponibile']
            totale_iva += rigo_iva['iva']        

        # Calcolo IVA mista
        riepilogo_iva_mista_dict = {'ALT': 0, 'MBS':0, 'SIG':0}
        riepilogo_iva_tot = {'ALT': 0, 'MBS':0, 'SIG':0}
        has_iva_mista = False

        for rigo in self.righe.all():

            if rigo.aliquota_iva in ('ALT', 'MAB'):
                riepilogo_iva_tot['ALT'] += rigo.prezzo_totale
            elif rigo.aliquota_iva == 'MBS':
                riepilogo_iva_tot['MBS'] += rigo.prezzo_totale
            elif rigo.aliquota_iva == 'SIG':
                riepilogo_iva_tot['SIG'] += rigo.prezzo_totale
                has_iva_mista = True


        riepilogo_iva_mista_dict['ALT'] = riepilogo_iva_tot['ALT']
        riepilogo_iva_mista_dict['MBS'] = min(riepilogo_iva_tot['MBS'] * 2, totale_imponibile - riepilogo_iva_tot['ALT'])
        riepilogo_iva_mista_dict['SIG'] = riepilogo_iva_tot['SIG'] + riepilogo_iva_tot['MBS'] - riepilogo_iva_mista_dict['MBS']

        if has_iva_mista:
            riepilogo_iva = [
                {'imponibile': riepilogo_iva_mista_dict['SIG'], 'aliquota': 22, 'iva': riepilogo_iva_mista_dict['SIG'] * 22 / 100},
                {'imponibile': riepilogo_iva_mista_dict['MBS'], 'aliquota': 10, 'iva': riepilogo_iva_mista_dict['MBS'] * 10 / 100},            
                {'imponibile': riepilogo_iva_mista_dict['ALT'], 'aliquota': 10, 'iva': riepilogo_iva_mista_dict['ALT'] * 10 / 100},            
                ]
            totale_iva = sum([r['iva'] for r in riepilogo_iva])

        totale_offerta = float(totale_imponibile + totale_iva)

        return {
            'totale_imponibile': totale_imponibile,
            'totale_iva': totale_iva,
            'totale_offerta': totale_offerta,
            'max_sconti': max_sconti,
            'riepilogo_iva': riepilogo_iva,
            }





UNITA_MISURA = (
    (u'Q.tà', 'Quantità'),
    ('PZ', 'Pezzi'),
    ('m', 'Metri'),
    ('m2', 'Metri quadri'),
    ('m3', 'Metri cubi'),
    ('l', 'Litri'),
    ('h', 'Ore'),
)

TIPO_FATTURAZIONE = (
    ('L', 'Fatturazione Lazzari'),
    ('F', 'Fatturazione fornitore')
)

# 28.6.2021 - calcolo IVA mista per beni significativi
ALIQUOTE_IVA = (
    ('22', '22%'),
    ('10', '10%'),
    ('4', '4%'),
    ('Esente', 'Esente'),
    ('Esclusa', 'Esclusa'),
    ('SIG', 'Bene significativo e accessori'),
    ('MBS', "Manodopera per beni significativi"),
    ('MAB', "Manodopera per altri beni"),
    ('ALT', "Altri beni IVA 10%"),
)

# CATEGORIE_IVA = (
#     ('', '---'),
#     ('SIG', 'Bene significativo e accessori'),
#     ('MAN', "Manodopera e componenti"),
#     ('ALT', "Altri beni IVA 10%"),
# )


class DocumentoCompilato(ClusterableModel):
    """documento compilato automaticamente"""
    documento = models.ForeignKey('wagtaildocs.Document', on_delete=models.CASCADE, related_name='+')

    panels = [
        FieldPanel('documento'),
        InlinePanel('campi', label="Campi compilabili"),
    ]

    def __str__(self):
        return self.documento.title
    
    class Meta:
        verbose_name_plural = "Documenti compilabili"
    

class CampoCompilabile(models.Model):
    """Campo compilabile automaticamente"""

    AVAILABLE_FIELDS = (
        ('cliente.ragsoc', 'Nome cliente'),
        ('cliente.indirizzo_completo', 'Indirizzo completo'),
        ('cliente.cf_piva', 'CF o P: IVA'),
        ('cliente.luogo_data', 'Luogo e data di oggi')
    )



    campo = models.CharField(max_length=200, choices=AVAILABLE_FIELDS)
    n_pagina = models.IntegerField(default=1, verbose_name="N. di pagina")
    posizione_x = models.FloatField(default=0, verbose_name="Posizione X", help_text="Distanza in cm dal margine sinistro")
    posizione_y = models.FloatField(default=0, verbose_name="Posizione Y", help_text="Distanza in cm dal margine inferiore")
    documento = ParentalKey(DocumentoCompilato, on_delete=models.CASCADE, related_name='campi')

    panels = [
        FieldRowPanel([
            FieldPanel('campo'),
            FieldPanel('n_pagina'),
        ]),
        FieldRowPanel([
            FieldPanel('posizione_x'),
            FieldPanel('posizione_y'),
        ]),
    ]


    def __str__(self):
        return self.campo
    
    class Meta:
        verbose_name_plural = "Campi compilabili"
        ordering = ['n_pagina', '-posizione_y', 'posizione_x']



class AllegatoOfferta(models.Model):
    """Allegati a una offerta"""
    documento  = models.ForeignKey('wagtaildocs.Document', on_delete=models.CASCADE, related_name='+')
    offerta = ParentalKey(Offerta, related_name='allegati', on_delete=models.CASCADE)

    def __str__(self):
        return self.documento.title
    
    class Meta:
        verbose_name_plural = "Allegati offerta"




class ModelloPresentazioneOfferta(models.Model):
    """Modello di Allegati a una offerta"""
    titolo = models.CharField(max_length=200)
    testo = RichTextField()

    def __str__(self):
        return self.titolo

    panels = [
        FieldPanel('titolo'),
        FieldPanel('testo'),
    ]

    class Meta:
        verbose_name_plural = "Presentazioni standard offerte"
        ordering = ['titolo']


class CodiceRigoInput(forms.TextInput):
    input_type = 'text'
 #   template_name = 'sito/widgets/codice_rigo_input.html'

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['codice'] = value
        return context

    class Media:
        js = ('js/customer_detail.js',)




class RigoOfferta(Orderable):
    """Righi di un'offerta"""
    from .widgets import WagtailSelect2TextInput

    offerta = ParentalKey(Offerta, related_name='righe', on_delete=models.CASCADE)
    sort_order = models.IntegerField(blank=True, default=0, db_column='ordine')
    codice = models.CharField(max_length=50, blank=True)
    immagine = models.ForeignKey(
        'wagtailimages.Image', on_delete=models.SET_NULL, related_name='+',
        verbose_name="Foto", null=True, blank=True
    )
    descrizione = models.TextField()
    um = models.CharField(max_length=4, choices=UNITA_MISURA, default=u'Q.tà')
    quantita = models.DecimalField('Quantità', max_digits=7, decimal_places=3, default=1)
    prezzo = models.DecimalField(default=0, max_digits=7, decimal_places=2)
    sconto1 = models.DecimalField(blank=True, null=True, max_digits=4, decimal_places=1)
    sconto2 = models.DecimalField(blank=True, null=True, max_digits=4, decimal_places=1)
    sconto3 = models.DecimalField(blank=True, null=True, max_digits=4, decimal_places=1)
    sconto4 = models.DecimalField(blank=True, null=True, max_digits=4, decimal_places=1)
    aliquota_iva = models.CharField(max_length=10, choices=ALIQUOTE_IVA, default='22')
    fatturazione = models.CharField(max_length=1, choices=TIPO_FATTURAZIONE, default='L')
    speciale = models.BooleanField("Speciale?", default=False, help_text="Voce speciale in evidenza (es. spese di spedizione)")
    colore = models.CharField(max_length=10, blank=True, help_text="Colore di sfondo per la riga (es. #ff0000)")
#    categoria_iva = models.CharField(max_length=3, choices=CATEGORIE_IVA, default='', blank=True)

    def __str__(self):
        return "%s - %s" % (self.offerta, self.descrizione)
    
    @property
    def prezzo_netto(self):
        prezzo_netto = self.prezzo
        if self.sconto1:
            prezzo_netto = prezzo_netto * (100 - self.sconto1) / 100
        if self.sconto2:
            prezzo_netto = prezzo_netto * (100 - self.sconto2) / 100
        if self.sconto3:
            prezzo_netto = prezzo_netto * (100 - self.sconto3) / 100
        if self.sconto4:
            prezzo_netto = prezzo_netto * (100 - self.sconto4) / 100
        return prezzo_netto
    

    @property
    def prezzo_totale(self):
        return self.prezzo_netto * self.quantita
    

    def to_json(self):
        return {
            'codice': self.codice,
            'immagine': self.immagine.get_rendition('fill-100x100').url if self.immagine else '',
            'descrizione': self.descrizione,
            'um': self.um,
            'quantita': self.quantita,
            'prezzo': self.prezzo,
            'sconto1': self.sconto1,
            'sconto2': self.sconto2,
            'sconto3': self.sconto3,
            'sconto4': self.sconto4,
            'aliquota_iva': self.aliquota_iva,
            'fatturazione': self.fatturazione,
            'speciale': self.speciale,
            'colore': self.colore,
            'prezzo_netto': self.prezzo_netto,
            'prezzo_totale': self.prezzo_totale,
        }

    panels = [
        FieldRowPanel([
            FieldPanel('codice', widget=WagtailSelect2TextInput),
            FieldPanel('immagine'),
        ]),
        FieldPanel('descrizione'),
        FieldRowPanel([
            FieldPanel('um'),
            FieldPanel('quantita'),
            FieldPanel('prezzo'),
        ]),
        FieldRowPanel([
            FieldPanel('sconto1'),
            FieldPanel('sconto2'),
            FieldPanel('sconto3'),
            FieldPanel('sconto4'),
        ]),
        FieldRowPanel([
            FieldPanel('aliquota_iva'),
            FieldPanel('fatturazione'),
            NativeColorPanel('colore'),
        ]),
    ]

    class Meta:
        verbose_name = "Rigo offerta"
        verbose_name_plural = "Righi offerta"
        ordering = ['offerta', 'sort_order', 'speciale']



class Indirizzo(Orderable):
    cliente = ParentalKey(Cliente, related_name='indirizzi', on_delete=models.CASCADE)
    indirizzo = models.CharField(max_length=200, blank=True)
    cap = models.CharField('CAP', blank=True, max_length=5)
    citta = models.CharField('Città', blank=True, max_length=200)
    provincia = models.CharField(blank=True, max_length=2)
    stato = models.CharField(max_length=100, default='Italia')

    panels = [
        FieldRowPanel([
            FieldPanel('indirizzo'),
            FieldPanel('citta'),
        ]),
        FieldRowPanel([
            FieldPanel('cap'),
            FieldPanel('provincia'),
            FieldPanel('stato'),
        ]),
    ]

    def __str__(self):
        return "%s - %s" % (self.indirizzo, self.citta)
    
    class Meta:
        verbose_name = "Indirizzo aggiuntivo"
        verbose_name_plural = "Indirizzi aggiuntivi"





class Listino(models.Model):
    nome = models.CharField(max_length=100)
    file = models.FileField('File', upload_to='listini')
    marchio = models.CharField(max_length=50)
    data = models.DateField(auto_now_add=True)
    attivo = models.BooleanField(default=True)


    @property
    def totale_prodotti(self):
        return self.prodotti.count()

    def __str__(self):
        if self.data:
            return "%s %s del %s" % (self.nome, self.marchio, self.data.strftime('%d.%m.%Y'))
        else:
            return "%s %s" % (self.nome, self.marchio)
    
    class Meta:
        verbose_name = "Listino"
        verbose_name_plural = "Listini"
        ordering = ('-attivo', '-data', 'marchio')






class Prodotto(index.Indexed, models.Model):
    codice = models.CharField(max_length=50, blank=True)
    descrizione = models.TextField()
    prezzo = models.DecimalField(default=0, max_digits=7, decimal_places=2)
    attivo = models.BooleanField(default=True)
    listino = models.ForeignKey(Listino, blank=True, null=True, on_delete=models.SET_NULL, related_name='prodotti')
    

    search_fields = [
        index.AutocompleteField('codice'),
        index.AutocompleteField('descrizione'),
    ]

    def to_json(self):
        return {
            'codice': self.codice,
            'descrizione': self.descrizione,
            'prezzo': self.prezzo,
        }


    def __str__(self):
        return self.descrizione
    
    class Meta:
        verbose_name = "Prodotto"
        verbose_name_plural = "Prodotti"
        ordering = ('listino', 'descrizione')
        
        
#
# Estensione maggio 2018 - Attività clienti
#

class Agente(models.Model):
    """Qualcuno che fa un'attività per un cliente"""
    nome = models.CharField(max_length=100)
    attivo = models.BooleanField(default=True)
    
    def __str__(self):
        return self.nome

    class Meta:
        verbose_name_plural = "Agenti"

        
class TipoAttivita(models.Model):
    """Attività che si possono fare per un cliente"""
    nome = models.CharField(max_length=100)
    
    def __str__(self):
        return self.nome

    class Meta:
        ordering = ('nome',)
        verbose_name = "Tipo di attività"
        verbose_name_plural = "Tipi di attività"
        
        
class Attivita(models.Model):
    """Un'attività svolta per un cliente (telefonata, visita, preventivo)"""
    cliente = ParentalKey(Cliente, related_name="attivita", on_delete=models.CASCADE)
    data = models.DateField(default=datetime.now)
    ora = models.TimeField(blank=True, null=True, default=datetime.now)
    dataora = models.DateTimeField(auto_now_add=True)
    tipo = models.ForeignKey(TipoAttivita, blank=True, null=True, on_delete=models.SET_NULL)
    descrizione = models.TextField(blank=True, null=True)
    agente = models.ForeignKey(Agente, blank=True, null=True, on_delete=models.SET_NULL, default=4) # "agente" nel senso di colui che agisce, che fa l'attività indicata
    
    panels = [
        FieldRowPanel([
            FieldPanel('data'),
            FieldPanel('ora'),
            FieldPanel('tipo'),
            FieldPanel('agente'),
        ]),
        FieldPanel('descrizione'),
    ]

    def __str__(self):
        return "%s %s %s" % (self.data.strftime('%d.%m.%Y'), self.tipo, self.cliente)
    
    
    class Meta:
        verbose_name = "Attività"
        verbose_name_plural = "Attività"
        ordering = ('-data', '-ora')

        
class Variazione(models.Model):
    descrizione = models.TextField()
    data = models.DateTimeField(auto_now_add=True)
    cliente = models.ForeignKey(Cliente, related_name="variazioni", on_delete=models.CASCADE)


    def __str__(self):
        return "%s %s" % (self.data.strftime('%d.%m.%Y'), self.cliente)
    
    class Meta:
        verbose_name_plural = "Variazioni"
        ordering = ('-data',)







class Provincia(models.Model):
    nome = models.CharField(max_length=100)
    sigla = models.CharField(max_length=2)
    
    def __str__(self):
        return self.nome or self.sigla

    class Meta:
        verbose_name_plural = "Province"
        ordering = ('nome', 'sigla')


class Comune(index.Indexed, models.Model):
    nome = models.CharField(max_length=100)
    cap = models.CharField(max_length=5)
    provincia = models.ForeignKey(Provincia, on_delete=models.CASCADE)
    

    search_fields = [
        index.SearchField('nome'),
    ]

    def to_json(self):
        return {
            'nome': self.nome,
            'cap': self.cap,
            'provincia': self.provincia.sigla,
        }

    def __str__(self):
        return "%s (%s)" % (self.nome, self.provincia.sigla)

    class Meta:
        verbose_name_plural = "Comuni"
        ordering = ('nome',)