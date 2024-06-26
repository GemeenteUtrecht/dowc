import os

from django.urls import reverse_lazy

from sentry_sdk.integrations import django, redis

from .environ import config

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
DJANGO_PROJECT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir)
)
BASE_DIR = os.path.abspath(
    os.path.join(DJANGO_PROJECT_DIR, os.path.pardir, os.path.pardir)
)

#
# Core Django settings
#
SITE_ID = config("SITE_ID", default=1)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config("SECRET_KEY")

# NEVER run with DEBUG=True in production-like environments
DEBUG = config("DEBUG", default=False)

# = domains we're running on
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="", split=True)

IS_HTTPS = config("IS_HTTPS", default=not DEBUG)

# Internationalization
# https://docs.djangoproject.com/en/2.0/topics/i18n/

LANGUAGE_CODE = "nl-nl"

TIME_ZONE = "Europe/Amsterdam"  # note: this *may* affect the output of DRF datetimes

USE_I18N = True

USE_L10N = True

USE_TZ = True

USE_THOUSAND_SEPARATOR = True

#
# DATABASE and CACHING setup
#
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", "dowc"),
        "USER": config("DB_USER", "dowc"),
        "PASSWORD": config("DB_PASSWORD", "dowc"),
        "HOST": config("DB_HOST", "localhost"),
        "PORT": config("DB_PORT", 5432),
        # "CONN_MAX_AGE": 60,  # Lifetime of a database connection for performance.
    },
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{config('CACHE_DEFAULT', 'localhost:6379/0')}",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
        },
    },
    "axes": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{config('CACHE_AXES', 'localhost:6379/0')}",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
        },
    },
}

# Application definition

INSTALLED_APPS = [
    # Note: contenttypes should be first, see Django ticket #10827
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    # Note: If enabled, at least one Site object is required
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    # django-admin-index
    "ordered_model",
    "django_admin_index",
    # Optional applications.
    "django.contrib.admin",
    # External applications.
    "axes",
    "django_auth_adfs",
    "django_auth_adfs_db",
    "rest_framework",
    "rest_framework.authtoken",
    "hijack",
    "hijack_admin",
    "compat",  # Part of hijack
    "solo",
    "sniplates",
    "zgw_consumers",
    "zgw_auth_backend",
    "privates",
    "drf_spectacular",
    "djangodav",
    # Project applications.
    "dowc.accounts",
    "dowc.api",
    "dowc.core",
    "dowc.utils",
    "dowc.emails",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "axes.middleware.AxesMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # 'django.middleware.locale.LocaleMiddleware',
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

if DEBUG:
    MIDDLEWARE.append("dowc.core.middleware.request_response_logger_middleware")

ROOT_URLCONF = "dowc.urls"

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    "django.template.loaders.filesystem.Loader",
    "django.template.loaders.app_directories.Loader",
)

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(DJANGO_PROJECT_DIR, "templates")],
        "APP_DIRS": False,  # conflicts with explicity specifying the loaders
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "dowc.utils.context_processors.settings",
            ],
            "loaders": TEMPLATE_LOADERS,
        },
    }
]

WSGI_APPLICATION = "dowc.wsgi.application"

# Translations
LOCALE_PATHS = (os.path.join(DJANGO_PROJECT_DIR, "conf", "locale"),)

#
# SERVING of static and media files
#

STATIC_URL = "/static/"

STATIC_ROOT = os.path.join(BASE_DIR, "static")

# Additional locations of static files
STATICFILES_DIRS = [os.path.join(DJANGO_PROJECT_DIR, "static")]

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

MEDIA_ROOT = os.path.join(BASE_DIR, "media")

MEDIA_URL = "/media/"

#
# Sending EMAIL
#
EMAIL_HOST = config("EMAIL_HOST", default="localhost")
EMAIL_PORT = config(
    "EMAIL_PORT", default=25
)  # disabled on Google Cloud, use 487 instead
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=False)
EMAIL_TIMEOUT = 10

DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="dowc@example.com")

#
# LOGGING
#
LOG_STDOUT = config("LOG_STDOUT", default=DEBUG)
LOG_LEVEL = config("LOG_LEVEL", default="INFO")
LOG_PERFORMANCE = config("LOG_PERFORMANCE", default=False)

LOGGING_DIR = os.path.join(BASE_DIR, "log")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s %(levelname)s %(name)s %(module)s %(process)d %(thread)d  %(message)s"
        },
        "timestamped": {"format": "%(asctime)s %(levelname)s %(name)s  %(message)s"},
        "simple": {"format": "%(levelname)s  %(message)s"},
        "performance": {"format": "%(asctime)s %(process)d | %(thread)d | %(message)s"},
    },
    "filters": {"require_debug_false": {"()": "django.utils.log.RequireDebugFalse"}},
    "handlers": {
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
        "null": {"level": "DEBUG", "class": "logging.NullHandler"},
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "timestamped",
        },
        "django": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOGGING_DIR, "django.log"),
            "formatter": "verbose",
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 10,
        },
        "project": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOGGING_DIR, "dowc.log"),
            "formatter": "verbose",
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 10,
        },
        "performance": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOGGING_DIR, "performance.log"),
            "formatter": "performance",
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 10,
        },
    },
    "loggers": {
        "dowc": {
            "handlers": ["project"] if not LOG_STDOUT else ["console"],
            "level": LOG_LEVEL,
            "propagate": True,
        },
        "django.request": {
            "handlers": ["django"] if not LOG_STDOUT else ["console"],
            "level": "ERROR",
            "propagate": True,
        },
        "django.template": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
        "django_auth_adfs": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": True,
        },
    },
}

