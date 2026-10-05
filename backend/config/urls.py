from django.urls import path

from traces import views

urlpatterns = [
    path("api/health", views.health),
    path("api/overview", views.overview),
    path("api/traces/<str:trace_id>", views.trace_detail),
]
