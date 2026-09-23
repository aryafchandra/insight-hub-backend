from django.http import FileResponse, Http404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Chart, Dashboard, ShareLink
from .serializers import (
    ChartSerializer,
    DashboardCreateSerializer,
    DashboardDetailSerializer,
    DashboardListSerializer,
    ShareLinkSerializer,
)


def get_owned_dashboard_or_404(user, dashboard_id):
    # 404, not 403 — same "don't leak existence" convention used for
    # datasets/dashboards elsewhere in this project.
    try:
        return Dashboard.objects.get(id=dashboard_id, owner=user)
    except Dashboard.DoesNotExist:
        raise Http404() from None


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

    def perform_destroy(self, instance):
        # Soft delete: flag the row instead of removing it (TICKET-601).
        # Dashboard.objects already excludes deleted_at rows everywhere, so
        # this dashboard, its charts (see ChartDetailView.get_queryset
        # below), and its share links (see public_views.py) all stop
        # resolving immediately without needing a real DELETE.
        instance.deleted_at = timezone.now()
        instance.save(update_fields=["deleted_at"])


class ChartCreateView(generics.CreateAPIView):
    serializer_class = ChartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_dashboard(self):
        if not hasattr(self, "_dashboard"):
            self._dashboard = get_owned_dashboard_or_404(
                self.request.user, self.kwargs["dashboard_id"]
            )
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
        # dashboard__deleted_at is explicit here on purpose: this queries
        # Chart directly, so it does NOT go through Dashboard's own
        # soft-delete manager — a chart under a soft-deleted dashboard would
        # otherwise stay reachable even though the dashboard itself 404s.
        return Chart.objects.filter(
            dashboard__owner=self.request.user, dashboard__deleted_at__isnull=True
        )


class DashboardShareView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id):
        dashboard = get_owned_dashboard_or_404(request.user, id)
        link = ShareLink.objects.filter(dashboard=dashboard, revoked_at__isnull=True).first()
        created = link is None
        if created:
            link = ShareLink.objects.create(dashboard=dashboard)
        return Response(
            ShareLinkSerializer(link).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class DashboardShareRegenerateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id):
        dashboard = get_owned_dashboard_or_404(request.user, id)
        ShareLink.objects.filter(dashboard=dashboard, revoked_at__isnull=True).update(
            revoked_at=timezone.now()
        )
        link = ShareLink.objects.create(dashboard=dashboard)
        return Response(ShareLinkSerializer(link).data, status=status.HTTP_201_CREATED)


class DashboardExportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, id):
        dashboard = get_owned_dashboard_or_404(request.user, id)
        dataset = dashboard.dataset
        response = FileResponse(dataset.raw_file.open("rb"), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{dataset.name}"'
        return response
