from django.apps import AppConfig


class WebConfig(AppConfig):
    name = 'Web'
INSTALLED_APPS = [ 'Web.apps.WebConfig', ]