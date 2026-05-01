from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.validators import RegexValidator


# Modelo principal del inventario.
# Representa cada vehículo publicado en la plataforma con sus datos técnicos,
# comerciales y administrativos.
class Stock(models.Model):
    """Almacena la ficha completa de un vehículo en stock."""

    # Datos identificativos del vehículo.
    Titulo = models.CharField(max_length=100)
    Matricula = models.CharField(max_length=16, blank=True, null=True)
    VIN = models.CharField(
        max_length=17,
        blank=True,
        null=True,
        validators=[RegexValidator(regex=r'^[A-HJ-NPR-Z0-9]{17}$', message='VIN inválido (17 caracteres alfanuméricos, sin I, O, Q).')]
    )

    # Descripción libre y fechas de control interno.
    Descrepción = models.TextField(blank=True)
    Fecha_de_creación = models.DateTimeField(auto_now_add=True)
    Ultima_actualización = models.DateTimeField(auto_now=True)

    # Datos técnicos y de catálogo.
    Año = models.PositiveSmallIntegerField(validators=[ MinValueValidator(1000), MaxValueValidator(9999) ])
    Kilometros = models.PositiveIntegerField(blank=True, null=True, validators=[MinValueValidator(0)])
    Versión = models.CharField(max_length=80, blank=True, null=True)
    Carrocería = models.CharField(max_length=50, blank=True, null=True)
    Puertas = models.PositiveSmallIntegerField(blank=True, null=True, validators=[MinValueValidator(1), MaxValueValidator(9)])
    Tracción = models.CharField(max_length=50, blank=True, null=True)
    Fecha_matriculación = models.CharField(max_length=30, blank=True, null=True)
    Marca = models.CharField(max_length=50)
    Modelo = models.CharField(max_length=50)
    Motor = models.DecimalField(max_digits=5, decimal_places=2)
    Transmisión = models.CharField(max_length=50)
    Combustible = models.CharField(max_length=50)
    color= models.CharField(max_length=30)

    # Datos de venta y relación con el usuario que creó la ficha.
    Precio = models.DecimalField(max_digits=10, decimal_places=2)
    Vendido = models.BooleanField(default=False)
    Usario = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    Foto = models.ImageField(upload_to='car_photos/', blank=True, null=True)

    def __str__(self):
        """Devuelve el nombre legible del vehículo para admin y listados."""
        return self.Marca + " " + self.Modelo + " (" + str(self.Año) + ")"

    def precio_formateado(self): 
        """Formatea el precio sin decimales para mostrarlo en la interfaz."""
        valor = float(self.Precio) 
        return f"{valor:,.0f}".replace(",", " ")


# Modelo de galería.
# Permite asociar varias imágenes adicionales a un mismo vehículo y mantener
# su orden de visualización.
class StockImage(models.Model):
    """Guarda imágenes secundarias de un vehículo para la galería."""

    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='car_photos/gallery/')
    orden = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Las imágenes se muestran primero por orden manual y luego por id.
        ordering = ['orden', 'id']

    def __str__(self):
        """Identifica una imagen por su vehículo asociado y su id."""
        return f"Imagen {self.stock_id} - {self.id}"


# Modelo de contacto.
# Registra los mensajes enviados desde el formulario de contacto de la web.
class ContactMessage(models.Model):
    """Almacena mensajes enviados por usuarios o visitantes desde contacto."""

    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        # Los mensajes más recientes aparecen primero.
        ordering = ['-created_at']

    def __str__(self):
        """Resume el mensaje con asunto, remitente y fecha."""
        return f"{self.subject} - {self.name} ({self.created_at.strftime('%d/%m/%Y')})"


# Modelo de solicitud de prueba.
# Relaciona a un interesado con un vehículo y una fecha/hora propuesta.
class TestDriveRequest(models.Model):
    """Registra peticiones de prueba de conducción sobre un vehículo."""

    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='test_drive_requests')
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    preferred_date = models.CharField(max_length=40, blank=True)
    preferred_datetime = models.DateTimeField(blank=True, null=True)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        # Se priorizan las solicitudes más recientes en el panel interno.
        ordering = ['-created_at']

    def __str__(self):
        """Devuelve un resumen legible de la solicitud registrada."""
        return f"Prueba {self.stock_id} - {self.name} ({self.created_at.strftime('%d/%m/%Y')})"


# Modelo de favoritos.
# Permite que cada usuario guarde vehículos concretos para consultarlos más tarde.
class Favorite(models.Model):
    """Representa la relación de favorito entre un usuario y un vehículo."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Los favoritos nuevos aparecen primero y se evita duplicar la relación usuario-vehículo.
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'stock'], name='unique_user_stock_favorite')
        ]

    def __str__(self):
        """Identifica el favorito mediante el usuario y el vehículo relacionados."""
        return f"Favorito {self.user_id} - {self.stock_id}"
