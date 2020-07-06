from django.conf import settings


def react_mode(context):
    return {'react_version': 'development' if settings.DEBUG else 'production.min'}
