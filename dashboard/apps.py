from django.apps import AppConfig
import threading
import sys

class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dashboard'

    def ready(self):
        # Only start scheduler if running the development or production server
        # Avoid starting during migrations, shell, etc.
        skip_commands = [
            'makemigrations', 'migrate', 'collectstatic', 'shell', 'test', 'createsuperuser', 'loaddata', 'dumpdata'
        ]
        if any(cmd in sys.argv for cmd in skip_commands):
            return
        if 'runserver' in sys.argv or 'gunicorn' in sys.argv:
            from .views import reddit_scheduler
            scheduler_thread = threading.Thread(target=reddit_scheduler, daemon=True)
            scheduler_thread.start()
