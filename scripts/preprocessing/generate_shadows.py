"""Notebook-derived discrete Shadow Ghosting, not an exact swept shadow."""
import argparse
import math

import geopandas as gpd
import pandas as pd
from shapely.affinity import translate
from shapely.ops import unary_union

from .common import new_output, read_polygons


def make_shadow_ghost(geometry, height, sun_alt, sun_azi, steps=7):
    if not isinstance(steps, int) or steps < 1:
        raise ValueError('steps must be a positive integer')
    if any(not math.isfinite(v) for v in (height, sun_alt, sun_azi)) or height < 0:
        raise ValueError('Height and solar angles must be finite; height must be nonnegative')
    if not -90 <= sun_alt <= 90 or not 0 <= sun_azi <= 360:
        raise ValueError('Invalid solar angle')
    if sun_alt <= 0 or geometry is None:
        return None
    if geometry.is_empty or not geometry.is_valid or geometry.geom_type not in ('Polygon', 'MultiPolygon'):
        raise ValueError('A valid nonempty polygon is required')
    length = height / math.tan(math.radians(max(sun_alt, 0.1)))
    dx = -length * math.sin(math.radians(sun_azi))
    dy = -length * math.cos(math.radians(sun_azi))
    return unary_union([translate(geometry, xoff=dx*i/steps, yoff=dy*i/steps)
                        for i in range(steps + 1)])


def generate_shadows(buildings, solar, height_column='height', steps=7, simplify=0.3):
    if buildings.crs is None:
        raise ValueError('Building CRS is required')
    if not math.isfinite(simplify) or simplify < 0:
        raise ValueError('Simplification tolerance must be nonnegative and finite')
    required = {'time_slot', 'sun_altitude', 'sun_azimuth', 'timestamp_kst'}
    if not required.issubset(solar.columns) or solar.empty or solar.time_slot.duplicated().any():
        raise ValueError('Solar scenario needs unique hours and solar/timestamp fields')
    buildings = buildings.to_crs(5179).copy()
    buildings.geometry = buildings.geometry.simplify(simplify)
    rows = []
    for sun in solar.itertuples(index=False):
        hour = int(sun.time_slot)
        if hour != sun.time_slot or not 0 <= hour <= 23:
            raise ValueError('Invalid time_slot')
        stamp = pd.Timestamp(sun.timestamp_kst)
        if stamp.tzinfo is None or stamp.tz_convert('Asia/Seoul').hour != hour:
            raise ValueError('Scenario timestamp must match the KST time_slot')
        for idx, building in buildings.iterrows():
            geom = make_shadow_ghost(building.geometry, float(building[height_column]),
                                     sun.sun_altitude, sun.sun_azimuth, steps)
            if geom is not None:
                rows.append(dict(build_id=str(idx), time_slot=hour,
                                 timestamp=stamp.tz_convert('Asia/Seoul').tz_localize(None),
                                 geometry=geom))
    if not rows:
        raise ValueError('Scenario produced no daylight shadows')
    return gpd.GeoDataFrame(rows, crs=5179)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--buildings', required=True)
    parser.add_argument('--solar', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--height-column', default='height')
    parser.add_argument('--steps', type=int, default=7)
    parser.add_argument('--simplify', type=float, default=0.3)
    args = parser.parse_args()
    output = new_output(args.output)
    result = generate_shadows(read_polygons(args.buildings), pd.read_csv(args.solar),
                              args.height_column, args.steps, args.simplify)
    result.to_file(output, driver='GPKG', layer='hourly_shadows')


if __name__ == '__main__':
    main()
