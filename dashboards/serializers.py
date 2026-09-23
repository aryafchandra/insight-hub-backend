from rest_framework import serializers

from datasets.data_access import read_columns
from datasets.models import Dataset

from .models import Chart, Dashboard, ShareLink


class ChartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chart
        fields = [
            "id",
            "dashboard",
            "chart_type",
            "x_column",
            "y_column",
            "narrative",
            "x",
            "y",
            "width",
            "height",
            "z_index",
        ]
        read_only_fields = ["id", "dashboard"]

    def validate(self, attrs):
        dashboard = self.context.get("dashboard") or getattr(self.instance, "dashboard", None)
        schema = dashboard.dataset.schema or []
        valid_columns = {col["name"] for col in schema}

        x_column = attrs.get("x_column", getattr(self.instance, "x_column", None))
        y_column = attrs.get("y_column", getattr(self.instance, "y_column", None))

        if x_column is not None and x_column not in valid_columns:
            raise serializers.ValidationError(
                {"x_column": f"'{x_column}' is not a column in the dataset's schema."}
            )
        if y_column is not None and y_column not in valid_columns:
            raise serializers.ValidationError(
                {"y_column": f"'{y_column}' is not a column in the dataset's schema."}
            )
        return attrs


class DashboardListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dashboard
        fields = ["id", "title", "dataset", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class DashboardDetailSerializer(serializers.ModelSerializer):
    charts = ChartSerializer(many=True, read_only=True)

    class Meta:
        model = Dashboard
        fields = ["id", "title", "dataset", "charts", "created_at", "updated_at"]
        read_only_fields = ["id", "dataset", "charts", "created_at", "updated_at"]


class DashboardCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dashboard
        fields = ["id", "title", "dataset", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request is not None:
            # Scoped so an unowned dataset_id and a nonexistent one both hit
            # the same "does not exist" error — don't let a 400 vs. a
            # different 400 reveal whether someone else's dataset exists.
            self.fields["dataset"].queryset = Dataset.objects.filter(owner=request.user)

    def validate_dataset(self, dataset):
        if dataset.status != Dataset.Status.READY:
            raise serializers.ValidationError(
                "Dataset must be fully processed (status='ready') before it can back a dashboard."
            )
        return dataset


class ShareLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShareLink
        fields = ["token", "created_at"]


class PublicChartSerializer(serializers.ModelSerializer):
    data = serializers.SerializerMethodField()

    class Meta:
        model = Chart
        fields = [
            "id",
            "chart_type",
            "x_column",
            "y_column",
            "narrative",
            "x",
            "y",
            "width",
            "height",
            "z_index",
            "data",
        ]

    def get_data(self, chart):
        dataset = self.context["dataset"]
        return read_columns(dataset, chart.x_column, chart.y_column)


class PublicDashboardSerializer(serializers.ModelSerializer):
    charts = serializers.SerializerMethodField()

    class Meta:
        model = Dashboard
        fields = ["id", "title", "charts", "created_at"]

    def get_charts(self, dashboard):
        serializer = PublicChartSerializer(
            dashboard.charts.all(), many=True, context={"dataset": dashboard.dataset}
        )
        return serializer.data
