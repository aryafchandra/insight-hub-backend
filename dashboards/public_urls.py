from django.urls import path

from .public_views import PublicDashboardView

app_name = "public-dashboards"

urlpatterns = [
    path("<str:token>/", PublicDashboardView.as_view(), name="public-dashboard-detail"),
]
