# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Backend',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(default=django.utils.timezone.now, db_index=True)),
                ('updated', models.DateTimeField(default=django.utils.timezone.now, db_index=True)),
                ('name', models.CharField(unique=True, max_length=200, db_index=True)),
                ('display_name', models.CharField(max_length=200, null=True)),
                ('description', models.CharField(max_length=500, null=True)),
                ('enabled', models.BooleanField(default=True)),
                ('klass', models.CharField(help_text=b'Example: notifier.backends.EmailBackend', max_length=500)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GroupPrefs',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(default=django.utils.timezone.now, db_index=True)),
                ('updated', models.DateTimeField(default=django.utils.timezone.now, db_index=True)),
                ('notify', models.BooleanField(default=True)),
                ('backend', models.ForeignKey(to='notifier.Backend')),
                ('group', models.ForeignKey(to='auth.Group')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(default=django.utils.timezone.now, db_index=True)),
                ('updated', models.DateTimeField(default=django.utils.timezone.now, db_index=True)),
                ('name', models.CharField(unique=True, max_length=200, db_index=True)),
                ('display_name', models.CharField(max_length=200)),
                ('public', models.BooleanField(default=True)),
                ('backends', models.ManyToManyField(to='notifier.Backend', blank=True)),
                ('permissions', models.ManyToManyField(to='auth.Permission', blank=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SentNotification',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(default=django.utils.timezone.now, db_index=True)),
                ('updated', models.DateTimeField(default=django.utils.timezone.now, db_index=True)),
                ('success', models.BooleanField(default=False)),
                ('read', models.BooleanField(default=False)),
                ('backend', models.ForeignKey(to='notifier.Backend')),
                ('notification', models.ForeignKey(to='notifier.Notification')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserPrefs',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(default=django.utils.timezone.now, db_index=True)),
                ('updated', models.DateTimeField(default=django.utils.timezone.now, db_index=True)),
                ('notify', models.BooleanField(default=True)),
                ('backend', models.ForeignKey(to='notifier.Backend')),
                ('notification', models.ForeignKey(to='notifier.Notification')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='userprefs',
            unique_together=set([('user', 'notification', 'backend')]),
        ),
        migrations.AddField(
            model_name='groupprefs',
            name='notification',
            field=models.ForeignKey(to='notifier.Notification'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='groupprefs',
            unique_together=set([('group', 'notification', 'backend')]),
        ),
    ]
