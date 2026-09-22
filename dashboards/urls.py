from django.urls import path

from .views import ChartCreateView, DashboardDetailView, DashboardListCreateView

app_name = "dashboards"

urlpatterns = [
    path("", DashboardListCreateView.as_view(), name="dashboard-list"),
    path("<uuid:id>/", DashboardDetailView.as_view(), name="dashboard-detail"),
    path(
        "<uuid:dashboard_id>/charts/",
        ChartCreateView.as_view(),
        name="chart-create",
    ),
]
