from django.urls import path

from .views import ChartDetailView

app_name = "charts"

urlpatterns = [
    path("<uuid:id>/", ChartDetailView.as_view(), name="chart-detail"),
]
