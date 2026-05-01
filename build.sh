#!/usr/bin/env bash

pip install -r requirements.txt

python manage.py migrate

python manage.py collectstatic --noinput

python manage.py shell <<'PY'
import os
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()
username = os.getenv('DJANGO_SUPERUSER_USERNAME')
email = os.getenv('DJANGO_SUPERUSER_EMAIL')
password = os.getenv('DJANGO_SUPERUSER_PASSWORD')

if not username or not email or not password:
	raise SystemExit('Faltan variables DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL o DJANGO_SUPERUSER_PASSWORD')

user, created = User.objects.get_or_create(
	username=username,
	defaults={
		'email': email,
		'is_staff': True,
		'is_superuser': True,
		'is_active': True,
		'last_login': timezone.now(),
	},
)

if created:
	user.set_password(password)
	user.save(update_fields=['password'])
	print('Superusuario creado')
else:
	changed = False
	if user.email != email:
		user.email = email
		changed = True
	if not user.is_staff:
		user.is_staff = True
		changed = True
	if not user.is_superuser:
		user.is_superuser = True
		changed = True
	if not user.is_active:
		user.is_active = True
		changed = True
	if user.last_login is None:
		user.last_login = timezone.now()
		changed = True

	user.set_password(password)
	changed = True

	if changed:
		user.save()
	print('Superusuario actualizado')
PY