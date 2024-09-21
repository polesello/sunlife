
class ClienteForm(BaseModelForm):
    
# Anziché ridefinire l'intero controllo, definisco solo un attributo del widget
    def __init__(self, azienda, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(ClienteForm, self).__init__(*args, **kwargs)
        
        if self.fields.has_key('piva'):
            self.fields['piva'].widget.attrs["pattern"] = "\d*"
        # Solo gruppi e segnalazioni dell'azienda autenticata
        
        if user.has_perm('sito.view_all_groups'):
            gruppi = Gruppo.objects.filter(azienda = azienda)
        else:
            gruppi = Gruppo.objects.filter(users = user)

        self.fields['gruppo'].queryset = gruppi
        self.fields['segnalazione'].queryset = Segnalazione.objects.filter(azienda=azienda)
# Non tutti possono vedere le note private
        if user and not user.has_perm('sito.view_client_private_note'):
            del self.fields['note_private']

        self.fields['richieste'].widget=forms.CheckboxSelectMultiple()
        self.fields['richieste'].queryset=TipoRichiesta.objects.all()

        users = User.objects.filter(azienda=azienda)
        self.fields['users'].widget=forms.CheckboxSelectMultiple()
        self.fields['users'].queryset = users

    class Meta:
        model = Cliente
        exclude = ['lat', 'lng', 'fax', 'fido', 'swift', 'foto', 'altro', 'vecchio_gruppo']

class ClientePrivatoForm(ClienteForm):

    class Meta:
        model = Cliente
        exclude = ['piva', 'swift', 'fido', 'foto', 'fax', 'pec', 'lat', 'lng', 'altro', 'vecchio_gruppo']


class ClienteInfoForm(forms.Form):
    """14.8.2020 - info aggiuntive variabili per il cliente,
    i campi sono creati nella view
    che vengono salvate in un campo JSON"""
    pass

        
class GruppoForm(BaseModelForm):

    class Meta:
        model = Gruppo
        fields = ['nome', 'logo', 'is_privato', 'parent', 'ordine', 'visibile', 'users']
        widgets = {
            'users': forms.CheckboxSelectMultiple(),
        }

        
        
class InformazioneUtenteForm(BaseModelForm):

    class Meta:
        model = InformazioneUtente
        exclude = ['azienda']



class PersonaForm(ModelForm):


    class Meta:
        model = Persona
        exclude = ['cliente', 'foto', 'ordine']
        widgets = {
            'nome': forms.TextInput(attrs={'class':'edit-mode'}),
            'telefono': forms.TextInput(attrs={'class':'edit-mode'}),
            'email': forms.EmailInput(attrs={'class':'edit-mode'}),
            'mansione': forms.TextInput(attrs={'class':'edit-mode'}),
        }



class CondizioneClienteForm(ModelForm):

    class Meta:
        model = CondizioneCliente
        exclude = ['cliente', 'condizione'] 




class CondizioneParticolareClienteForm(ModelForm):

    class Meta:
        model = CondizioneParticolareCliente
        exclude = ['cliente', 'marchio']

     
class FirmaNewsletterForm(ModelForm):   
    class Meta:
        model = FirmaNewsletter
        fields = '__all__'



class NewsletterForm(BaseModelForm):   
    class Meta:
        model = Newsletter
        exclude = ['data_aggiornamento', 'data_spedizione']     






class AllegatoNewsletterForm(ModelForm):
    class Meta:
        model = AllegatoNewsletter
        exclude = ['newsletter']




class RigoOffertaInlineForm(ModelForm):

    class Meta:
        model = RigoOfferta
        fields = ['codice', 'speciale', 'descrizione', 'um', 'quantita', 'prezzo', 'sconto1', 'sconto2', 'sconto3', 'sconto4','fatturazione','aliquota_iva']
        widgets = {
            'codice': forms.TextInput(attrs={'class':'medium-field autocomplete'}),
            'descrizione': forms.Textarea(attrs={'rows':'5', 'class':'autocomplete'}),
            'um': forms.Select(attrs={'class':'short-field'}),
            'quantita': forms.NumberInput(attrs={'class':'short-field'}),
            'prezzo': forms.NumberInput(attrs={'class':'short-field'}),
            'sconto1': forms.NumberInput(attrs={'class':'short-field'}),
            'sconto2': forms.NumberInput(attrs={'class':'short-field'}),
            'sconto3': forms.NumberInput(attrs={'class':'short-field'}),
            'sconto4': forms.NumberInput(attrs={'class':'short-field'}),
            'speciale': forms.CheckboxInput(attrs={'title':'Rigo in evidenza'}),
          #  'categoria_iva': forms.Select(attrs={'class':'short-field'}),
            'fatturazione': forms.Select(attrs={'class':'short-field'}),
        }


        
class ListinoForm(BaseModelForm):

    class Meta:
        model = Listino
        fields = ['nome', 'file', 'marchio', 'data', 'attivo']
