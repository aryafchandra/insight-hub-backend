from django.http import Http404
from rest_framework import generics, permissions

from .models import Chart, Dashboard
from .serializers import (
    ChartSerializer,
    DashboardCreateSerializer,
    DashboardDetailSerializer,
    DashboardListSerializer,
)


class DashboardListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Dashboard.objects.filter(owner=self.request.user)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return DashboardCreateSerializer
        return DashboardListSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class DashboardDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DashboardDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"
    lookup_url_kwarg = "id"
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        # Ownership-scoped so a dashboard owned by someone else 404s rather
        # than 403ing — same "don't leak existence" convention as datasets.
        return Dashboard.objects.filter(owner=self.request.user)


class ChartCreateView(generics.CreateAPIView):
    serializer_class = ChartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_dashboard(self):
        if not hasattr(self, "_dashboard"):
            try:
                self._dashboard = Dashboard.objects.get(
                    id=self.kwargs["dashboard_id"], owner=self.request.user
                )
            except Dashboard.DoesNotExist:
                # 404, not 403 — same "don't leak existence" convention used
                # for datasets/dashboards elsewhere in this project.
                raise Http404() from None
        return self._dashboard

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["dashboard"] = self.get_dashboard()
        return context

    def perform_create(self, serializer):
        serializer.save(dashboard=self.get_dashboard())


class ChartDetailView(generics.UpdateAPIView, generics.DestroyAPIView):
    serializer_class = ChartSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"
    lookup_url_kwarg = "id"

    def get_queryset(self):
        return Chart.objects.filter(dashboard__owner=self.request.user)
