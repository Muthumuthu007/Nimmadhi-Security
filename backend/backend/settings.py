"""
Django settings for backend project.
"""
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-change-this-in-production'

DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'users',
    'stock',
    'production',
    'casting',
    'undo',
    'reports',
    'grn',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
            ],
        },
    },
]

WSGI_APPLICATION = 'backend.wsgi.application'

# No database needed - using DynamoDB exclusively
DATABASES = {}

# No Django authentication - using DynamoDB with JWT

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# No Django user model - using DynamoDB for authentication

# AWS DynamoDB Configuration
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-2')

# DynamoDB Table Names
DYNAMODB_TABLES = {
    'USERS': 'users',
    'GROUPS': 'Groups', 
    'STOCK': 'stock',
    'TRANSACTIONS': 'transactions',
    'PRODUCTION': 'production',
    'UNDO_ACTIONS': 'undo_actions',
    'PRODUCTS': 'products',
    'CASTING_PRODUCTS': 'casting_products',
    'stock_remarks': 'stock_remarks',
    'stock_transactions': 'stock_transactions',
    'undo_actions': 'undo_actions',
    'push_to_production': 'push_to_production',
    'PUSH_TO_PRODUCTION': 'push_to_production',
    'GRN_TABLE': 'grn_table'
}

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')