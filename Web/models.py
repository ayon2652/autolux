from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

# Create your models here.
class Stock(models.Model):
    Titulo = models.CharField(max_length=100)
    Descrepción = models.TextField(blank=True)
    Fecha_de_creación = models.DateTimeField(auto_now_add=True)
    Ultima_actualización = models.DateTimeField(auto_now=True)
    Año = models.PositiveSmallIntegerField(validators=[ MinValueValidator(1000), MaxValueValidator(9999) ])
    Marca = models.CharField(max_length=50)
    Modelo = models.CharField(max_length=50)
    Motor = models.DecimalField(max_digits=5, decimal_places=2)
    Transmisión = models.CharField(max_length=50)
    Combustible = models.CharField(max_length=50)
    color= models.CharField(max_length=30)
    Precio = models.DecimalField(max_digits=10, decimal_places=2)
    Vendido = models.BooleanField(default=False)
    Usario = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    Foto = models.ImageField(upload_to='car_photos/', blank=True, null=True)

    def __str__(self):
        return self.Marca + " " + self.Modelo + " (" + str(self.Año) + ")"
    def precio_formateado(self): 
        valor = float(self.Precio) 
        return f"{valor:,.0f}".replace(",", " ")
