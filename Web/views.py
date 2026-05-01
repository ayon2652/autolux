from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate
from django.core.cache import cache
from django.db import IntegrityError
from django.db.models import Q, Case, When, IntegerField
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.urls import reverse
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import json
from .models import Stock, StockImage, ContactMessage, TestDriveRequest, Favorite
from .forms import StockForm
from django.utils.html import format_html, strip_tags
from django.utils import timezone
from django.contrib.auth.decorators import login_required # añadir encima de la funcion def para proteger el contenido de usuarios no autenticados
from django.views.decorators.http import require_POST
from datetime import datetime, date, time, timedelta


SITE_NAME = 'Autolux Ocasión'


# -----------------------------
# Utilidades SEO y URLs públicas
# -----------------------------
def _clean_seo_text(value, max_length=160):
    """Limpia texto HTML y lo recorta para usarlo en metadatos SEO."""
    cleaned = ' '.join(strip_tags(str(value or '')).split())
    if len(cleaned) <= max_length:
        return cleaned

    shortened = cleaned[: max_length - 1].rsplit(' ', 1)[0].strip()
    return f'{shortened or cleaned[: max_length - 1]}…'


def _absolute_image_url(request, image_field):
    """Convierte una imagen del modelo en una URL absoluta válida para SEO y sharing."""
    if image_field and hasattr(image_field, 'url'):
        return request.build_absolute_uri(image_field.url)
    return ''


def _absolute_url(request, value):
    """Devuelve una URL absoluta a partir de una ruta relativa o una URL completa."""
    if not value:
        return ''
    if str(value).startswith('http://') or str(value).startswith('https://'):
        return str(value)
    return request.build_absolute_uri(str(value))


def _build_seo_context(request, *, title, description, canonical_url=None, image_url='', robots='index,follow', og_type='website', json_ld=None):
    """Construye el contexto SEO común que usan las plantillas en cada vista."""
    canonical = canonical_url or request.build_absolute_uri(request.path)
    return {
        'seo_title': title,
        'seo_description': _clean_seo_text(description, max_length=170),
        'seo_canonical_url': canonical,
        'seo_og_url': canonical,
        'seo_image_url': _absolute_url(request, image_url),
        'seo_robots': robots,
        'seo_og_type': og_type,
        'seo_site_name': SITE_NAME,
        'seo_json_ld': json_ld,
    }


def _serialize_json_ld(*items):
    """Agrupa uno o varios bloques JSON-LD ignorando valores vacíos."""
    valid_items = [item for item in items if item]
    if not valid_items:
        return None
    if len(valid_items) == 1:
        return valid_items[0]
    return valid_items


# -----------------------------
# Utilidades de seguridad y sesión
# -----------------------------
def _get_client_ip(request):
    """Obtiene la IP real del cliente para control de intentos de login."""
    forwarded_for = (request.META.get('HTTP_X_FORWARDED_FOR') or '').strip()
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return (request.META.get('REMOTE_ADDR') or 'unknown').strip()


def _login_security_config():
    """Lee la configuración de bloqueo de login desde settings con valores por defecto."""
    return {
        'max_attempts': int(getattr(settings, 'LOGIN_MAX_ATTEMPTS', 5)),
        'fail_window_seconds': int(getattr(settings, 'LOGIN_FAIL_WINDOW_SECONDS', 900)),
        'lock_seconds': int(getattr(settings, 'LOGIN_LOCK_SECONDS', 900)),
    }


def _login_attempt_keys(request, username):
    """Genera claves de caché para registrar fallos y bloqueos por usuario e IP."""
    normalized_username = (username or '').strip().lower() or 'unknown'
    client_ip = _get_client_ip(request)
    base = f'auth:login:{client_ip}:{normalized_username}'
    return f'{base}:fails', f'{base}:locked'


# -----------------------------
# Migas de pan y datos estructurados
# -----------------------------
def _build_breadcrumb_context(request, items):
    """Construye las migas de pan visibles y su representación JSON-LD."""
    breadcrumb_items = []
    item_list = []

    for index, item in enumerate(items, start=1):
        label = (item.get('label') or '').strip()
        if not label:
            continue

        relative_url = item.get('url') or ''
        absolute_url = request.build_absolute_uri(relative_url) if relative_url else ''
        breadcrumb_items.append({
            'label': label,
            'url': relative_url,
            'is_current': not bool(relative_url),
        })
        if absolute_url:
            item_list.append({
                '@type': 'ListItem',
                'position': len(item_list) + 1,
                'name': label,
                'item': absolute_url,
            })
        else:
            item_list.append({
                '@type': 'ListItem',
                'position': len(item_list) + 1,
                'name': label,
            })

    json_ld = {
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        'itemListElement': item_list,
    } if item_list else None

    return {
        'breadcrumb_items': breadcrumb_items,
        'breadcrumb_json_ld': json_ld,
    }


def _vehicle_json_ld(request, stock, image_urls):
    """Genera el marcado schema.org de un vehículo para SEO enriquecido."""
    primary_image = _absolute_url(request, image_urls[0]) if image_urls else _absolute_image_url(request, stock.Foto)
    payload = {
        '@context': 'https://schema.org',
        '@type': 'Car',
        'name': f'{stock.Marca} {stock.Modelo} {stock.Año}',
        'brand': {'@type': 'Brand', 'name': stock.Marca},
        'model': stock.Modelo,
        'vehicleModelDate': stock.Año,
        'fuelType': stock.Combustible,
        'vehicleTransmission': stock.Transmisión,
        'color': stock.color,
        'url': request.build_absolute_uri(reverse('item_page', args=[stock.id])),
        'offers': {
            '@type': 'Offer',
            'priceCurrency': 'EUR',
            'price': str(stock.Precio),
            'availability': 'https://schema.org/InStock' if not stock.Vendido else 'https://schema.org/SoldOut',
        },
    }

    if stock.Kilometros is not None:
        payload['mileageFromOdometer'] = {
            '@type': 'QuantitativeValue',
            'value': stock.Kilometros,
            'unitCode': 'KMT',
        }

    if primary_image:
        payload['image'] = primary_image

    return payload


