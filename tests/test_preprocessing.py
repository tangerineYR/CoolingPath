from datetime import date

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import box

pytest.importorskip("pysolar", reason="Install .[preprocessing] to run pipeline tests")

from scripts.preprocessing.aggregate_shadow_by_link import aggregate_shadow_by_link
from scripts.preprocessing.common import new_output, read_polygons
from scripts.preprocessing.generate_shadows import generate_shadows, make_shadow_ghost
from scripts.preprocessing.generate_solar_scenarios import generate_solar_scenarios


def test_solar_scenario_matches_historical_location():
    solar = generate_solar_scenarios(date(2025, 7, 8))
    assert list(solar.time_slot) == list(range(8, 20))
    assert solar.iloc[0].sun_altitude == pytest.approx(29.55, abs=0.1)
    assert solar.iloc[0].sun_azimuth == pytest.approx(83.16, abs=0.1)
    assert solar.timestamp_kst.str.endswith('+09:00').all()


def test_ghost_direction_and_extent():
    building = box(0, 0, 10, 10)
    shadow = make_shadow_ghost(building, 10, 45, 90, steps=7)
    assert shadow.bounds == pytest.approx((-10, 0, 10, 10))
    assert shadow.area == pytest.approx(200)
    assert make_shadow_ghost(building, 10, 0, 90) is None
    with pytest.raises(ValueError):
        make_shadow_ghost(building, 10, 45, 90, steps=0)
    with pytest.raises(ValueError):
        make_shadow_ghost(building, float('nan'), 45, 90)


def test_overlapping_buildings_and_unshaded_links():
    roads = gpd.GeoDataFrame({'link_id': [1, 2]},
                            geometry=[box(0, 0, 10, 10), box(20, 0, 30, 10)], crs=5179)
    shadows = gpd.GeoDataFrame({'time_slot': [8, 8]},
                              geometry=[box(0, 0, 6, 10), box(4, 0, 8, 10)], crs=5179)
    assert list(aggregate_shadow_by_link(roads, shadows).shadow_ratio) == pytest.approx([0.8, 0])
    legacy = aggregate_shadow_by_link(roads, shadows, 'legacy-sum')
    assert list(legacy.shadow_ratio) == pytest.approx([1, 0])
    with pytest.raises(ValueError, match='unique'):
        aggregate_shadow_by_link(pd.concat([roads, roads]), shadows)


def test_pipeline_file_roundtrip_and_no_overwrite(tmp_path):
    buildings = gpd.GeoDataFrame({'height': [10]}, geometry=[box(0, 0, 10, 10)], crs=5179)
    solar = pd.DataFrame({'time_slot': [8], 'sun_altitude': [45], 'sun_azimuth': [90],
                          'timestamp_kst': ['2025-07-08 08:00:00+09:00']})
    shadows = generate_shadows(buildings, solar, simplify=0)
    path = new_output(tmp_path / 'shadows.gpkg')
    shadows.to_file(path, layer='hourly_shadows', driver='GPKG')
    restored = read_polygons(path, layer='hourly_shadows')
    roads = gpd.GeoDataFrame({'link_id': [1]}, geometry=[box(-10, 0, 0, 10)], crs=5179)
    assert aggregate_shadow_by_link(roads, restored).iloc[0].shadow_ratio == pytest.approx(1)
    with pytest.raises(FileExistsError):
        new_output(path)
    with pytest.raises(ValueError, match='CRS'):
        generate_shadows(buildings.set_crs(None, allow_override=True), solar)
