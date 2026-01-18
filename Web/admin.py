from django.contrib import admin
from .models import Stock

class StockAdmin(admin.ModelAdmin):
    list_display = ('Marca', 'Modelo', 'Año', 'Precio', 'Vendido')
    list_filter = ('Vendido', 'Año', 'Marca')
    search_fields = ('Titulo', 'Marca', 'Modelo', 'Año')
    readonly_fields = ('Fecha_de_creación', 'Ultima_actualización')
# Register your models here.
admin.site.register(Stock, StockAdmin)
