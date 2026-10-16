from streamlit.testing.v1 import AppTest

from coolingpath.config import ROOT_DIR
from coolingpath.data import load_roads, load_shadow_data
from coolingpath.routing import build_base_graph_with_shadow


def test_data_and_graph_from_other_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    roads = load_roads()
    shadow = load_shadow_data()
    assert len(roads) > 0
    assert shadow.shadow_ratio.between(0, 1).all()
    assert set(roads.link_id).intersection(shadow.link_id)
    graph = build_base_graph_with_shadow(roads, shadow)
    assert graph.number_of_edges() > 0
    assert graph.number_of_edges() + len(graph.graph["omitted_parallel_links"]) == len(roads)
    for omitted in graph.graph["omitted_parallel_links"]:
        lengths = roads.set_index("link_id")["length"]
        assert lengths[omitted["retained"]] <= lengths[omitted["omitted"]]
    assert all("crosswalk" in d for _, _, d in graph.edges(data=True))


def test_streamlit_initial_screen():
    app = AppTest.from_file(str(ROOT_DIR / "app.py")).run(timeout=60)
    assert not app.exception


def test_demo_search_without_external_api(monkeypatch):
    from coolingpath.ui import app as ui
    import geopandas as gpd
    from shapely.geometry import Point

    roads = load_roads()
    line = roads.geometry.iloc[0]
    points = gpd.GeoSeries(
        [Point(line.coords[0]), Point(line.coords[-1])], crs=roads.crs
    ).to_crs(4326)
    answers = iter([(p.y, p.x, name) for p, name in zip(points, ["start", "end"])])
    monkeypatch.setattr(ui, "search_place_kakao", lambda query: next(answers))
    app = AppTest.from_file(str(ROOT_DIR / "app.py")).run(timeout=60)
    next(r for r in app.radio if r.label == "기온 데이터 모드").set_value(
        "폭염 (demo)"
    ).run()
    next(b for b in app.button if b.label == "경로 탐색").click().run(timeout=60)
    assert not app.exception
    assert app.session_state["route_ready"]
