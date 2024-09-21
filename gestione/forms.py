from django import forms
from home.models import Gruppo, TipoRichiesta, Segnalazione

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit
from crispy_bootstrap5.bootstrap5 import FloatingField
from crispy_forms.bootstrap import StrictButton


class ClienteSearchForm(forms.Form):
    query = forms.CharField(label='Cerca cliente', max_length=100, required=False)
    gruppo = forms.ModelChoiceField(queryset=Gruppo.objects.all(), empty_label='Tutti i gruppi', required=False)
    intervento = forms.ModelChoiceField(queryset=TipoRichiesta.objects.all(), empty_label='Tutti gli interventi', required=False)
    segnalazione = forms.ModelChoiceField(queryset=Segnalazione.objects.all(), empty_label='Tutte le segnalazioni', required=False)
    prodotto = forms.CharField(label='Prodotto', max_length=100, required=False)


    def __init__(self, *args, **kwargs):
        super(ClienteSearchForm, self).__init__(*args, **kwargs)
        # crispy forms
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.layout = Layout(
            Row(
                Column(FloatingField('query'), css_class='col-md-4'),
                Column(FloatingField('gruppo'), css_class='col-md-4'),
                Column(FloatingField('intervento'), css_class='col-md-4'),
                Column(FloatingField('segnalazione'), css_class='col-md-4'),
                Column(FloatingField('prodotto'), css_class='col-md-4'),
                Column(
                    StrictButton('<i class="fas fa-search"></i> Cerca', css_class='btn btn-primary d-block w-100 h-100', type='submit'),
                    css_class='col-md-4 pb-3',
                )
            ),
        )

