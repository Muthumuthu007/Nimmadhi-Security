"""
WSGI config for backend project.
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings_debug')
application = get_wsgi_application()