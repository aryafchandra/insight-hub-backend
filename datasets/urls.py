from django.urls import path

from .views import DatasetDetailView, DatasetListCreateView

app_name = "datasets"

urlpatterns = [
    path("", DatasetListCreateView.as_view(), name="dataset-list"),
    path("<uuid:id>/", DatasetDetailView.as_view(), name="dataset-detail"),
]
