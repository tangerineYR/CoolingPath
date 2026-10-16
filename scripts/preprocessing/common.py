"""Validation shared by the offline preprocessing commands."""
from pathlib import Path

import geopandas as gpd


def read_polygons(path, layer=None):
    frame = gpd.read_file(path, **({'layer': layer} if layer else {}))
    if frame.crs is None:
        raise ValueError('Input CRS is missing; assign the verified source CRS first')
    if frame.empty or frame.geometry.isna().any() or frame.geometry.is_empty.any():
        raise ValueError('Input must contain nonempty polygon geometries')
    if not frame.geometry.is_valid.all():
        raise ValueError('Repair invalid geometries explicitly before preprocessing')
    if not frame.geom_type.isin(['Polygon', 'MultiPolygon']).all():
        raise ValueError('Expected polygon geometries (use buffered roads)')
    return frame.to_crs(5179)


def new_output(path):
    path = Path(path)
    if path.exists():
        raise FileExistsError(f'Refusing to overwrite {path}')
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