def robots_txt(request):
    """Genera dinámicamente el archivo robots.txt con rutas permitidas y bloqueadas."""
    sitemap_url = request.build_absolute_uri(reverse('django.contrib.sitemaps.views.sitemap'))
    lines = [
        'User-agent: *',
        'Allow: /',
        'Disallow: /admin/',
        'Disallow: /signup/',
        'Disallow: /login/',
        'Disallow: /logout/',
        'Disallow: /favoritos/',
        'Disallow: /comparar/',
        'Disallow: /mensajes-contacto/',
        'Disallow: /stock/add/',
        'Disallow: /stock/lookup/',
        'Disallow: /item/*/available-slots/',
        f'Sitemap: {sitemap_url}',
    ]
    return HttpResponse('\n'.join(lines), content_type='text/plain; charset=utf-8')


# -----------------------------
# Utilidades de normalización de datos
# -----------------------------
def _pick_value(source, aliases):
    """Busca el primer valor disponible en un diccionario usando varios alias posibles."""
    for key in aliases:
        if key in source and source[key] not in (None, ''):
            return source[key]
    return None


# -----------------------------
# Lógica de horarios para pruebas de conducción
# -----------------------------
def _business_hours_for_day(target_date):
    """Devuelve el horario comercial de un día concreto o None si está cerrado."""
    if _is_holiday(target_date):
        return None, None

    weekday = target_date.weekday()
    if 0 <= weekday <= 4:
        return time(9, 30), time(20, 0)
    if weekday == 5:
        return time(10, 0), time(16, 0)
    return None, None


def _is_holiday(target_date):
    """Comprueba si una fecha es festiva usando festivos puntuales y recurrentes."""
    explicit_holidays = set(getattr(settings, 'TEST_DRIVE_HOLIDAYS', []))
    recurring_holidays = set(getattr(settings, 'TEST_DRIVE_RECURRING_HOLIDAYS', []))

    if target_date.isoformat() in explicit_holidays:
        return True

    if target_date.strftime('%m-%d') in recurring_holidays:
        return True

    return False


def _occupied_slot_values(target_date):
    """Recupera las horas ya reservadas para una fecha concreta."""
    occupied_values = set()
    reserved_qs = TestDriveRequest.objects.filter(preferred_datetime__date=target_date).exclude(preferred_datetime__isnull=True)
    for reserved in reserved_qs.values_list('preferred_datetime', flat=True):
        occupied_values.add(timezone.localtime(reserved).strftime('%H:%M'))
    return occupied_values


def _available_slot_values(target_date):
    """Calcula los huecos disponibles en franjas de 30 minutos para reservar pruebas."""
    open_time, close_time = _business_hours_for_day(target_date)
    if not open_time:
        return []

    current_timezone = timezone.get_current_timezone()
    now_local = timezone.localtime()
    occupied_values = _occupied_slot_values(target_date)

    slots = []
    cursor = datetime.combine(target_date, open_time)
    end_cursor = datetime.combine(target_date, close_time)

    while cursor < end_cursor:
        slot_value = cursor.strftime('%H:%M')
        aware_slot = timezone.make_aware(cursor, current_timezone)
        if slot_value not in occupied_values and aware_slot > now_local:
            slots.append(slot_value)
        cursor += timedelta(minutes=30)

    return slots


def test_drive_available_slots(request, stock_id):
    """Endpoint JSON que devuelve slots disponibles para un vehículo y fecha."""
    get_object_or_404(Stock, pk=stock_id)

    date_str = (request.GET.get('date') or '').strip()
    if not date_str:
        return JsonResponse({'slots': [], 'closed': True})

    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        return JsonResponse({'error': 'Fecha inválida'}, status=400)

    open_time, _ = _business_hours_for_day(target_date)
    if not open_time:
        return JsonResponse({'slots': [], 'closed': True, 'is_holiday': _is_holiday(target_date), 'is_sunday': target_date.weekday() == 6})

    slots = _available_slot_values(target_date)
    return JsonResponse({'slots': slots, 'closed': False})


# -----------------------------
# Integración y normalización de datos de vehículos
# -----------------------------
def _normalize_vehicle_payload(payload):
    """Normaliza la respuesta de una API externa genérica al formato del proyecto."""
    if isinstance(payload, list) and payload:
        payload = payload[0]

    if isinstance(payload, dict):
        for container_key in ['data', 'result', 'vehicle', 'vehiculo']:
            nested = payload.get(container_key)
            if isinstance(nested, dict):
                payload = nested
                break

    if not isinstance(payload, dict):
        return {}

    normalized = {
        'Marca': _pick_value(payload, ['Marca', 'marca', 'brand', 'make']),
        'Modelo': _pick_value(payload, ['Modelo', 'modelo', 'model']),
        'Año': _pick_value(payload, ['Año', 'anio', 'año', 'year']),
        'Kilometros': _pick_value(payload, ['Kilometros', 'kilometros', 'km', 'mileage']),
        'Motor': _pick_value(payload, ['Motor', 'motor', 'engine', 'engine_size']),
        'Transmisión': _pick_value(payload, ['Transmisión', 'transmision', 'transmission']),
        'Combustible': _pick_value(payload, ['Combustible', 'combustible', 'fuel']),
        'color': _pick_value(payload, ['color', 'Color', 'colour']),
        'Matricula': _pick_value(payload, ['Matricula', 'matricula', 'plate', 'license_plate']),
        'VIN': _pick_value(payload, ['VIN', 'vin']),
    }

    if normalized['Marca'] and normalized['Modelo']:
        normalized['Titulo'] = f"{normalized['Marca']} {normalized['Modelo']}"

    return {k: v for k, v in normalized.items() if v not in (None, '')}


