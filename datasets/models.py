import uuid

from django.conf import settings
from django.db import models


def dataset_upload_path(instance, filename):
    return f"datasets/{instance.owner_id}/{instance.id}/{filename}"


class Dataset(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="datasets"
    )
    name = models.CharField(max_length=255)
    raw_file = models.FileField(upload_to=dataset_upload_path)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    schema = models.JSONField(null=True, blank=True)
    row_count = models.IntegerField(null=True, blank=True)
    failure_reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
