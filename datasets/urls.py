from django.urls import path

from .views import (
    ChartTypeSuggestionView,
    DatasetDataView,
    DatasetDetailView,
    DatasetListCreateView,
    DatasetPreviewView,
)

app_name = "datasets"

urlpatterns = [
    path("", DatasetListCreateView.as_view(), name="dataset-list"),
    path("<uuid:id>/", DatasetDetailView.as_view(), name="dataset-detail"),
    path("<uuid:id>/preview/", DatasetPreviewView.as_view(), name="dataset-preview"),
    path("<uuid:id>/data/", DatasetDataView.as_view(), name="dataset-data"),
    path(
        "<uuid:id>/suggest-chart-type/",
        ChartTypeSuggestionView.as_view(),
        name="dataset-suggest-chart-type",
    ),
]
