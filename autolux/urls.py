"""
URL configuration for autolux project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path, re_path
from Web import views
from Web.sitemaps import StaticViewSitemap, StockSitemap
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve


sitemaps = {
    'static': StaticViewSitemap,
    'stock': StockSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('ckeditor5/', include('django_ckeditor_5.urls')),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', views.robots_txt, name='robots_txt'),
    path('',  views.home, name='home'),
    path('contacto/',  views.contact, name='contact'),
    path('mensajes-contacto/',  views.contact_messages_admin, name='contact_messages_admin'),
    path('signup/',  views.signup, name='signup'),
    path('login/',  views.signin, name='login'),
    path('logout/',  views.signout, name='logout'),
    path('stock/',  views.stock_view, name='stock'),
    path('comparar/', views.compare_view, name='compare'),
    path('favoritos/',  views.favorites_view, name='favorites'),
    path('favoritos/toggle/<int:stock_id>/', views.toggle_favorite, name='toggle_favorite'),
    path('stock/add/',  views.addstock, name='addstock'),
    path('stock/<int:stock_id>/edit/', views.editstock, name='editstock'),
    path('stock/lookup/', views.vehicle_lookup, name='vehicle_lookup'),
    path('item/<int:stock_id>/available-slots/', views.test_drive_available_slots, name='test_drive_available_slots'),
    path('item/<int:stock_id>/', views.item_page, name='item_page'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]
