from django.apps import AppConfig
from django.db.models.signals import post_migrate


class NotifierConfig(AppConfig):
    name = 'notifier'

    def ready(self):
        from notifier.management import create_backends, create_notifications

        post_migrate.connect(
            create_backends,
            dispatch_uid="notifier.management.create_backends",
            sender=self
        )
        post_migrate.connect(
            create_notifications,
            dispatch_uid="notifier.management.create_notifications",
            sender=self
        )
