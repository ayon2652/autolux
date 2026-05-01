from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Stock


class StaticViewSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return ['home', 'stock', 'contact']

    def location(self, item):
        return reverse(item)


class StockSitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.7

    def items(self):
        return Stock.objects.filter(Vendido=False).order_by('-Ultima_actualización', '-Fecha_de_creación')

    def lastmod(self, obj):
        return obj.Ultima_actualización or obj.Fecha_de_creación

    def location(self, obj):
        return reverse('item_page', args=[obj.pk])
