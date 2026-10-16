"""Aggregate road/shadow intersections with an explicit overlap policy."""
import argparse

import pandas as pd

from .common import new_output, read_polygons


def aggregate_shadow_by_link(roads, shadows, overlap_policy='union'):
    if overlap_policy not in ('union', 'legacy-sum'):
        raise ValueError('Unknown overlap policy')
    if roads.crs is None or shadows.crs is None:
        raise ValueError('Road and shadow CRS are required')
    roads, shadows = roads.to_crs(5179), shadows.to_crs(5179)
    if roads.empty or roads.link_id.isna().any() or roads.link_id.duplicated().any():
        raise ValueError('Road link_id must be non-null and unique')
    if (roads.area <= 0).any():
        raise ValueError('Road buffer area must be positive')
    if shadows.empty or shadows.time_slot.isna().any():
        raise ValueError('Shadow hours are required')
    result = []
    for hour, hourly in shadows.groupby('time_slot', sort=True):
        if int(hour) != hour or not 0 <= hour <= 23:
            raise ValueError('Invalid shadow hour')
        for road in roads.itertuples(index=False):
            # Spatial index avoids intersecting every building with every road.
            matches = hourly.sindex.query(road.geometry, predicate='intersects')
            pieces = hourly.geometry.iloc[matches].intersection(road.geometry)
            if overlap_policy == 'union':
                area = pieces.union_all().area
            else:
                # Notebook compatibility: overlapping buildings count repeatedly.
                area = pieces.area.sum()
            ratio = min(1.0, max(0.0, area / road.geometry.area))
            result.append(dict(link_id=road.link_id, time_slot=int(hour), shadow_ratio=ratio))
    return pd.DataFrame(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--roads', required=True)
    parser.add_argument('--shadows', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--overlap-policy', choices=['union', 'legacy-sum'], default='union')
    args = parser.parse_args()
    output = new_output(args.output)
    result = aggregate_shadow_by_link(read_polygons(args.roads),
                                     read_polygons(args.shadows, layer='hourly_shadows'),
                                     args.overlap_policy)
    result.to_csv(output, index=False)


if __name__ == '__main__':
    main()
