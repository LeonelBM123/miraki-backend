import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')

app = Celery('miraki')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

try:
    from apps.alerts.celery_beat_schedule import CELERY_BEAT_SCHEDULE

    app.conf.beat_schedule = CELERY_BEAT_SCHEDULE
except ImportError:
    pass