def _normalize_carsxe_payload(payload):
    """Normaliza específicamente la respuesta de CarsXE al esquema de AutoLux."""
    if not isinstance(payload, dict):
        return {}

    source = payload
    if isinstance(payload.get('attributes'), dict):
        source = payload['attributes']

    normalized = {
        'Marca': _pick_value(source, ['Marca', 'marca', 'make', 'Make']),
        'Modelo': _pick_value(source, ['Modelo', 'modelo', 'model', 'Model']),
        'Año': _pick_value(source, ['Año', 'anio', 'año', 'year', 'registration_year', 'model_year']),
        'Kilometros': _pick_value(source, ['Kilometros', 'kilometros', 'km', 'mileage', 'estimated_current_odometer', 'last_odometer_reading']),
        'Versión': _pick_value(source, ['Versión', 'version', 'trim', 'variant', 'description']),
        'Carrocería': _pick_value(source, ['Carrocería', 'carroceria', 'body_style', 'body_type', 'style']),
        'Puertas': _pick_value(source, ['Puertas', 'puertas', 'doors', 'number_of_doors']),
        'Tracción': _pick_value(source, ['Tracción', 'traccion', 'drive_type', 'drivetrain']),
        'Fecha_matriculación': _pick_value(source, ['Fecha_matriculación', 'fecha_matriculacion', 'registration_date']),
        'Motor': _pick_value(source, ['Motor', 'motor', 'engine', 'engine_size']),
        'Transmisión': _pick_value(source, ['Transmisión', 'transmision', 'transmission', 'transmission_type']),
        'Combustible': _pick_value(source, ['Combustible', 'combustible', 'fuel', 'fuel_type']),
        'color': _pick_value(source, ['color', 'Color', 'colour']),
        'Matricula': _pick_value(source, ['Matricula', 'matricula', 'plate', 'license_plate']),
        'VIN': _pick_value(source, ['VIN', 'vin', 'vehicle_identification_number', 'vechile_identification_number']),
    }

    if not normalized['Matricula'] and isinstance(payload.get('input'), dict):
        normalized['Matricula'] = payload['input'].get('plate')
    if not normalized['VIN'] and isinstance(payload.get('input'), dict):
        normalized['VIN'] = payload['input'].get('vin')

    if normalized.get('Marca') and normalized.get('Modelo'):
        normalized['Titulo'] = f"{normalized['Marca']} {normalized['Modelo']}"

    return {k: v for k, v in normalized.items() if v not in (None, '')}


def _carsxe_request(path, params):
    """Realiza una petición HTTP GET a CarsXE y devuelve el JSON parseado."""
    url = f"https://api.carsxe.com{path}?{urlencode(params)}"
    req = Request(url, headers={'Accept': 'application/json'}, method='GET')
    with urlopen(req, timeout=settings.VEHICLE_LOOKUP_TIMEOUT) as response:
        return json.loads(response.read().decode('utf-8'))


def _carsxe_lookup(plate, vin):
    """Busca un vehículo por VIN o matrícula usando CarsXE como fuente principal."""
    if not settings.CARSXE_API_KEY:
        return {}

    if vin:
        payload = _carsxe_request('/specs', {
            'key': settings.CARSXE_API_KEY,
            'vin': vin,
        })
        if payload.get('success'):
            data = _normalize_carsxe_payload(payload)
            if data:
                return data

    if plate:
        params = {
            'key': settings.CARSXE_API_KEY,
            'plate': plate,
            'country': settings.CARSXE_DEFAULT_COUNTRY or 'ES',
        }
        if settings.CARSXE_DEFAULT_STATE:
            params['state'] = settings.CARSXE_DEFAULT_STATE

        payload = _carsxe_request('/v2/platedecoder', params)
        if payload.get('success'):
            data = _normalize_carsxe_payload(payload)
            if data:
                return data

    return {}


# -----------------------------
# Integración con Google Places
# -----------------------------
def _google_places_request(endpoint, params):
    """Lanza peticiones contra Google Places API y devuelve la respuesta JSON."""
    query = urlencode(params)
    url = f"https://maps.googleapis.com/maps/api/place/{endpoint}/json?{query}"
    req = Request(url, headers={'Accept': 'application/json'}, method='GET')
    with urlopen(req, timeout=settings.GOOGLE_PLACE_TIMEOUT) as response:
        return json.loads(response.read().decode('utf-8'))


def _resolve_google_place_id():
    """Obtiene el place_id del negocio desde settings o resolviéndolo por texto."""
    if settings.GOOGLE_PLACE_ID:
        return settings.GOOGLE_PLACE_ID, None

    payload = _google_places_request('findplacefromtext', {
        'input': settings.GOOGLE_PLACE_QUERY,
        'inputtype': 'textquery',
        'fields': 'place_id,name',
        'language': settings.GOOGLE_PLACE_LANGUAGE or 'es',
        'key': settings.GOOGLE_PLACES_API_KEY,
    })

    status = payload.get('status')
    if status != 'OK':
        return None, status or 'UNKNOWN_STATUS'

    candidates = payload.get('candidates') or []
    if not candidates:
        return None, 'NO_CANDIDATES'

    place_id = candidates[0].get('place_id')
    return place_id, None if place_id else 'MISSING_PLACE_ID'


def _first_name_from_author(name):
    """Reduce el nombre del autor de una reseña al primer nombre para mostrarlo en UI."""
    cleaned_name = (name or 'Cliente').strip()
    if not cleaned_name:
        return 'Cliente'

    return cleaned_name.split()[0]


def _get_google_business_reviews():
    """Obtiene valoración global y reseñas públicas del negocio desde Google Places."""
    if not settings.GOOGLE_PLACES_API_KEY:
        return {'_error': 'MISSING_GOOGLE_PLACES_API_KEY'}

    language = settings.GOOGLE_PLACE_LANGUAGE or 'es'

    try:
        place_id, resolve_error = _resolve_google_place_id()
        if resolve_error:
            return {'_error': f'PLACE_RESOLVE_{resolve_error}'}

        details_payload = _google_places_request('details', {
            'place_id': place_id,
            'language': language,
            'reviews_sort': 'newest',
            'fields': 'name,rating,user_ratings_total,reviews,url,place_id',
            'key': settings.GOOGLE_PLACES_API_KEY,
        })

        details_status = details_payload.get('status')
        if details_status != 'OK':
            return {'_error': f'PLACE_DETAILS_{details_status or "UNKNOWN_STATUS"}'}

        result = details_payload.get('result') or {}
        reviews = []
        for review in (result.get('reviews') or []):
            review_text = (review.get('text') or '').strip()
            if not review_text:
                continue

            author_first_name = _first_name_from_author(review.get('author_name', 'Cliente'))
            reviews.append({
                'author_name': author_first_name,
                'rating': review.get('rating', 0),
                'text': review_text,
                'relative_time_description': review.get('relative_time_description', ''),
                'profile_photo_url': review.get('profile_photo_url', ''),
            })

            if len(reviews) >= 6:
                break

        return {
            'name': result.get('name', 'Google Reviews'),
            'rating': result.get('rating', 0),
            'user_ratings_total': result.get('user_ratings_total', 0),
            'url': result.get('url', ''),
            'place_id': result.get('place_id', place_id),
            'reviews': reviews,
        }
    except Exception:
        return {'_error': 'GOOGLE_REQUEST_EXCEPTION'}


