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
    dry = graph[0][1]["cost_walkability"]
    apply_costs(graph, rain_mm=3)
    assert graph[0][1]["cost_walkability"] > dry


def test_shortest_distance_ignores_facilities_and_rain():
    graph = nx.Graph()
    graph.add_edge("s", "t", length=100, tunnel=True)
    graph.add_edge("s", "a", length=55)
    graph.add_edge("a", "t", length=55)
    apply_costs(graph, rain_mm=3)
    baseline = nx.shortest_path(graph, "s", "t", weight="length")
    assert baseline == ["s", "t"]
    assert nx.shortest_path(graph, "s", "t", weight="cost_walkability") != baseline
    assert find_constrained_best_path(
        graph, "s", "t", baseline, "cost_walkability", 0.05
    ) == baseline


def test_no_silent_parallel_edge_loss():
    import geopandas as gpd
    import pandas as pd
    from shapely.geometry import LineString
    from coolingpath.routing import build_base_graph_with_shadow

    roads = gpd.GeoDataFrame([
        dict(u=0, v=1, link_id=2, length=110, geometry=LineString([(0, 0), (1, 0)])),
        dict(u=1, v=0, link_id=1, length=100, geometry=LineString([(1, 0), (0, 0)])),
    ], crs=5179)
    shadow = pd.DataFrame(dict(link_id=[1, 2], time_slot=[8, 8], shadow_ratio=[0.1, 0.9]))
    for ordered in [roads, roads.iloc[::-1]]:
        build_base_graph_with_shadow.clear()
        with pytest.warns(UserWarning, match="Parallel road policy"):
            graph = build_base_graph_with_shadow(ordered, shadow)
        assert graph[0][1]["link_id"] == 1
        assert graph[0][1]["shadow_by_hour"][8] == 0.1
        assert graph.graph["omitted_parallel_links"] == [{"retained": 1, "omitted": 2}]
    build_base_graph_with_shadow.clear()


def test_temperature_proxy_is_explicit():
    from coolingpath.metrics import build_forecast_for_graph
    env = {"raw_forecast": [dict(time="14:00", hour=14, temp=35, rain=0, humidity=60)]}
    row = build_forecast_for_graph(env, 0.4, 14)[0]
    assert row["shade_adjusted_temp"] == 33.0
    assert "feels_like" not in row
