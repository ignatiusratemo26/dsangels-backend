from django.apps import AppConfig


class AiEngineConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ai_engine"
    verbose_name = "AI Engine"

    def ready(self):
        # from . import utils
        # utils.initialize_curated_content()
        pass
