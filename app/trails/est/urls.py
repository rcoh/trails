from django.conf.urls import url

from est import views

urlpatterns = [
    url(r'', views.default_map, name='default')
]
