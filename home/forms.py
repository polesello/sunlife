from django import forms
from .models import Listino

class ListinoForm(forms.ModelForm):
    
    class Meta:
        model = Listino
        fields = '__all__'