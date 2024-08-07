"""
Django settings for shapeblock project.

Generated by 'django-admin startproject' using Django 5.0.2.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

from pathlib import Path

import os
import environ
from datetime import timedelta

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent

env = environ.Env()
env.read_env(os.path.join(BASE_DIR, ".env.sb"))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

SECRET_KEY = env("SECRET_KEY", default="django-insecure-j)s)xyusi2r^2)*%0i*n7)as+eba3)zh1^&3*y21o4^pv&z3wd")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG", True)

TEST_RUN = env.bool('TEST_RUN', False) and DEBUG

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS",default=["*"])


# Application definition

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # 3rd party
    "allauth",
    "allauth.account",
    "rest_framework",
    "rest_framework.authtoken",
    'drf_spectacular',
    # custom
    "shapeblock.authentication.apps.AuthenticationConfig",
    "shapeblock.projects.apps.ProjectsConfig",
    "shapeblock.apps.apps.AppsConfig",
    "shapeblock.deployments.apps.DeploymentsConfig",
    "shapeblock.services.apps.ServicesConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
]

ROOT_URLCONF = "shapeblock.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, 'templates')],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "shapeblock.wsgi.application"

ASGI_APPLICATION = "shapeblock.asgi.application"

AUTHENTICATION_BACKENDS = (
    # Needed to login by username in Django admin, regardless of `allauth`
    "django.contrib.auth.backends.ModelBackend",
    # `allauth` specific authentication methods, such as login by e-mail
    "allauth.account.auth_backends.AuthenticationBackend",
)

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {"default": env.db()}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

SITE_ID = 1

# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": '[{asctime}] {levelname} "{name}" {message}',
            "style": "{",
            "datefmt": "%d/%b/%Y %H:%M:%S",  # match Django server time format
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": env("DJANGO_LOG_LEVEL", default="INFO"),
        },
        "shapeblock": {
            "handlers": ["console"],
            "level": env("SHAPEBLOCK_LOG_LEVEL", default="INFO"),
        },
    },
}


# Rest fw

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}


# Allauth
ACCOUNT_AUTHENTICATION_METHOD = "username"
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_EMAIL_REQUIRED = False
ACCOUNT_EMAIL_SUBJECT_PREFIX = ""
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE = False
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_LOGOUT_ON_GET = True

EMAIL_SUBJECT_PREFIX = env("EMAIL_SUBJECT_PREFIX", default="[ShapeBlock] ")

DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL")

# App specific
GITHUB_TOKEN = env("GH_TOKEN")

CHART_VERSION = env("CHART_VERSION", default="0.2.0")

KUBE_SERVER = env("KUBE_SERVER")
KUBE_TOKEN = env("KUBE_TOKEN")
KUBE_NAMESPACE = env("KUBE_NAMESPACE")

# DRF spectacular

SPECTACULAR_SETTINGS = {
    'TITLE': 'ShapeBlock',
    'DESCRIPTION': 'ShapeBlock API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    # OTHER SETTINGS
}

# Channels
REDIS_HOST = env("REDIS_HOST", default="redis")
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(REDIS_HOST, 6379)],
        },
    }
}

ADMIN_URL = env("ADMIN_URL", default="admin/")

if DEBUG:
    # use in development
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    # https://docs.djangoproject.com/en/dev/ref/settings/#email-host
    EMAIL_HOST = env("EMAIL_HOST", default="mailhog")
    # https://docs.djangoproject.com/en/dev/ref/settings/#email-port
    EMAIL_PORT = 1025
else:
    # use in production
    EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"
    ANYMAIL = {
        "MAILGUN_API_KEY": env("MAILGUN_API_KEY"),
        "MAILGUN_SENDER_DOMAIN": env("MAILGUN_DOMAIN"),
        "MAILGUN_API_URL": env("MAILGUN_API_URL", default="https://api.mailgun.net/v3"),
    }
    ACCOUNT_DEFAULT_HTTP_PROTOCOL='https'
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

    # Django security checklist settings.
    # More details here: https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

CLUSTER_DOMAIN = env("CLUSTER_DOMAIN", default="example.com")


FERNET_KEYS = env.list('FERNET_KEYS')