# -----------------------------
# Endpoints y vistas principales
# -----------------------------
@login_required
def vehicle_lookup(request):
    """Endpoint privado para staff que autocompleta datos de vehículo por matrícula o VIN."""
    if not request.user.is_staff:
        return JsonResponse({'ok': False, 'error': 'No tienes permisos para consultar esta herramienta.'}, status=403)

    plate = (request.GET.get('matricula') or '').strip().upper()
    vin = (request.GET.get('vin') or '').strip().upper()

    if not plate and not vin:
        return JsonResponse({'ok': False, 'error': 'Indica matrícula o VIN.'}, status=400)

    try:
        carsxe_data = _carsxe_lookup(plate=plate, vin=vin)
        if carsxe_data:
            return JsonResponse({'ok': True, 'data': carsxe_data})
    except HTTPError as exc:
        if exc.code in (401, 403):
            return JsonResponse({'ok': False, 'error': 'CarsXE rechazó la API key (401/403).'}, status=502)
    except URLError:
        pass
    except Exception:
        pass

    if not settings.VEHICLE_LOOKUP_API_URL:
        return JsonResponse({'ok': False, 'error': 'CarsXE no devolvió datos y no hay API alternativa configurada.'}, status=404)

    query_params = {}
    if plate:
        query_params['matricula'] = plate
    if vin:
        query_params['vin'] = vin
    if settings.VEHICLE_LOOKUP_API_KEY_PARAM and settings.VEHICLE_LOOKUP_API_KEY:
        query_params[settings.VEHICLE_LOOKUP_API_KEY_PARAM] = settings.VEHICLE_LOOKUP_API_KEY

    api_url = settings.VEHICLE_LOOKUP_API_URL
    separator = '&' if '?' in api_url else '?'
    url = f"{api_url}{separator}{urlencode(query_params)}" if query_params else api_url

    headers = {'Accept': 'application/json'}
    if settings.VEHICLE_LOOKUP_API_KEY and settings.VEHICLE_LOOKUP_API_KEY_HEADER:
        headers[settings.VEHICLE_LOOKUP_API_KEY_HEADER] = settings.VEHICLE_LOOKUP_API_KEY

    req = Request(url, headers=headers, method='GET')

    try:
        with urlopen(req, timeout=settings.VEHICLE_LOOKUP_TIMEOUT) as response:
            raw_body = response.read().decode('utf-8')
    except HTTPError as exc:
        return JsonResponse({'ok': False, 'error': f'Error API externa ({exc.code}).'}, status=502)
    except URLError:
        return JsonResponse({'ok': False, 'error': 'No se pudo conectar con la API externa.'}, status=502)
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Fallo inesperado consultando la API.'}, status=500)

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'La API respondió un formato no válido.'}, status=502)

    normalized = _normalize_vehicle_payload(payload)
    if not normalized:
        return JsonResponse({'ok': False, 'error': 'No se encontraron datos para ese vehículo.'}, status=404)

    return JsonResponse({'ok': True, 'data': normalized})

# Página de inicio: muestra destacados, hero principal y reseñas del negocio.
def home(request):
    featured_stocks = Stock.objects.filter(Vendido=False).order_by('-Fecha_de_creación')[:4]
    if not featured_stocks:
        featured_stocks = Stock.objects.order_by('-Fecha_de_creación')[:4]

    hero_stock = featured_stocks.first()
    featured_hero_items = []

    for stock in featured_stocks:
        featured_hero_items.append({
            'title': f'{stock.Marca} {stock.Modelo} {stock.Año}',
            'price': f'€{stock.precio_formateado()}',
            'photo': stock.Foto.url if stock.Foto else '',
            'url': reverse('item_page', args=[stock.id]),
        })

    google_business = _get_google_business_reviews()
    google_reviews_error = google_business.get('_error') if isinstance(google_business, dict) else None

    hero_image = _absolute_image_url(request, hero_stock.Foto) if hero_stock else ''
    home_json_ld = {
        '@context': 'https://schema.org',
        '@type': 'AutoDealer',
        'name': SITE_NAME,
        'url': request.build_absolute_uri(reverse('home')),
        'telephone': '+34 603 957 981',
        'address': {
            '@type': 'PostalAddress',
            'streetAddress': 'El Crucero Auzoa, 35',
            'addressLocality': 'Muskiz',
            'addressRegion': 'Bizkaia',
            'postalCode': '48550',
            'addressCountry': 'ES',
        },
    }

    seo_context = _build_seo_context(
        request,
        title=f'Coches de ocasión en Muskiz | {SITE_NAME}',
        description='Compra coches de ocasión revisados, con atención cercana y acceso rápido a inventario, contacto y pruebas en Autolux Ocasión.',
        canonical_url=request.build_absolute_uri(reverse('home')),
        image_url=hero_image,
        json_ld=_serialize_json_ld(home_json_ld),
    )

    return render(request, 'index.html', {
        'featured_stocks': featured_stocks,
        'hero_stock': hero_stock,
        'featured_hero_items': featured_hero_items,
        'google_business': google_business,
        'google_reviews': google_business.get('reviews', []),
        'google_reviews_error': google_reviews_error,
        'google_reviews_fallback_url': settings.GOOGLE_PLACE_FALLBACK_URL,
        **seo_context,
    })

