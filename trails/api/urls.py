from django.urls import path

from api import views

urlpatterns = [
    path('trailheads/', views.nearby_trailheads),
]