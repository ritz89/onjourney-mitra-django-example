from .base import *  # noqa: F403

DEBUG = True
SECRET_KEY = "django-insecure-public-demo-only"
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
ONJOURNEY_DEMO_MODE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
