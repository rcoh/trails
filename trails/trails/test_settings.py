from .settings import *
DATABASES = {
    "default": {
        # In tests, no path => in memory database
        "ENGINE": "django.contrib.gis.db.backends.spatialite",
    }
}
