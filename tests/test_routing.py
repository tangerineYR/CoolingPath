import networkx as nx
import pytest

from coolingpath.metrics import calc_avg_shadow
from coolingpath.routing import apply_costs, find_constrained_best_path


def test_shade_benefit_and_detour_constraint():
    graph = nx.Graph()
    graph.add_edge("s", "t", length=100, shadow_ratio=0)
    graph.add_edge("s", "a", length=55, shadow_ratio=1)
    graph.add_edge("a", "t", length=55, shadow_ratio=1)
    apply_costs(graph)
    assert nx.shortest_path(graph, "s", "t", weight="cost_cooling") == ["s", "a", "t"]
    assert find_constrained_best_path(
        graph, "s", "t", ["s", "t"], "cost_cooling", 0.14
    ) == ["s", "a", "t"]
    assert find_constrained_best_path(
        graph, "s", "t", ["s", "t"], "cost_cooling", 0.05
    ) == ["s", "t"]


def test_shadow_is_length_weighted():
    graph = nx.Graph()
    graph.add_edge(0, 1, length=25, shadow_ratio=1)
    graph.add_edge(1, 2, length=75, shadow_ratio=0)
    assert calc_avg_shadow(graph, [0, 1, 2]) == pytest.approx(0.25)


def test_rain_changes_cost():
    graph = nx.Graph()
    graph.add_edge(0, 1, length=100, shadow_ratio=0.5)
    apply_costs(graph, rain_mm=0)
    dry = graph[0][1]["cost_shortest"]
    apply_costs(graph, rain_mm=3)
    assert graph[0][1]["cost_shortest"] > dry
