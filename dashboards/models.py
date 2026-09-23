import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from datasets.models import Dataset


def generate_share_token():
    return uuid.uuid4().hex


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class Dashboard(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dashboards"
    )
    dataset = models.ForeignKey(
        Dataset, on_delete=models.PROTECT, related_name="dashboards"
    )
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    # Soft delete: deleted_at set instead of removing the row. `objects`
    # (the default manager) hides deleted rows everywhere automatically;
    # `all_objects` is the only way to still find them, e.g. from a shell.
    objects = SoftDeleteManager()
    all_objects = models.Manager()

    def __str__(self):
        return self.title


class Chart(models.Model):
    class ChartType(models.TextChoices):
        LINE = "line", "Line"
        BAR = "bar", "Bar"
        PIE = "pie", "Pie"
        SCATTER = "scatter", "Scatter"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dashboard = models.ForeignKey(
        Dashboard, on_delete=models.CASCADE, related_name="charts"
    )
    chart_type = models.CharField(max_length=20, choices=ChartType.choices)
    x_column = models.CharField(max_length=255)
    y_column = models.CharField(max_length=255)
    narrative = models.TextField(null=True, blank=True)
    x = models.FloatField(default=0)
    y = models.FloatField(default=0)
    width = models.FloatField(default=400, validators=[MinValueValidator(0.01)])
    height = models.FloatField(default=300, validators=[MinValueValidator(0.01)])
    z_index = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.chart_type} ({self.x_column} / {self.y_column})"


class ShareLink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dashboard = models.ForeignKey(
        Dashboard, on_delete=models.CASCADE, related_name="share_links"
    )
    token = models.CharField(
        max_length=32, unique=True, db_index=True, default=generate_share_token
    )
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.token
