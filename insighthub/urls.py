from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/", include("accounts.urls")),
    path("datasets/", include("datasets.urls")),
    path("dashboards/", include("dashboards.urls")),
    path("charts/", include("dashboards.chart_urls")),
]
