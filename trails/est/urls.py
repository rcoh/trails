from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from est import views

urlpatterns = [
    path('', views.default_map, name='index'),
    path('about', views.about, name='about'),
    path('api/default', views.base_map, name='default'),
    path('api/areas', views.areas, name='areas'),
    path('api/circuit/<str:network_id>/', views.circuit, name='circuits'),
    path('api/circuit/<str:circuit_id>/gpx', views.gpx, name='gpx'),
    path('api/import', csrf_exempt(views.external_import), name='import')
]
