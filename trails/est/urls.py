from django.urls import path

from est import views

urlpatterns = [
    path('', views.default_map, name='index'),
    path('about', views.about, name='about'),
    path('api/default', views.base_map, name='default'),
    path('api/areas', views.areas, name='areas'),
    path('api/circuit/<str:network_id>/', views.circuit, name='circuits'),
    path('api/circuit/<str:circuit_id>/gpx', views.gpx, name='gpx'),
]
