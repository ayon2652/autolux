from django import forms
from .models import Stock   # o el nombre real de tu modelo

class StockForm(forms.ModelForm):
    class Meta:
        model = Stock
        fields = [
            'Titulo',
            'Descrepción',
            'Año',
            'Marca',
            'Modelo',
            'Motor',
            'Transmisión',
            'Combustible',
            'color',
            'Precio',
            'Foto',
        ]
