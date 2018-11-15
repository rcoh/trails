from django.urls import path, include

from api import views
from trails import settings

urlpatterns = [
    path("trailheads/", views.nearby_trailheads),
    path("histogram/", views.histogram),
    path("trails/", views.top_trails),
    path("export/", views.export_gpx),
    path("statusz", views.statusz),
    path("meta/", views.meta),
]

# if settings.DEBUG:
#    import debug_toolbar
#    urlpatterns = [
#        path('__debug__/', include(debug_toolbar.urls)),
#
#        # For django versions before 2.0:
#        # url(r'^__debug__/', include(debug_toolbar.urls)),

#    ] + urlpatterns
