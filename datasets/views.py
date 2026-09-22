import django_rq
from rest_framework import generics, permissions
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .chart_suggestion import suggest_chart_type
from .data_access import read_columns, read_preview
from .jobs import parse_dataset
from .models import Dataset
from .serializers import DatasetDetailSerializer, DatasetUploadSerializer


class DatasetListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Dataset.objects.filter(owner=self.request.user)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return DatasetUploadSerializer
        return DatasetDetailSerializer

    def perform_create(self, serializer):
        dataset = serializer.save(owner=self.request.user)
        django_rq.get_queue("default").enqueue(parse_dataset, dataset.id)


class DatasetDetailView(generics.RetrieveAPIView):
    serializer_class = DatasetDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"
    lookup_url_kwarg = "id"

    def get_queryset(self):
        # Scoped to the requesting user so a dataset owned by someone else
        # 404s rather than 403ing (don't leak existence — see CLAUDE.md
        # convention applied elsewhere to share links).
        return Dataset.objects.filter(owner=self.request.user)


class _OwnedReadyDatasetMixin:
    permission_classes = [permissions.IsAuthenticated]

    def get_dataset(self):
        dataset = generics.get_object_or_404(
            Dataset.objects.filter(owner=self.request.user), id=self.kwargs["id"]
        )
        if dataset.status != Dataset.Status.READY:
            raise ValidationError(
                "Dataset is not ready yet — wait for status to become 'ready'."
            )
        return dataset


class DatasetPreviewView(_OwnedReadyDatasetMixin, APIView):
    def get(self, request, id):
        dataset = self.get_dataset()
        return Response(read_preview(dataset))


class DatasetDataView(_OwnedReadyDatasetMixin, APIView):
    def get(self, request, id):
        dataset = self.get_dataset()
        x_column = request.query_params.get("x")
        y_column = request.query_params.get("y")
        valid_columns = {col["name"] for col in dataset.schema or []}

        if not x_column or not y_column:
            raise ValidationError("Both 'x' and 'y' query parameters are required.")
        if x_column not in valid_columns or y_column not in valid_columns:
            raise ValidationError("'x' and 'y' must reference columns in the dataset's schema.")

        return Response(read_columns(dataset, x_column, y_column))


class ChartTypeSuggestionView(_OwnedReadyDatasetMixin, APIView):
    def get(self, request, id):
        dataset = self.get_dataset()
        valid_columns = {col["name"]: col["type"] for col in dataset.schema or []}

        x_column = request.query_params.get("x")
        y_column = request.query_params.get("y")

        if not x_column:
            raise ValidationError("The 'x' query parameter is required.")
        if x_column not in valid_columns:
            raise ValidationError("'x' must reference a column in the dataset's schema.")
        if y_column is not None and y_column not in valid_columns:
            raise ValidationError("'y' must reference a column in the dataset's schema.")

        x_type = valid_columns[x_column]
        y_type = valid_columns[y_column] if y_column else None
        return Response({"suggested_chart_type": suggest_chart_type(x_type, y_type)})
