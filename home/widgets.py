from django_select2.forms import HeavySelect2Widget, ModelSelect2Widget, Select2Widget
from django import forms

class WagtailSelect2TextInput(forms.TextInput):
    
    data_url = '/prodotti/search/'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs['style'] = 'width:100%;'
        self.attrs['class'] = 'awesomplete'


    class Media:
        js = [
           # 'https://cdnjs.cloudflare.com/ajax/libs/select2/4.0.3/js/select2.full.js',
           # 'https://cdnjs.cloudflare.com/ajax/libs/select2/4.0.3/js/i18n/it.js',
         #   'https://my.sunlifegroup.it/static/manage/js/typeahead.min.js',

      #      'https://code.jquery.com/ui/1.12.1/jquery-ui.js',
                '/static/home/js/awesomplete.min.js',
             '/static/home/js/autocomplete.js',
       ]
        css = {
            'all': [
              # 'https://cdnjs.cloudflare.com/ajax/libs/select2/4.0.3/css/select2.min.css',
                '/static/home/css/awesomplete.css',

            ]
        }

    # def get_queryset(self):
    #     from .models import Prodotto
    #     return Prodotto.objects.all()


    # search_fields = [
    #     'codice__icontains',
    #     'descrizione__icontains',
    # ]
