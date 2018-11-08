"""
Django settings for trails project.

Generated by 'django-admin startproject' using Django 2.1.1.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""

import os

IS_PROD = os.environ.get("ENV") == "prod"

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = "/db/"

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# TODO: generate from env
SECRET_KEY = "d=#4bn3nq-ltca9ed^^@!)z7io6c2onv0stwvk2kjpz=+@pb@@"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = not IS_PROD

ALLOWED_HOSTS = ["*"]

if IS_PROD:
    # SECURE_HSTS_SECONDS = 600
    # SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    # SECURE_SSL_REDIRECT = True
    # SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = "DENY"
    DATABASES = {
        "default": {
            "ENGINE": "django.contrib.gis.db.backends.postgis",
            "NAME": "trails-db-blue",
            "USER": os.environ['DB_USER'],
            "PASSWORD": os.environ['DB_PASSWORD'],
            "HOST": os.environ['DB_HOST'],
            "POST": os.environ['DB_PORT']
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.contrib.gis.db.backends.spatialite",
            "NAME": os.path.join(DB_DIR, "db.sqlite3"),
        }
    }

REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    "DEFAULT_PARSER_CLASSES": ("rest_framework.parsers.JSONParser",)
}

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    "corsheaders",
    "rest_framework",
    "osm",
    "api"
    # 'debug_toolbar',
]

MIDDLEWARE = [
    "django.middleware.gzip.GZipMiddleware",
    #'debug_toolbar.middleware.DebugToolbarMiddleware',
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "corsheaders.middleware.CorsMiddleware",
]

INTERNAL_IPS = ['127.0.0.1']

CORS_ORIGIN_ALLOW_ALL = True

ROOT_URLCONF = "trails.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

WSGI_APPLICATION = "trails.wsgi.application"

# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

SPATIALITE_LIBRARY_PATH = "mod_spatialite.so"

#DEBUG_TOOLBAR_PANELS = [
#    'djdt_flamegraph.FlamegraphPanel'
#]

# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATIC_URL = "/static/"

if not IS_PROD:
    LOGGING = {
        'version': 1,
        'filters': {
            'require_debug_true': {
                '()': 'django.utils.log.RequireDebugTrue',
            }
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'filters': ['require_debug_true'],
                'class': 'logging.StreamHandler',
            }
        },
        'loggers': {
            'django.db.backends': {
                'level': 'DEBUG',
                'handlers': ['console'],
            }
        }
    }