# Registro de usuarios: crea una cuenta y valida duplicados o contraseñas.
def signup(request):
    if request.method == 'GET':
        return render(request, 'signup.html',{
        'form': UserCreationForm()
         })
    else:
        if request.POST['password1'] == request.POST['password2']:
            try:
                user = User.objects.create_user(
                username=request.POST['username'],
                password=request.POST['password1'])
                user.save()
                login(request, user) #registro coockie session
                return redirect('login')
            except IntegrityError:
                return render(request, 'signup.html',{
                'form': UserCreationForm(),
                'error':('El usuario ya existe')
                })
                
        return render(request, 'signup.html',{
            'form': UserCreationForm(),
            'error':('Las contraseñas no coinciden')
            })

# Inicio de sesión: autentica usuarios y aplica throttling por fallos repetidos.
def signin(request):
    if request.method == 'GET':
        return render(request, 'login.html',{
        'form': AuthenticationForm()
         })
    else:
        username = (request.POST.get('username') or '').strip()
        password = request.POST.get('password') or ''

        fails_key, lock_key = _login_attempt_keys(request, username)
        throttle_conf = _login_security_config()

        if cache.get(lock_key):
            return render(request, 'login.html', {
                'form': AuthenticationForm(),
                'error': 'Demasiados intentos. Espera unos minutos antes de volver a iniciar sesión.',
            })

        user = authenticate(
            request,
            username=username,
            password=password
        )
        if user is None:
            failed_attempts = int(cache.get(fails_key, 0)) + 1
            cache.set(fails_key, failed_attempts, throttle_conf['fail_window_seconds'])

            if failed_attempts >= throttle_conf['max_attempts']:
                cache.set(lock_key, True, throttle_conf['lock_seconds'])
                cache.delete(fails_key)
                error_message = 'Demasiados intentos. Espera unos minutos antes de volver a iniciar sesión.'
            else:
                error_message = 'El usuario o la contraseña son incorrectos'

            return render(request, 'login.html',{
            'form': AuthenticationForm(),
            'error': error_message
            })
        else:
            cache.delete(fails_key)
            cache.delete(lock_key)
            login(request, user) #crear coockie session
            return redirect('home')

# Cierre de sesión: invalida la sesión actual y redirige al inicio.
@require_POST
@login_required
def signout(request):
    logout(request)
    return redirect('home')


# Contacto: muestra el formulario y guarda mensajes recibidos en la base de datos.
def contact(request):
    breadcrumb_context = _build_breadcrumb_context(request, [
        {'label': 'Inicio', 'url': reverse('home')},
        {'label': 'Contacto'},
    ])
    seo_context = _build_seo_context(
        request,
        title=f'Contacto | {SITE_NAME}',
        description='Contacta con Autolux Ocasión en Muskiz para resolver dudas, solicitar información o concertar una visita sobre cualquier vehículo.',
        canonical_url=request.build_absolute_uri(reverse('contact')),
        json_ld=_serialize_json_ld(breadcrumb_context['breadcrumb_json_ld']),
    )

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        subject = request.POST.get('subject', '').strip()
        message_text = request.POST.get('message', '').strip()
        
        # Validación básica
        if not all([name, email, subject, message_text]):
            messages.error(request, 'Por favor completa todos los campos obligatorios.')
            return render(request, 'contact.html', {'form_data': request.POST, **breadcrumb_context, **seo_context})
        
        try:
            # Guardar en BD
            ContactMessage.objects.create(
                name=name,
                email=email,
                phone=phone,
                subject=subject,
                message=message_text
            )
            
            messages.success(request, '✓ Tu mensaje ha sido enviado correctamente. Nos pondremos en contacto pronto.')
            return redirect('/contacto/')
        
        except Exception as e:
            messages.error(request, f'Error al enviar el mensaje. Intenta más tarde.')
            return render(request, 'contact.html', {'form_data': request.POST, **breadcrumb_context, **seo_context})
    
    return render(request, 'contact.html', {**breadcrumb_context, **seo_context})


# Panel interno: permite gestionar mensajes de contacto y solicitudes de prueba.
@login_required
def contact_messages_admin(request):
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('home')

    # Abrir vehículo desde una solicitud y marcarla como leída
    open_test_drive_id = (request.GET.get('open_test_drive') or '').strip()
    if open_test_drive_id.isdigit():
        test_drive_request = TestDriveRequest.objects.filter(id=int(open_test_drive_id)).select_related('stock').first()
        if test_drive_request:
            if not test_drive_request.is_read:
                test_drive_request.is_read = True
                test_drive_request.save(update_fields=['is_read'])
            return redirect('item_page', stock_id=test_drive_request.stock_id)

    # Marcar un mensaje como leído (soporta AJAX para el botón Ver)
    if request.method == 'POST' and 'mark_read_message' in request.POST:
        msg_id = request.POST.get('mark_read_message')
        updated = ContactMessage.objects.filter(id=msg_id, is_read=False).update(is_read=True)

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'updated': bool(updated)})

        return redirect('contact_messages_admin')
    
    # Marcar como leído todos los mensajes nuevos
    if request.method == 'POST' and 'mark_all_read' in request.POST:
        ContactMessage.objects.filter(is_read=False).update(is_read=True)
        messages.success(request, 'Todos los mensajes han sido marcados como leídos.')
        return redirect('contact_messages_admin')

    # Marcar como leídas todas las solicitudes de prueba
    if request.method == 'POST' and 'mark_all_test_drive_read' in request.POST:
        TestDriveRequest.objects.filter(is_read=False).update(is_read=True)
        messages.success(request, 'Todas las solicitudes de prueba han sido marcadas como leídas.')
        return redirect('contact_messages_admin')

    # Marcar una solicitud de prueba como leída
    if request.method == 'POST' and 'mark_read_test_drive' in request.POST:
        request_id = request.POST.get('mark_read_test_drive')
        updated = TestDriveRequest.objects.filter(id=request_id, is_read=False).update(is_read=True)
        if updated:
            messages.success(request, 'Solicitud marcada como leída.')
        return redirect('contact_messages_admin')

    # Marcar una solicitud de prueba como no leída
    if request.method == 'POST' and 'mark_unread_test_drive' in request.POST:
        request_id = request.POST.get('mark_unread_test_drive')
        updated = TestDriveRequest.objects.filter(id=request_id, is_read=True).update(is_read=False)
        if updated:
            messages.success(request, 'Solicitud marcada como no leída.')
        return redirect('contact_messages_admin')
    
    # Eliminar mensaje
    if request.method == 'POST' and 'delete_message' in request.POST:
        msg_id = request.POST.get('delete_message')
        try:
            ContactMessage.objects.get(id=msg_id).delete()
            messages.success(request, 'Mensaje eliminado correctamente.')
        except ContactMessage.DoesNotExist:
            messages.error(request, 'Mensaje no encontrado.')
        return redirect('contact_messages_admin')

    # Eliminar solicitud de prueba
    if request.method == 'POST' and 'delete_test_drive' in request.POST:
        request_id = request.POST.get('delete_test_drive')
        try:
            TestDriveRequest.objects.get(id=request_id).delete()
            messages.success(request, 'Solicitud de prueba eliminada correctamente.')
        except TestDriveRequest.DoesNotExist:
            messages.error(request, 'Solicitud de prueba no encontrada.')
        return redirect('contact_messages_admin')
    
    # Obtener todos los mensajes
    all_messages = ContactMessage.objects.all()
    unread_count = all_messages.filter(is_read=False).count()
    test_drive_requests = TestDriveRequest.objects.select_related('stock').all()
    unread_test_drive_count = test_drive_requests.filter(is_read=False).count()
    
    context = {
        'messages_list': all_messages,
        'unread_count': unread_count,
        'test_drive_requests': test_drive_requests,
        'unread_test_drive_count': unread_test_drive_count,
    }

    return render(request, 'contact_messages_admin.html', context)

    # Inventario: listado de vehículos con filtros, ordenación y favoritos.


