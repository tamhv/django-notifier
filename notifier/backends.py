###############################################################################
# Imports
###############################################################################
# Python
from smtplib import SMTPException

# Django
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.template.loader import render_to_string


###############################################################################
# Code
###############################################################################
class BaseBackend(object):
    # Name of backend method associated with this class
    name = None
    display_name = None
    description = None

    def __init__(self, notification, *args, **kwargs):
        self.notification = notification
        self.template = ('/notifier/%s/%s.txt' %
                         (notification.name, self.name))

    # Define how to send the notification
    def send(self, user, context=None):
        if not context:
            self.context = {}
        else:
            self.context = context

        self.context.update({
            'user': user,
            'site': Site.objects.get_current() if settings.SITE_ID else None
        })


class EmailBackend(BaseBackend):
    name = 'email'
    display_name = 'Email'
    description = 'Send via email'

    def __init__(self, notification, *args, **kwargs):
        super(EmailBackend, self).__init__(notification, *args, **kwargs)

        self.template_subject = (
            'notifier/%s/%s_subject.txt' % (notification.name, self.name)
        )
        self.template_text_message = (
            'notifier/%s/%s_text_message.txt' % (notification.name, self.name)
        )
        self.template_html_message = (
            'notifier/%s/%s_html_message.txt' % (notification.name, self.name)
        )

    def send(self, user, context=None):
        super(EmailBackend, self).send(user, context)

        subject = render_to_string(self.template_subject, self.context)
        subject = ''.join(subject.splitlines())
        text_message = render_to_string(self.template_text_message,
                                        self.context)
        html_message = render_to_string(self.template_html_message,
                                        self.context)

        try:
            send_mail(subject=subject, message=text_message,
                      from_email=settings.DEFAULT_FROM_EMAIL,
                      reciepent_list=[user.email, ],
                      html_message=html_message)
        except SMTPException:
            return False
        else:
            return True
