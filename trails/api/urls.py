from django.urls import path

from api import views

urlpatterns = [
    path("trailheads/", views.nearby_trailheads),
    path("histogram/", views.histogram),
    path("trails/", views.top_trails),
]
