###############################################################################
# Imports
###############################################################################
# Python
from collections import Iterable
from importlib import import_module

# Django
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import Q
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.utils.timezone import now

# User
from notifier import managers


###############################################################################
# Models
###############################################################################
class BaseModel(models.Model):
    """Abstract base class with auto-populated created and updated fields. """
    created = models.DateTimeField(default=now, db_index=True)
    updated = models.DateTimeField(default=now, db_index=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.updated = now()
        super(BaseModel, self).save(*args, **kwargs)


class Backend(BaseModel):
    """
    Entries for various delivery backends (SMS, Email)
    """
    name = models.CharField(max_length=200, unique=True, db_index=True)
    display_name = models.CharField(max_length=200, null=True)
    description = models.CharField(max_length=500, null=True)

    # This can be set to False to stop all deliveries using this
    # method, regardless of permissions and preferences
    enabled = models.BooleanField(default=True)

    # The klass value defines the class to be used to send the notification.
    klass = models.CharField(max_length=500,
                             help_text='Example: notifier.backends.EmailBackend')

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name

    def _get_backendclass(self):
        """
        Return the python class from the string value in `self.klass`
        """
        module, klass = self.klass.rsplit('.', 1)
        return getattr(import_module(module), klass)

    backendclass = property(_get_backendclass)

    def send(self, user, notification, context=None):
        """
        Send the notification to the specified user using this backend.

        returns Boolean according to success of delivery.
        """

        backendobject = self.backendclass(notification)
        sent_success = backendobject.send(user, context)

        SentNotification.objects.create(user=user, notification=notification,
                                        backend=self, success=sent_success)

        return sent_success

    def send_anonymous(self, user, notification, context=None):
        """
        Send the notification to the specified user using this backend.
        Anonymous because we don't have a user object.

        returns Boolean according to success of delivery.
        """

        backendobject = self.backendclass(notification)
        sent_success = backendobject.send_anonymous(user, context)

        SentNotification.objects.create(to=user, notification=notification,
                                        backend=self, success=sent_success)

        return sent_success


class Notification(BaseModel):
    """
    Entries for various notifications
    """
    name = models.CharField(max_length=200, unique=True, db_index=True)
    display_name = models.CharField(max_length=200)

    # This field determines whether the notification is to be shown
    #   to users or it is private and only set by code.
    # This only affects UI, the notification is otherwise enabled
    #   and usable in all ways.
    public = models.BooleanField(default=True)

    # user should have all the permissions selected here to be able to change
    # the user prefs for this notification or see it in the UI
    permissions = models.ManyToManyField(Permission, blank=True)

    # These are the backend methods that are allowed for this type of
    # notification
    backends = models.ManyToManyField(Backend, blank=True)

    objects = managers.NotificationManager()

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name

    def check_perms(self, user):
        # Need an iterable with permission strings to check using has_perms.
        # This makes it possible to take advantage of the cache.
        perm_list = set(
            ["%s.%s" % (p.content_type.app_label, p.codename)
             for p in self.permissions.select_related()]
        )

        if not user.has_perms(perm_list):
            return False
        return True

    def get_backends(self, user):
        """
        Returns backends after checking `User` and `Group` preferences
        as well as `backend.enabled` flag.
        """
        user_settings = self.userprefs_set.filter(user=user)
        group_filter = Q()
        groups = user.groups.all()
        for group in groups:
            group_filter = Q(group_filter | Q(group=group))

        group_settings = self.groupprefs_set.filter(group_filter)

        backends = self.backends.filter(enabled=True)

        remove_backends = []
        for backend in backends:
            try:
                userprefs = user_settings.get(backend=backend)
            except UserPrefs.DoesNotExist:
                r = group_settings.filter(backend=backend, notify=True).first()
                if r is None:
                    remove_backends.append(backend.id)
            else:
                if not userprefs.notify:
                    remove_backends.append(backend.id)

        return backends.exclude(id__in=remove_backends)

    def get_user_prefs(self, user):
        """
        Return a dictionary of all available backend methods with True
        or False values depending on preferences.
        """
        all_backends = self.backends.filter(enabled=True)
        selected_backends = self.get_backends(user)

        backend_dict = dict(zip(all_backends, [False] * len(all_backends)))
        for backend in all_backends:
            if backend in selected_backends:
                backend_dict[backend] = True

        return backend_dict

    def update_user_prefs(self, user, prefs_dict):
        """
        Update or create a `UserPrefs` instance as required
        """
        result = {}
        for backend, value in prefs_dict.items():
            if not isinstance(backend, Backend):
                backend = Backend.objects.get(name=backend)

            try:
                userpref = self.userprefs_set.get(
                    user=user,
                    backend=backend
                )
            except UserPrefs.DoesNotExist:
                UserPrefs.objects.create(
                    user=user,
                    notification=self,
                    backend=backend,
                    notify=value
                )
                result[backend.name] = 'created'
            else:
                if userpref.notify != value:
                    userpref.notify = value
                    userpref.save()
                    result[backend.name] = 'updated'
        return result

    def update_group_prefs(self, group, prefs_dict):
        """
        Update or create a `GroupPrefs` instance as required
        """
        result = {}
        for backend, value in prefs_dict.items():
            if not isinstance(backend, Backend):
                backend = Backend.objects.get(name=backend)

            try:
                grouppref = self.groupprefs_set.get(
                    group=group,
                    backend=backend
                )
            except GroupPrefs.DoesNotExist:
                GroupPrefs.objects.create(
                    group=group,
                    notification=self,
                    backend=backend,
                    notify=value
                )
                result[backend.name] = 'created'
            else:
                if grouppref.notify != value:
                    grouppref.notify = value
                    grouppref.save()
                    result[backend.name] = 'updated'
        return result

    def send(self, users, context=None):
        if not isinstance(users, Iterable):
            users = [users]

        for user in users:
            # check if user object
            if isinstance(user, get_user_model()):
                backends = self.get_backends(user)
                for backend in backends:
                    backend.send(user, self, context)
            # check for anonymous email address
            # bypass checks for preferences
            # each backend is responsible for handling the email
            elif isinstance(user, unicode):
                backends = Backend.objects.filter(enabled=True)
                for backend in backends:
                    backend.send_anonymous(user, self, context)


class GroupPrefs(BaseModel):
    """
    Per group notification settings

    If notification is not explicitly set to True, then default to False.
    """
    group = models.ForeignKey(Group)
    notification = models.ForeignKey(Notification)
    backend = models.ForeignKey(Backend)
    notify = models.BooleanField(default=True)

    class Meta:
        unique_together = ('group', 'notification', 'backend')

    def __unicode__(self):
        return '%s:%s:%s' % (self.group, self.notification, self.backend)

    def __str__(self):
        return self.__unicode__()


class UserPrefs(BaseModel):
    """
    Per user notification settings

    Supercedes group setting.
    If notification preference is not explicitly set, then use group setting.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    notification = models.ForeignKey(Notification)
    backend = models.ForeignKey(Backend)
    notify = models.BooleanField(default=True)

    objects = managers.UserPrefsManager()

    class Meta:
        unique_together = ('user', 'notification', 'backend')

    def __unicode__(self):
        return '%s:%s:%s' % (self.user, self.notification, self.backend)

    def __str__(self):
        return self.__unicode__()

    def save(self, *args, **kwargs):
        if not self.notification.check_perms(self.user):
            raise PermissionDenied
        super(UserPrefs, self).save(*args, **kwargs)


class SentNotification(BaseModel):
    """
    Record of every notification sent.
    Either user or to should be filled in.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True)
    to = models.CharField(max_length=255, null=True, blank=True)
    notification = models.ForeignKey(Notification)
    backend = models.ForeignKey(Backend)
    success = models.BooleanField(default=False)
    read = models.BooleanField(default=False)

    def __unicode__(self):
        return '%s:%s:%s' % (self.user, self.notification, self.backend)

    def __str__(self):
        return self.__unicode__()


###############################################################################
# Signal Recievers
###############################################################################
@receiver(pre_delete, sender=Backend,
          dispatch_uid='notifier.models.backend_pre_delete')
def backend_pre_delete(sender, instance, **kwargs):
    raise PermissionDenied(
        'Cannot delete backend %s. Remove from settings.' % instance.name)
