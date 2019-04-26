from __future__ import absolute_import

import os

from django.conf import settings

from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                      '{{ cookiecutter.project_name }}.settings')

app = Celery('{{ cookiecutter.project_name }}')
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
