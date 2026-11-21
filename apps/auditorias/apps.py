from django.apps import AppConfig


class AuditoriasConfig(AppConfig):
    name = "apps.auditorias"
    verbose_name = "Auditorias"

    def ready(self):
        from . import sinais  # noqa: F401
