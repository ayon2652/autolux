# AutoLux

Proyecto intermodular desarrollado con Django para la gestión y publicación de vehículos de ocasión.

## Descripción

AutoLux es una plataforma web orientada a concesionarios o compraventas de coches de segunda mano. Permite gestionar el inventario de vehículos, mostrar fichas detalladas, comparar coches, guardar favoritos, solicitar pruebas de conducción y contactar con el negocio desde la propia web.

Además, el proyecto integra servicios externos para enriquecer la información mostrada y mejorar la experiencia de usuario, como la consulta de datos de vehículos por matrícula o VIN y la obtención de reseñas del negocio.

## Tecnologías utilizadas

### Backend

- **Python**: lenguaje principal del proyecto.
- **Django**: framework web que gestiona rutas, vistas, ORM, autenticación y panel de administración.
- **django-ckeditor-5**: editor de texto enriquecido integrado en formularios administrativos.
- **gunicorn**: servidor WSGI para despliegue en producción.
- **dj-database-url**: configuración de base de datos a partir de variables de entorno.
- **python-dotenv**: carga de variables de entorno desde el archivo `.env`.
- **Pillow**: gestión de imágenes subidas al sistema.

### Base de datos

- **SQLite**: base de datos usada en desarrollo local.
- **PostgreSQL**: base de datos preparada para producción.
- **psycopg2-binary**: driver de conexión entre Python/Django y PostgreSQL.

### Frontend

- **HTML5**: estructura de las páginas.
- **CSS3**: estilos y diseño responsive.
- **JavaScript**: interacción cliente para galería, comparador, favoritos, calculadora financiera y pruebas de conducción.
- **Django Templates**: sistema de plantillas con renderizado dinámico en servidor.

### APIs y servicios externos

- **CarsXE API**: consulta de información del vehículo a partir de matrícula o VIN.
- **Google Places API**: obtención de datos del negocio y reseñas públicas.

### SEO y despliegue

- **django.contrib.sitemaps**: generación de sitemap XML.
- **Schema.org / JSON-LD**: datos estructurados para buscadores.
- **Open Graph**: metadatos para compartir contenido en redes sociales.
- **robots.txt dinámico**: control del rastreo por motores de búsqueda.

### Herramientas de desarrollo

- **Git**: control de versiones del proyecto.
- **README.md**: documento principal de documentación e instalación.
- **pip** y **venv**: gestión del entorno virtual y dependencias.
- **Node.js / Mermaid CLI**: generación de diagramas del proyecto en formato gráfico.

## Funcionalidades principales

- Gestión de stock de vehículos.
- Fichas detalladas con galería de imágenes.
- Comparador de vehículos.
- Sistema de favoritos para usuarios autenticados.
- Formulario de contacto.
- Solicitud de prueba de conducción con control de horarios.
- Lookup de vehículo por matrícula o VIN.
- Integración de reseñas del negocio.

## Estructura general

- [autolux/settings.py](autolux/settings.py): configuración principal del proyecto.
- [Web/models.py](Web/models.py): modelos de datos.
- [Web/views.py](Web/views.py): lógica de vistas y reglas de negocio.
- [Web/templates/](Web/templates/): plantillas HTML.
- [Web/static/](Web/static/): recursos estáticos propios.

## Preparación para producción

1. Crear entorno e instalar dependencias:
	- `python -m venv .venv`
	- `pip install -r requirements.txt`
2. Crear `.env` a partir de `.env.example` y completar:
	- `SECRET_KEY`
	- `ALLOWED_HOSTS`
	- `CSRF_TRUSTED_ORIGINS`
	- `DATABASE_URL` (PostgreSQL)
3. Ejecutar migraciones y recopilar estáticos:
	- `python manage.py migrate`
	- `python manage.py collectstatic --noinput`
4. Validar configuración de despliegue:
	- `python manage.py check --deploy`
5. Ejecutar con Gunicorn:
	- `gunicorn autolux.wsgi:application --bind 0.0.0.0:8000`