# vista para la pagina de stock


def stock_view(request):
    stocks = Stock.objects.all()

    search_query = (request.GET.get('q') or '').strip()
    min_price = (request.GET.get('min_price') or '').strip()
    max_price = (request.GET.get('max_price') or '').strip()
    min_year = (request.GET.get('min_year') or '').strip()
    max_year = (request.GET.get('max_year') or '').strip()
    max_km = (request.GET.get('max_km') or '').strip()
    fuel = (request.GET.get('fuel') or '').strip()
    transmission = (request.GET.get('transmission') or '').strip()
    body = (request.GET.get('body') or '').strip()
    status = (request.GET.get('status') or 'all').strip()
    order = (request.GET.get('order') or 'newest').strip()

    if search_query:
        stocks = stocks.filter(
            Q(Marca__icontains=search_query)
            | Q(Modelo__icontains=search_query)
            | Q(Titulo__icontains=search_query)
            | Q(Combustible__icontains=search_query)
            | Q(Transmisión__icontains=search_query)
            | Q(Versión__icontains=search_query)
            | Q(Carrocería__icontains=search_query)
        )

    numeric_filters = {
        'Precio__gte': min_price,
        'Precio__lte': max_price,
        'Año__gte': min_year,
        'Año__lte': max_year,
        'Kilometros__lte': max_km,
    }

    for lookup, raw_value in numeric_filters.items():
        if not raw_value:
            continue
        try:
            stocks = stocks.filter(**{lookup: raw_value})
        except (TypeError, ValueError):
            pass

    if fuel:
        stocks = stocks.filter(Combustible__iexact=fuel)

    if transmission:
        stocks = stocks.filter(Transmisión__iexact=transmission)

    if body:
        stocks = stocks.filter(Carrocería__iexact=body)

    if status == 'available':
        stocks = stocks.filter(Vendido=False)
    elif status == 'sold':
        stocks = stocks.filter(Vendido=True)

    order_map = {
        'newest': ['-Fecha_de_creación'],
        'price-asc': ['Precio', '-Fecha_de_creación'],
        'price-desc': ['-Precio', '-Fecha_de_creación'],
        'year-desc': ['-Año', '-Fecha_de_creación'],
        'year-asc': ['Año', '-Fecha_de_creación'],
        'km-asc': ['Kilometros', '-Fecha_de_creación'],
    }
    stocks = stocks.order_by(*(order_map.get(order) or order_map['newest']))

    fuel_options = (
        Stock.objects.exclude(Combustible__isnull=True)
        .exclude(Combustible='')
        .values_list('Combustible', flat=True)
        .distinct()
        .order_by('Combustible')
    )
    transmission_options = (
        Stock.objects.exclude(Transmisión__isnull=True)
        .exclude(Transmisión='')
        .values_list('Transmisión', flat=True)
        .distinct()
        .order_by('Transmisión')
    )
    body_options = (
        Stock.objects.exclude(Carrocería__isnull=True)
        .exclude(Carrocería='')
        .values_list('Carrocería', flat=True)
        .distinct()
        .order_by('Carrocería')
    )

    favorite_ids = set()
    if request.user.is_authenticated:
        favorite_ids = set(Favorite.objects.filter(user=request.user).values_list('stock_id', flat=True))

    breadcrumb_context = _build_breadcrumb_context(request, [
        {'label': 'Inicio', 'url': reverse('home')},
        {'label': 'Inventario'},
    ])

    has_filtering = any([
        search_query,
        min_price,
        max_price,
        min_year,
        max_year,
        max_km,
        fuel,
        transmission,
        body,
        status != 'all',
        order != 'newest',
    ])
    seo_context = _build_seo_context(
        request,
        title=f'Inventario de coches de ocasión | {SITE_NAME}',
        description=f'Explora {stocks.count()} vehículos de ocasión con filtros por precio, año, combustible y transmisión en {SITE_NAME}.',
        canonical_url=request.build_absolute_uri(reverse('stock')),
        image_url=_absolute_image_url(request, stocks.first().Foto) if stocks else '',
        robots='noindex,follow' if has_filtering else 'index,follow',
        json_ld=_serialize_json_ld(breadcrumb_context['breadcrumb_json_ld']),
    )

    return render(request, 'stock.html', {
        'stocks': stocks,
        'filters': {
            'q': search_query,
            'min_price': min_price,
            'max_price': max_price,
            'min_year': min_year,
            'max_year': max_year,
            'max_km': max_km,
            'fuel': fuel,
            'transmission': transmission,
            'body': body,
            'status': status,
            'order': order,
        },
        'fuel_options': fuel_options,
        'transmission_options': transmission_options,
        'body_options': body_options,
        'results_count': stocks.count(),
        'favorite_ids': favorite_ids,
        **breadcrumb_context,
        **seo_context,
    })


