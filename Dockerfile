FROM python:3.12-slim

# Evitar buffering
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependencias del sistema (ejemplo para psycopg2 / mysqlclient)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copiar proyecto
COPY . /app/

# Recoger estáticos en build
RUN python manage.py collectstatic --noinput

# Exponer puerto interno de Gunicorn
EXPOSE 8000

# Comando de arranque
CMD ["gunicorn", "autolux.wsgi:application", "--bind", "0.0.0.0:8000"]
