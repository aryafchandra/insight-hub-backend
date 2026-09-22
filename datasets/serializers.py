from django.conf import settings
from rest_framework import serializers

from .models import Dataset


class DatasetUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dataset
        fields = ["id", "name", "raw_file", "status"]
        read_only_fields = ["id", "status"]

    def validate_raw_file(self, value):
        if not value.name.lower().endswith(".csv"):
            raise serializers.ValidationError("Only .csv files are supported.")
        if value.size > settings.MAX_CSV_UPLOAD_BYTES:
            max_mb = settings.MAX_CSV_UPLOAD_BYTES // (1024 * 1024)
            raise serializers.ValidationError(f"File exceeds the {max_mb}MB upload limit.")
        return value

    def validate(self, attrs):
        if not attrs.get("name"):
            attrs["name"] = attrs["raw_file"].name
        return attrs


class DatasetDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dataset
        fields = [
            "id",
            "name",
            "status",
            "schema",
            "row_count",
            "failure_reason",
            "created_at",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.status != Dataset.Status.READY:
            data.pop("schema", None)
            data.pop("row_count", None)
        if instance.status != Dataset.Status.FAILED:
            data.pop("failure_reason", None)
        return data
