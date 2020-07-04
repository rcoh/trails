from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from est import views, admin

urlpatterns = [
    path('', views.default_map, name='index'),
    path('about', views.about, name='about'),
    path('api/default', views.base_map, name='default'),
    path('api/areas', views.areas, name='areas'),
    path('api/circuit/<str:network_id>/', views.compute_circuit, name='circuits'),
    path('api/circuit/<str:circuit_id>/gpx', views.gpx, name='gpx'),
    path('api/circuit/<str:circuit_id>/json', views.circuit_json, name='circuit-json'),
    path('api/network/<str:network_id>/', views.network, name='network'),
    path('api/import', csrf_exempt(views.external_import), name='import'),
]
