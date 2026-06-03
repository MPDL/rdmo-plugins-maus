from django.apps import AppConfig


class RDMOMAUSConfig(AppConfig):
    name = 'rdmo_maus'

    def ready(self):
        import rdmo_maus.checks  # noqa: F401