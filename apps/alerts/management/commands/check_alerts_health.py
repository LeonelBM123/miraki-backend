import json
import os
from pathlib import Path

from celery import current_app
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = 'Check alerts subsystem health.'

    def handle(self, *args, **options):
        issues = []

        try:
            if not current_app.control.ping(timeout=2.0):
                issues.append('Celery worker did not respond to ping.')
        except Exception as exc:
            issues.append(f'Celery ping failed: {exc}')

        credentials = os.environ.get('FCM_CREDENTIALS_JSON')
        if not credentials:
            issues.append('FCM_CREDENTIALS_JSON is not configured.')
        else:
            credential_path = Path(credentials)
            if credential_path.exists():
                pass
            else:
                try:
                    json.loads(credentials)
                except json.JSONDecodeError:
                    issues.append('FCM_CREDENTIALS_JSON must be a JSON string or a path to a file.')

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 1
                FROM pg_views
                WHERE schemaname = current_schema()
                  AND viewname = %s
                """,
                ['vw_ultima_posicion_nino'],
            )
            if cursor.fetchone() is None:
                issues.append('Database view vw_ultima_posicion_nino is missing.')

        if issues:
            raise CommandError('Health check failed:\n- ' + '\n- '.join(issues))

        self.stdout.write(self.style.SUCCESS('Alerts health check passed.'))
