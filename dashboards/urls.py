from django.urls import path

from .views import (
    ChartCreateView,
    DashboardDetailView,
    DashboardExportView,
    DashboardListCreateView,
    DashboardShareRegenerateView,
    DashboardShareView,
)

app_name = "dashboards"

urlpatterns = [
    path("", DashboardListCreateView.as_view(), name="dashboard-list"),
    path("<uuid:id>/", DashboardDetailView.as_view(), name="dashboard-detail"),
    path(
        "<uuid:dashboard_id>/charts/",
        ChartCreateView.as_view(),
        name="chart-create",
    ),
    path("<uuid:id>/share/", DashboardShareView.as_view(), name="dashboard-share"),
    path(
        "<uuid:id>/share/regenerate/",
        DashboardShareRegenerateView.as_view(),
        name="dashboard-share-regenerate",
    ),
    path("<uuid:id>/export/", DashboardExportView.as_view(), name="dashboard-export"),
]