def compare_view(request):
    """Compara hasta tres vehículos y resalta mejor precio, año y kilometraje."""
    raw_ids = request.GET.getlist('ids')
    selected_ids = []

    for raw_id in raw_ids:
        try:
            stock_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if stock_id not in selected_ids:
            selected_ids.append(stock_id)

    selected_ids = selected_ids[:3]

    if len(selected_ids) < 2:
        messages.error(request, 'Selecciona al menos 2 vehículos para comparar.')
        return redirect('stock')

    ordering = Case(
        *[When(pk=pk, then=pos) for pos, pk in enumerate(selected_ids)],
        output_field=IntegerField(),
    )
    stocks = Stock.objects.filter(pk__in=selected_ids).order_by(ordering)

    if stocks.count() < 2:
        messages.error(request, 'No se pudo generar la comparación con los vehículos seleccionados.')
        return redirect('stock')

    stock_list = list(stocks)

    best_price = min(stock.Precio for stock in stock_list)
    newest_year = max(stock.Año for stock in stock_list)

    km_candidates = [stock.Kilometros for stock in stock_list if stock.Kilometros is not None]
    best_km = min(km_candidates) if km_candidates else None

    highlights = {
        'price': {stock.id for stock in stock_list if stock.Precio == best_price},
        'year': {stock.id for stock in stock_list if stock.Año == newest_year},
        'km': {stock.id for stock in stock_list if best_km is not None and stock.Kilometros == best_km},
    }

    return render(request, 'compare.html', {
        'stocks': stock_list,
        'highlights': highlights,
        **_build_seo_context(
            request,
            title=f'Comparador de vehículos | {SITE_NAME}',
            description='Comparador privado de vehículos seleccionados en Autolux Ocasión.',
            canonical_url=request.build_absolute_uri(reverse('compare')),
            robots='noindex,follow',
        ),
    })


@login_required
def toggle_favorite(request, stock_id):
    """Añade o elimina un vehículo de favoritos para el usuario autenticado."""
    if request.method != 'POST':
        return redirect('item_page', stock_id=stock_id)

    stock = get_object_or_404(Stock, pk=stock_id)
    favorite, created = Favorite.objects.get_or_create(user=request.user, stock=stock)

    if created:
        messages.success(request, 'Añadido a favoritos.')
    else:
        favorite.delete()
        messages.success(request, 'Eliminado de favoritos.')

    next_url = (request.POST.get('next') or '').strip()
    if next_url and next_url.startswith('/'):
        return redirect(next_url)

    return redirect('item_page', stock_id=stock_id)


@login_required
def favorites_view(request):
    """Muestra el listado privado de vehículos favoritos del usuario."""
    favorite_items = Favorite.objects.filter(user=request.user).select_related('stock')
    favorite_stocks = [item.stock for item in favorite_items]
    favorite_ids = set(item.stock_id for item in favorite_items)

    return render(request, 'favorites.html', {
        'stocks': favorite_stocks,
        'favorite_ids': favorite_ids,
        **_build_seo_context(
            request,
            title=f'Mis favoritos | {SITE_NAME}',
            description='Listado privado de vehículos guardados en favoritos.',
            canonical_url=request.build_absolute_uri(reverse('favorites')),
            robots='noindex,follow',
        ),
    })

# Alta de stock: formulario protegido para que el personal publique vehículos.
@login_required
def addstock(request):
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para añadir vehículos.')
        return redirect('stock')

    if request.method == 'POST':
        form = StockForm(request.POST, request.FILES)
        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.Usario = request.user  # tu campo se llama así
            vehicle.save()

            for index, photo in enumerate(request.FILES.getlist('Fotos'), start=1):
                StockImage.objects.create(stock=vehicle, image=photo, orden=index)

            return redirect('stock')
    else:
        form = StockForm()

    return render(request, 'add_stock.html', {'form': form})


@login_required
def editstock(request, stock_id):
    """Edición completa de un vehículo: datos, imágenes, borrado y estado de venta."""
    stock = get_object_or_404(Stock, pk=stock_id)

    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para editar este vehículo.')
        return redirect('item_page', stock_id=stock.id)

    if request.method == 'POST':
        if request.POST.get('delete_stock') == '1':
            stock_title = f'{stock.Marca} {stock.Modelo}'
            stock.delete()
            messages.success(request, f'Ficha eliminada correctamente: {stock_title}.')
            return redirect('stock')

        if request.POST.get('toggle_sale_status') == '1':
            stock.Vendido = not stock.Vendido
            stock.save(update_fields=['Vendido'])
            if stock.Vendido:
                messages.success(request, 'Vehículo marcado como vendido.')
            else:
                messages.success(request, 'Vehículo disponible de nuevo en venta.')
            return redirect('editstock', stock_id=stock.id)

        form = StockForm(request.POST, request.FILES, instance=stock)
        if form.is_valid():
            vehicle = form.save()

            for image in vehicle.images.all():
                if request.POST.get(f'delete_image_{image.id}') == 'on':
                    image.delete()
                    continue

                order_value = (request.POST.get(f'order_image_{image.id}') or '').strip()
                if order_value.isdigit():
                    image.orden = int(order_value)
                    image.save(update_fields=['orden'])

            max_order = vehicle.images.order_by('-orden', '-id').values_list('orden', flat=True).first() or 0
            for index, photo in enumerate(request.FILES.getlist('Fotos'), start=1):
                StockImage.objects.create(stock=vehicle, image=photo, orden=max_order + index)

            return redirect('item_page', stock_id=vehicle.id)
    else:
        form = StockForm(instance=stock)

    return render(request, 'edit_stock.html', {
        'form': form,
        'stock': stock,
        'existing_images': stock.images.all(),
    })


