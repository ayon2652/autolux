from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django_ckeditor_5.widgets import CKEditor5Widget
from django.utils.html import strip_tags
from PIL import Image, UnidentifiedImageError
import os
from .models import Stock


# Widget personalizado para mostrar los textos del input de imagen en español.
class SpanishClearableFileInput(forms.ClearableFileInput):
    initial_text = 'Imagen actual'
    input_text = 'Cambiar imagen'
    clear_checkbox_label = 'Eliminar imagen principal'


# Widget que habilita selección múltiple de archivos en el formulario.
class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


# Campo personalizado que permite procesar varias imágenes a la vez.
class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        """Valida uno o varios archivos y devuelve siempre una lista limpia."""
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(file_item, initial) for file_item in data]
        if data:
            return [single_file_clean(data, initial)]
        return []


# Formulario principal para crear y editar vehículos del inventario.
# Además de los campos del modelo, añade soporte para múltiples fotos de galería
# y validaciones de seguridad sobre imágenes subidas.
class StockForm(forms.ModelForm):
    """Formulario de gestión de vehículos con validación de imágenes y ayuda visual."""

    # Campo adicional que no pertenece directamente al modelo Stock.
    # Se usa para subir varias imágenes a la galería del vehículo.
    Fotos = MultipleFileField(required=False)

    # Extensiones y tipos MIME permitidos para reducir subidas inválidas o peligrosas.
    ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}
    ALLOWED_IMAGE_MIME_TYPES = {
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/bmp',
        'image/webp',
        'image/tiff',
    }

    class Meta:
        # Modelo y campos gestionados por el formulario principal.
        model = Stock
        fields = [
            'Titulo',
            'Matricula',
            'VIN',
            'Descrepción',
            'Año',
            'Kilometros',
            'Versión',
            'Carrocería',
            'Puertas',
            'Tracción',
            'Fecha_matriculación',
            'Marca',
            'Modelo',
            'Motor',
            'Transmisión',
            'Combustible',
            'color',
            'Precio',
            'Foto',
        ]

        # Widgets personalizados para mejorar usabilidad y control de entrada.
        widgets = {
            'Descrepción': CKEditor5Widget(config_name='autolux_full'),
            'Matricula': forms.TextInput(attrs={
                'placeholder': 'Ej: 1234ABC',
                'maxlength': 16,
                'autocomplete': 'off',
            }),
            'VIN': forms.TextInput(attrs={
                'placeholder': 'Ej: WVWZZZ1KZAW000001',
                'maxlength': 17,
                'autocomplete': 'off',
            }),
            'Año': forms.NumberInput(attrs={
                'type': 'number',
                'inputmode': 'numeric',
                'min': 1000,
                'max': 9999,
                'step': 1,
                'placeholder': 'Ej: 2020',
            }),
            'Kilometros': forms.NumberInput(attrs={
                'type': 'number',
                'inputmode': 'numeric',
                'min': 0,
                'step': 1,
                'placeholder': 'Ej: 85000',
            }),
            'Puertas': forms.NumberInput(attrs={
                'type': 'number',
                'inputmode': 'numeric',
                'min': 1,
                'max': 9,
                'step': 1,
                'placeholder': 'Ej: 5',
            }),
            'Versión': forms.TextInput(attrs={
                'placeholder': 'Ej: 1.5 dCi Authentique',
            }),
            'Carrocería': forms.TextInput(attrs={
                'placeholder': 'Ej: SUV, berlina, compacto',
            }),
            'Tracción': forms.TextInput(attrs={
                'placeholder': 'Ej: delantera, trasera, total',
            }),
            'Fecha_matriculación': forms.TextInput(attrs={
                'placeholder': 'Ej: 04/07/2010',
            }),
            'Foto': SpanishClearableFileInput(attrs={
                'accept': 'image/*',
            }),
        }

        # Etiquetas visibles en la interfaz del formulario.
        labels = {
            'Titulo': 'Título comercial',
            'Matricula': 'Matrícula',
            'VIN': 'Número de bastidor (VIN)',
            'Descrepción': 'Descripción',
            'Año': 'Año',
            'Kilometros': 'Kilómetros',
            'Versión': 'Versión',
            'Carrocería': 'Carrocería',
            'Puertas': 'Puertas',
            'Tracción': 'Tracción',
            'Fecha_matriculación': 'Fecha de matriculación',
            'Marca': 'Marca',
            'Modelo': 'Modelo',
            'Motor': 'Motor',
            'Transmisión': 'Transmisión',
            'Combustible': 'Combustible',
            'color': 'Color',
            'Precio': 'Precio',
            'Foto': 'Imagen principal',
            'Fotos': 'Nuevas fotos para la galería',
        }

        # Textos de ayuda mostrados al usuario para orientar el uso de ciertos campos.
        help_texts = {
            'Foto': 'Esta imagen será la portada principal del vehículo.',
            'Fotos': 'Puedes seleccionar varias imágenes nuevas para añadirlas a la galería.',
            'Descrepción': 'Describe el estado, equipamiento y puntos fuertes del vehículo.',
        }

    def __init__(self, *args, **kwargs):
        """Aplica estilos CSS, placeholders y ajustes de ayuda al inicializar el formulario."""
        super().__init__(*args, **kwargs)

        # Añade clase CSS común a todos los campos para mantener consistencia visual.
        for name, field in self.fields.items():
            css_class = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = f'{css_class} form-control'.strip()

        # Define placeholders y textos de apoyo para hacer el formulario más claro.
        self.fields['Titulo'].widget.attrs.setdefault('placeholder', 'Ej: Volkswagen Golf 2.0 TDI Life')
        self.fields['Marca'].widget.attrs.setdefault('placeholder', 'Ej: Volkswagen')
        self.fields['Modelo'].widget.attrs.setdefault('placeholder', 'Ej: Golf')
        self.fields['Motor'].widget.attrs.setdefault('placeholder', 'Ej: 2.0')
        self.fields['Combustible'].widget.attrs.setdefault('placeholder', 'Ej: Diésel')
        self.fields['Transmisión'].widget.attrs.setdefault('placeholder', 'Ej: Automática')
        self.fields['color'].widget.attrs.setdefault('placeholder', 'Ej: Gris antracita')
        self.fields['Precio'].widget.attrs.setdefault('placeholder', 'Ej: 18990')
        self.fields['Fotos'].label = 'Nuevas fotos para la galería'
        self.fields['Fotos'].help_text = 'Selecciona una o varias imágenes para ampliar la galería actual.'
        self.fields['Fotos'].widget.attrs.update({
            'accept': 'image/*',
            'class': 'form-control',
        })

    def _max_upload_bytes(self):
        """Calcula el tamaño máximo permitido por archivo según settings."""
        max_mb = int(getattr(settings, 'MAX_IMAGE_UPLOAD_MB', 8))
        return max_mb * 1024 * 1024

    def _validate_image_file(self, uploaded_file, *, field_name):
        """Valida extensión, MIME, tamaño e integridad real de una imagen subida."""
        if not uploaded_file:
            return

        extension = os.path.splitext(uploaded_file.name or '')[1].lower()
        if extension not in self.ALLOWED_IMAGE_EXTENSIONS:
            raise ValidationError(f'El archivo de {field_name} debe ser una imagen válida (JPG, PNG, GIF, BMP, WEBP o TIFF).')

        content_type = (getattr(uploaded_file, 'content_type', '') or '').lower()
        if content_type and content_type not in self.ALLOWED_IMAGE_MIME_TYPES:
            raise ValidationError(f'El archivo de {field_name} no tiene un tipo MIME permitido.')

        if uploaded_file.size > self._max_upload_bytes():
            max_mb = int(getattr(settings, 'MAX_IMAGE_UPLOAD_MB', 8))
            raise ValidationError(f'El archivo de {field_name} supera el tamaño máximo permitido ({max_mb} MB).')

        try:
            uploaded_file.seek(0)
            image = Image.open(uploaded_file)
            image.verify()
        except (UnidentifiedImageError, OSError, ValueError):
            raise ValidationError(f'El archivo de {field_name} no es una imagen válida o está corrupto.')
        finally:
            uploaded_file.seek(0)

    def clean_Descrepción(self):
        """Elimina HTML del contenido enriquecido antes de guardarlo como texto limpio."""
        raw_value = self.cleaned_data.get('Descrepción') or ''
        sanitized_text = strip_tags(raw_value)
        return sanitized_text.strip()

    def clean_Foto(self):
        """Valida la imagen principal del vehículo."""
        photo = self.cleaned_data.get('Foto')
        self._validate_image_file(photo, field_name='imagen principal')
        return photo

    def clean_Fotos(self):
        """Valida todas las imágenes adicionales seleccionadas para la galería."""
        photos = self.cleaned_data.get('Fotos') or []
        for photo in photos:
            self._validate_image_file(photo, field_name='galería')
        return photos
