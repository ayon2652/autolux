from django.contrib import admin
from .models import Stock, ContactMessage, TestDriveRequest, Favorite

class StockAdmin(admin.ModelAdmin):
    list_display = ('Marca', 'Modelo', 'Año', 'Precio', 'Vendido')
    list_filter = ('Vendido', 'Año', 'Marca')
    search_fields = ('Titulo', 'Marca', 'Modelo', 'Año')
    readonly_fields = ('Fecha_de_creación', 'Ultima_actualización')

class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'name', 'email', 'created_at', 'is_read')
    list_filter = ('is_read', 'created_at')
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('created_at', 'name', 'email', 'phone', 'subject', 'message')
    
    def has_add_permission(self, request):
        return False


class TestDriveRequestAdmin(admin.ModelAdmin):
    list_display = ('stock', 'name', 'email', 'phone', 'preferred_date', 'created_at', 'is_read')
    search_fields = ('name', 'email', 'phone', 'stock__Titulo', 'stock__Marca', 'stock__Modelo')
    list_filter = ('is_read', 'created_at',)
    readonly_fields = ('stock', 'name', 'email', 'phone', 'preferred_date', 'message', 'created_at', 'is_read')

    def has_add_permission(self, request):
        return False


class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'stock', 'created_at')
    search_fields = ('user__username', 'stock__Titulo', 'stock__Marca', 'stock__Modelo')
    list_filter = ('created_at',)
    readonly_fields = ('user', 'stock', 'created_at')

    def has_add_permission(self, request):
        return False

# Register your models here.
admin.site.register(Stock, StockAdmin)
admin.site.register(ContactMessage, ContactMessageAdmin)
admin.site.register(TestDriveRequest, TestDriveRequestAdmin)
admin.site.register(Favorite, FavoriteAdmin)
