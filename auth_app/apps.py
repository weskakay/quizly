from django.apps import AppConfig


class AuthAppConfig(AppConfig):
    """App holding registration, login, logout and token refresh."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'auth_app'
