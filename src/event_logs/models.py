from django.conf import settings
from django.db import models
from django.utils import timezone


class EventLogModel(models.Model):
    event_type = models.TextField()
    event_date_time = models.DateTimeField(default=timezone.now, db_index=True)
    environment = models.TextField(default=settings.ENVIRONMENT)
    event_context = models.TextField()
    is_published = models.BooleanField(default=False)
