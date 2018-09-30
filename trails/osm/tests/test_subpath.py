from unittest.mock import MagicMock

from geopy.distance import Distance

from osm.model import Trail, Subpath


def mock_trail(id, length):
    trail = Trail([MagicMock()], id, f"trail{id}")
    trail.length = MagicMock(return_value=Distance(kilometers=length))
    return trail


def test_subpath_similarity():
    trail_1 = mock_trail(1, 5)
    trail_2 = mock_trail(2, 5)
    trail_3 = mock_trail(3, 5)
    # subpath_1 = Subpath([trail_1, trail_2])
    # subpath_2 = Subpath([trail_1, trail_2])
    # assert subpath_1.similarity(subpath_2) == 1

    assert Subpath([trail_1, trail_2]).similarity(Subpath([trail_2, trail_1])) == 1
    assert Subpath([trail_1]).similarity(Subpath([trail_2])) == 0
    assert Subpath([trail_1, trail_3]).similarity(Subpath([trail_1, trail_2])) == 0.5
