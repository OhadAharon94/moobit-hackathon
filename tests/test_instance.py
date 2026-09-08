from qera.config import variable_index
from qera.instance import DEMANDS, LINK_BY_EDGE, PATH_EDGES, SCENARIOS, validate_fixture


def test_fixture_structure() -> None:
    validate_fixture()
    assert len(LINK_BY_EDGE) == 12
    assert len(DEMANDS) == 4
    assert len(SCENARIOS) == 3
    assert all(len(paths) == 3 for paths in PATH_EDGES)


def test_canonical_variable_order() -> None:
    assert [variable_index(d, p) for d in range(4) for p in range(3)] == list(
        range(12)
    )


def test_every_path_uses_existing_edges() -> None:
    for demand_paths in PATH_EDGES:
        for edges in demand_paths:
            assert all(edge in LINK_BY_EDGE for edge in edges)

