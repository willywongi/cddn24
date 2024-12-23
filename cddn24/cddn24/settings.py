import os
from pathlib import Path

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.utils.log import DEFAULT_LOGGING

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']
DEBUG = os.environ['DJANGO_DEBUG'] == "1"

# Network
ALLOWED_HOSTS = []
defined_hostname = os.environ.get('HOSTNAME')
if defined_hostname:
    ALLOWED_HOSTS.append(defined_hostname)

container_name = os.environ.get('BACKEND_CONTAINER_NAME')
if DEBUG and container_name:
    ALLOWED_HOSTS.append(container_name)

# Allow using ngrok or localhost.run    
if DEBUG:
    ALLOWED_HOSTS.extend((".ngrok-free.app", ".lhr.life"))

# Allow calls from Private Virtual Network
pvn_addr = os.environ.get("INSTANCE_PVN_ADDR")
if pvn_addr:
    ALLOWED_HOSTS.append(pvn_addr)

# https://docs.djangoproject.com/en/5.0/ref/settings/#secure-proxy-ssl-header
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

# Application definition
INSTALLED_APPS = [
    "django_dramatiq",
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_bootstrap5',
    "album",
]

ROOT_URLCONF = 'cddn24.urls'
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / "templates"
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'cddn24.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': "/var/lib/sqlite/data/db.sqlite3",
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/
LANGUAGE_CODE = 'it-it'
TIME_ZONE = 'Europe/Rome'
USE_I18N = True
USE_L10N = True
USE_TZ = True
LANGUAGES = [('it', 'Italiano'), ]

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
STATIC_URL = f"{os.environ['STATIC_PATH']}/"
STATIC_ROOT = f"/cddn24-{os.environ['STATIC_PATH']}"
MEDIA_URL = f"{os.environ['MEDIA_PATH']}/"
MEDIA_ROOT = f"/cddn24-{os.environ['MEDIA_PATH']}"

# Authentication
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]
AUTHENTICATION_BACKENDS = (
    # Needed to login by username in Django admin, regardless of `allauth`
    'django.contrib.auth.backends.ModelBackend',
)
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_SUBJECT_PREFIX = "cddn24 – "
LOGIN_REDIRECT_URL = '/'
LOGIN_URL = "/login"
LOGOUT_REDIRECT_URL = '/'

# Logging configuration
# https://docs.djangoproject.com/en/5.0/topics/logging/#configuring-logging
log_root = Path("/") / os.environ['LOG_PATH']
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': DEFAULT_LOGGING['filters'],
    "formatters": {
        "standard": {
            "format": '%(asctime)s %(name)s %(levelname)s %(message)s'
        },
        **DEFAULT_LOGGING['formatters']
    },
    'handlers': {
        'cddn24': {
            'level': 'DEBUG' if DEBUG else 'INFO',
            'filename': log_root / 'cddn24.log',
            'formatter': 'standard',
            "class": "logging.handlers.RotatingFileHandler",
            "maxBytes": 1048576,  # 1MB
            "backupCount": 5
        },
        'django': {
            'level': 'DEBUG' if DEBUG else 'INFO',
            'filename': log_root / 'django.log',
            'formatter': 'standard',
            "class": "logging.handlers.RotatingFileHandler",
            "maxBytes": 1048576,  # 1MB
            "backupCount": 5
        },
        **DEFAULT_LOGGING['handlers']
    },
    'loggers': {
        'django': {
            'handlers': ['django', 'mail_admins'],
            'level': 'INFO'
        },
        'cddn24': {
            'handlers': ['cddn24', 'console'],
            'level': 'DEBUG',
        },
        'django.server': DEFAULT_LOGGING['loggers']['django.server']
    },
}

# Email send configuration
# https://docs.djangoproject.com/en/5.0/topics/email/#smtp-backend
EMAIL_HOST = os.environ.get('EMAIL_HOST')
EMAIL_PORT = os.environ.get('EMAIL_PORT')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
EMAIL_SUBJECT_PREFIX = ""
SERVER_EMAIL = "gli-elfi@nerdsopolis.net"
DEFAULT_FROM_EMAIL = "gli-elfi@nerdsopolis.net"
# This custom backend allows composing email messages in MJML
EMAIL_BACKEND = "mjml_email_backend.MJMLEmailBackend"

# Admins email
ADMINS = []
admin_names = os.environ.get('ADMIN_NAMES')
admin_email_addresses = os.environ.get('ADMIN_EMAIL_ADDRESSES')
if admin_names and admin_email_addresses:
    ADMINS = [(name.strip(), addr.strip()) for name, addr in
              zip(admin_names.split(","), admin_email_addresses.split(","))]

# Dramatiq
DRAMATIQ_BROKER = {
    "BROKER": "dramatiq.brokers.redis.RedisBroker",
    "OPTIONS": {
        "host": os.environ['MESSAGE_BROKER_CONTAINER_NAME'],
    },
    "MIDDLEWARE": [
        "dramatiq.middleware.Prometheus",
        "dramatiq.middleware.AgeLimit",
        "dramatiq.middleware.TimeLimit",
        "dramatiq.middleware.Callbacks",
        "dramatiq.middleware.Retries",
        "django_dramatiq.middleware.DbConnectionsMiddleware",
        "django_dramatiq.middleware.AdminMiddleware",
    ]
}
DRAMATIQ_RESULT_BACKEND = {
    "BACKEND": "dramatiq.results.backends.redis.RedisBackend",
    "BACKEND_OPTIONS": {
        "host": os.environ['MESSAGE_BROKER_CONTAINER_NAME'],
    },
    "MIDDLEWARE_OPTIONS": {
        "result_ttl": 1000 * 60 * 10
    }
}

ROLLBAR = {
    "access_token": "e46e8e633d8b48a588566417a9016dab",
    "environment": os.environ["ENV_NAME"],
    "code_version": os.environ.get("CODE_VERSION", "0.0"),
    "root": BASE_DIR,
    "enabled": not DEBUG,
    "exception_level_filters": [
        (Http404, "warning"),
        (PermissionDenied, "warning"),
    ]
}