#
# AUTH settings - user accounts, passwords, backends...
#
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Allow logging in with both username+password and email+password
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesBackend",
    "dowc.accounts.backends.UserModelEmailBackend",
    "django.contrib.auth.backends.ModelBackend",
    "django_auth_adfs_db.backends.AdfsAuthCodeBackend",
]

SESSION_COOKIE_NAME = "dowc_sessionid"

LOGIN_URL = reverse_lazy("admin:login")
LOGIN_REDIRECT_URL = reverse_lazy("index")

#
# SECURITY settings
#
SESSION_COOKIE_SECURE = IS_HTTPS
SESSION_COOKIE_HTTPONLY = True

CSRF_COOKIE_SECURE = IS_HTTPS

X_FRAME_OPTIONS = "DENY"

#
# Custom settings
#
PROJECT_NAME = "dowc"
SITE_TITLE = "DO.W.C."

ENVIRONMENT = None
SHOW_ALERT = True

if "VERSION_TAG" in os.environ:
    RELEASE = config("VERSION_TAG", "")
elif "GIT_SHA" in os.environ:
    RELEASE = config("GIT_SHA", "")
else:
    RELEASE = None

##############################
#                            #
# 3RD PARTY LIBRARY SETTINGS #
#                            #
##############################

#
# DJANGO-AXES
#
AXES_CACHE = "axes"
AXES_LOGIN_FAILURE_LIMIT = 30  # Default: 3
AXES_LOCK_OUT_AT_FAILURE = True  # Default: True
AXES_USE_USER_AGENT = False  # Default: False
AXES_COOLOFF_TIME = 1  # One hour
AXES_BEHIND_REVERSE_PROXY = IS_HTTPS  # We have either Ingress or Nginx
AXES_ONLY_USER_FAILURES = (
    False  # Default: False (you might want to block on username rather than IP)
)
AXES_LOCK_OUT_BY_COMBINATION_USER_AND_IP = (
    False  # Default: False (you might want to block on username and IP)
)

#
# DJANGO-HIJACK
#
HIJACK_LOGIN_REDIRECT_URL = "/"
HIJACK_LOGOUT_REDIRECT_URL = reverse_lazy("admin:accounts_user_changelist")
# The Admin mixin is used because we use a custom User-model.
HIJACK_REGISTER_ADMIN = False
# This is a CSRF-security risk.
# See: http://django-hijack.readthedocs.io/en/latest/configuration/#allowing-get-method-for-hijack-views
HIJACK_ALLOW_GET_REQUESTS = True
HIJACK_AUTHORIZE_STAFF = True
HIJACK_AUTHORIZE_STAFF_TO_HIJACK_STAFF = True

#
# DJANGO AUTH ADFS
#
AUTH_ADFS = {"SETTINGS_CLASS": "django_auth_adfs_db.settings.Settings"}

#
# DRF
#
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.TokenAuthentication",
        "dowc.accounts.authentication.ZGWAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.backends.DjangoFilterBackend",
    ],
    "DEFAULT_RENDERER_CLASSES": (
        "djangorestframework_camel_case.render.CamelCaseJSONRenderer",
    ),
    "DEFAULT_PARSER_CLASSES": (
        "djangorestframework_camel_case.parser.CamelCaseJSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ),
    "DEFAULT_VERSION": "1",
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

#
# SENTRY - error monitoring
#
SENTRY_DSN = config("SENTRY_DSN", None)

SENTRY_SDK_INTEGRATIONS = [
    django.DjangoIntegration(),
    redis.RedisIntegration(),
]

if SENTRY_DSN:
    import sentry_sdk

    SENTRY_CONFIG = {
        "dsn": SENTRY_DSN,
        "release": RELEASE,
    }

    sentry_sdk.init(
        **SENTRY_CONFIG, integrations=SENTRY_SDK_INTEGRATIONS, send_default_pii=True
    )

#
# PRIVATES CONFIGURATION
#
PRIVATE_MEDIA_ROOT = os.path.join(BASE_DIR, "private")
PRIVATE_MEDIA_URL = "/private/"
FILE_UPLOAD_PERMISSIONS = None

#
# SENDFILE CONFIGURATION
#
SENDFILE_ROOT = PRIVATE_MEDIA_ROOT
SENDFILE_URL = PRIVATE_MEDIA_URL
SENDFILE_BACKEND = "sendfile.backends.nginx"

#
# DOCUMENT TOKEN CONFIGURATION
#
DOCUMENT_TOKEN_TIMEOUT_DAYS = 1

# ZGW-CONSUMERS
#
ZGW_CONSUMERS_CLIENT_CLASS = "dowc.client.Client"
ZGW_CONSUMERS_TEST_SCHEMA_DIRS = [
    os.path.join(DJANGO_PROJECT_DIR, "tests", "schemas"),
]

#
# SPECTACULAR
#
SPECTACULAR_SETTINGS = {
    "SCHEMA_PATH_PREFIX": "/api/v1",
    "TITLE": "DO.W.C.",
    "DESCRIPTION": """DO.W.C. facilitates reading and editing centrally located documents on local clients.
This API provides an interface to request the URL required to read/edit a document.""",
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.hooks.postprocess_schema_enums",
        "drf_spectacular.contrib.djangorestframework_camel_case.camelize_serializer_fields",
    ],
    "TOS": None,
    # Optional: MAY contain "name", "url", "email"
    "CONTACT": {
        "url": "https://github.com/GemeenteUtrecht/dowc",
    },
    # Optional: MUST contain "name", MAY contain URL
    "VERSION": "1.0.0",
    # Tags defined in the global scope
    "TAGS": [],
    "SERVERS": [{"url": "https://dowc.cg-intern.ont.utrecht.nl"}],
}
