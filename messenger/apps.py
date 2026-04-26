from django.apps import AppConfig

class MessengerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'messenger'

    def ready(self):
        # Django ishga tushganda signallarni eshitishni boshlaydi
        import messenger.signals