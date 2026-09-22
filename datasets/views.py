import django_rq
from rest_framework import generics, permissions

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