# Ficha de detalle: muestra un vehículo, similares y gestiona solicitudes de prueba.
def item_page(request, stock_id):
    stock = get_object_or_404(Stock, pk=stock_id)
    form_data = {}
    is_favorite = False
    can_edit_stock = False
    share_url = request.build_absolute_uri()
    share_text = f"Mira este vehículo: {stock.Marca} {stock.Modelo} ({stock.Año}) · €{stock.precio_formateado()}"

    similar_vehicles = (
        Stock.objects
        .exclude(pk=stock.pk)
        .annotate(
            similarity_score=(
                Case(When(Modelo=stock.Modelo, then=4), default=0, output_field=IntegerField()) +
                Case(When(Marca=stock.Marca, then=3), default=0, output_field=IntegerField()) +
                Case(When(Combustible=stock.Combustible, then=1), default=0, output_field=IntegerField()) +
                Case(When(Transmisión=stock.Transmisión, then=1), default=0, output_field=IntegerField())
            )
        )
        .filter(
            Q(Modelo=stock.Modelo) |
            Q(Marca=stock.Marca) |
            Q(Combustible=stock.Combustible) |
            Q(Transmisión=stock.Transmisión)
        )
        .order_by('Vendido', '-similarity_score', '-Fecha_de_creación')[:3]
    )

    if request.user.is_authenticated:
        is_favorite = Favorite.objects.filter(user=request.user, stock=stock).exists()
        can_edit_stock = request.user.is_staff

    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        email = (request.POST.get('email') or '').strip()
        phone = (request.POST.get('phone') or '').strip()
        preferred_day = (request.POST.get('preferred_day') or '').strip()
        preferred_time = (request.POST.get('preferred_time') or '').strip()
        message_text = (request.POST.get('message') or '').strip()

        form_data = {
            'name': name,
            'email': email,
            'phone': phone,
            'preferred_day': preferred_day,
            'preferred_time': preferred_time,
            'message': message_text,
        }

        if not name or not email or not preferred_day or not preferred_time:
            messages.error(request, 'Completa nombre, email, fecha y hora para solicitar la prueba.')
        else:
            selected_datetime = None

            try:
                parsed_day = date.fromisoformat(preferred_day)
                parsed_time = time.fromisoformat(preferred_time)
                available_slots = _available_slot_values(parsed_day)

                if preferred_time not in available_slots:
                    if _is_holiday(parsed_day) or parsed_day.weekday() == 6:
                        messages.error(request, 'No se permiten reservas los domingos ni festivos.')
                    else:
                        messages.error(request, 'La fecha/hora seleccionada ya no está disponible o está fuera de horario comercial.')
                else:
                    naive_dt = datetime.combine(parsed_day, parsed_time)
                    selected_datetime = timezone.make_aware(naive_dt, timezone.get_current_timezone())
            except ValueError:
                messages.error(request, 'Fecha u hora inválida. Revisa los datos e inténtalo de nuevo.')

            if selected_datetime:
                TestDriveRequest.objects.create(
                    stock=stock,
                    name=name,
                    email=email,
                    phone=phone,
                    preferred_date=f"{preferred_day} {preferred_time}",
                    preferred_datetime=selected_datetime,
                    message=message_text,
                )
                messages.success(request, 'Solicitud de prueba enviada. Te contactaremos lo antes posible.')
                return redirect('item_page', stock_id=stock.id)

    gallery_images = []

    if stock.Foto:
        gallery_images.append(stock.Foto.url)

    for related_name in ['images', 'imagenes', 'fotos', 'gallery_images']:
        if hasattr(stock, related_name):
            try:
                related_items = getattr(stock, related_name).all()
                for related_item in related_items:
                    image_field = getattr(related_item, 'image', None) or getattr(related_item, 'foto', None)
                    if image_field and hasattr(image_field, 'url'):
                        gallery_images.append(image_field.url)
            except Exception:
                pass

    gallery_images = list(dict.fromkeys(gallery_images))

    vehicle_name = f'{stock.Marca} {stock.Modelo} {stock.Año}'
    breadcrumb_context = _build_breadcrumb_context(request, [
        {'label': 'Inicio', 'url': reverse('home')},
        {'label': 'Inventario', 'url': reverse('stock')},
        {'label': vehicle_name},
    ])
    vehicle_description = _clean_seo_text(
        f'{vehicle_name} en venta por €{stock.precio_formateado()}. Combustible {stock.Combustible}, transmisión {stock.Transmisión}'
        + (f', {stock.Kilometros} km' if stock.Kilometros is not None else '')
        + '. Consulta fotos, detalles y solicita tu prueba en Autolux Ocasión.',
        max_length=170,
    )
    seo_context = _build_seo_context(
        request,
        title=f'{vehicle_name} en venta | {SITE_NAME}',
        description=vehicle_description,
        canonical_url=request.build_absolute_uri(reverse('item_page', args=[stock.id])),
        image_url=gallery_images[0] if gallery_images else _absolute_image_url(request, stock.Foto),
        og_type='product',
        json_ld=_serialize_json_ld(_vehicle_json_ld(request, stock, gallery_images), breadcrumb_context['breadcrumb_json_ld']),
    )

    return render(request, 'item_page.html', {
        'stock': stock,
        'gallery_images': gallery_images,
        'test_drive_form_data': form_data,
        'is_favorite': is_favorite,
        'can_edit_stock': can_edit_stock,
        'similar_vehicles': similar_vehicles,
        'share_url': share_url,
        'share_text': share_text,
        **breadcrumb_context,
        **seo_context,
    })

# Utilidad de imagen: devuelve una miniatura HTML para usarla en interfaces internas.
def imagen_tag(self):
    """Genera una etiqueta <img> para previsualizar una imagen asociada."""
    if self.imagen:
        return format_html('<img src="{}" width="100" height="100" />', self.imagen.url)
    else:
        return "No Image"
