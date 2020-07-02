from unittest import mock

from rest_framework.test import APIRequestFactory

from api.models import Route


def test_model_export():
    with mock.patch('api.models.Route') as route_mock:
        from api.views import export_gpx
        fake_route = mock.Mock(spec=Route)
        fake_route.nodes = [(0, 0), (1, 1), (2, 2), (0, 0)]
        route_mock.objects = mock.MagicMock()
        route_mock.objects.get = mock.MagicMock(return_value=fake_route)
        factory = APIRequestFactory()
        request = factory.get('/api/export', data={'id': 123})
        resp = export_gpx(request)
        assert resp.status_code == 200
