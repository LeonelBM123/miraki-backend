from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'evaluar-zonas-cada-60s': {
        'task': 'apps.alerts.tasks.evaluar_zonas',
        'schedule': crontab(),
        'options': {'expires': 55},
    },
}
