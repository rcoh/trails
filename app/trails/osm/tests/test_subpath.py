from unittest.mock import MagicMock

from geopy.distance import Distance

from osm.model import Trail, Subpath, Node


def mock_trail(id, length, start_node_id=None, end_node_id=None):
    trail = Trail([MagicMock()], id, f"trail{id}")
    trail.length = MagicMock(return_value=Distance(meters=length))
    trail.reverse = MagicMock(return_value=trail)
    trail.nodes = [Node(start_node_id, 0, 0), Node(end_node_id, 0, 0)]
    return trail


def test_subpath_similarity():
    trail_1 = mock_trail(1, 5)
    trail_2 = mock_trail(2, 5)
    trail_3 = mock_trail(3, 5)
    # subpath_1 = Subpath([trail_1, trail_2])
    # subpath_2 = Subpath([trail_1, trail_2])
    # assert subpath_1.similarity(subpath_2) == 1

    assert (
            Subpath.from_segments([trail_1, trail_2]).similarity(
                Subpath.from_segments([trail_2, trail_1])
            )
            == 1
    )
    assert (
            Subpath.from_segments([trail_1]).similarity(Subpath.from_segments([trail_2]))
            == 0
    )
    assert (
            Subpath.from_segments([trail_1, trail_3]).similarity(
                Subpath.from_segments([trail_1, trail_2])
            )
            == 0.5
    )


def test_subpath_length():
    trail_1 = mock_trail(1, 5)
    trail_2 = mock_trail(2, 6)
    trail_3 = mock_trail(3, 7)

    path = Subpath.from_segments([trail_1])
    assert path.unique_length_m == 5
    assert path.length_m == 5

    path = path.add_node(trail_2)
    assert path.unique_length_m == 11
    assert path.length_m == 11

    path = path.add_node(trail_1)
    assert path.unique_length_m == 11
    assert path.length_m == 16

    path = path.add_node(trail_3)
    assert path.unique_length_m == 18
    assert path.length_m == 23


def test_subpath_intersections():
    t1 = mock_trail(0, 1, 1, 2)
    t2 = mock_trail(1, 1, 2, 3)
    t3 = mock_trail(2, 1, 3, 4)
    t4 = mock_trail(3, 1, 4, 2)
    t5 = mock_trail(3, 1, 2, 1)

    # 1 -> 2 -> 3 -> 4 -> 2 -> 1
    s = Subpath.from_startnode(t1.nodes[0])
    segments = [t1, t2, t3, t4, t5]
    for segment in segments:
        s = s.add_node(segment)
    assert s.compute_intersections() == {2: {0, 1, 3}, 3: {1, 2}, 4: {2, 3}}


