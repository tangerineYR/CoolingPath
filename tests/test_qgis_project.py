"""Portable project checks run in CI without installing the QGIS desktop."""
import csv
from pathlib import Path
import sqlite3
import xml.etree.ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'docs/qgis/CoolingPath_QGIS.qgz'


def test_qgis_has_only_portable_local_layers():
    with ZipFile(PROJECT) as archive:
        xml = archive.read(next(name for name in archive.namelist() if name.endswith('.qgs')))
    root = ET.fromstring(xml)
    assert root.findtext('projectCrs/spatialrefsys/authid') == 'EPSG:5179'
    assert root.findtext('.//properties/Paths/Absolute') == 'false'
    assert not root.findtext('.//properties/Macros/pythonCode')
    layers = root.findall('./projectlayers/maplayer')
    assert len(layers) == 4
    sources = []
    for layer in layers:
        assert layer.findtext('provider') == 'ogr'
        assert layer.findtext('srs/spatialrefsys/authid') == 'EPSG:5179'
        source = layer.findtext('datasource')
        assert source.startswith('./') or source.startswith('../../data/processed/')
        assert '://' not in source and 'authcfg=' not in source
        path = (PROJECT.parent / source.split('|')[0]).resolve()
        assert path.is_relative_to(ROOT) and path.is_file()
        sources.append(source)
    assert len(set(sources)) == 4
    assert b'/workspace/' not in xml and b'/home/' not in xml
    assert b'../../../Documents/' not in xml and b'../../../processing/' not in xml


def test_showcase_matches_repository_statistics():
    path = ROOT / 'docs/qgis/CoolingPath_showcase.gpkg'
    with sqlite3.connect(f'file:{path}?mode=ro', uri=True) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert set(db.execute('SELECT table_name, srs_id FROM gpkg_contents')) == {
            ('shadows_20250708_1400', 5179), ('roads_shade_20250708_1400', 5179)}
        assert db.execute('SELECT count(*) FROM shadows_20250708_1400').fetchone()[0] == 1392
        assert db.execute('SELECT DISTINCT time_slot FROM shadows_20250708_1400').fetchall() == [(14,)]
        rows = db.execute('SELECT link_id, shadow_ratio, time_slot, length_m FROM roads_shade_20250708_1400').fetchall()
    assert len(rows) == len({row[0] for row in rows}) == 971
    with (ROOT / 'data/processed/hourly_link_stat_20250708.csv').open() as handle:
        expected = {int(row['link_id']): float(row['shadow_ratio'])
                    for row in csv.DictReader(handle) if int(row['time_slot']) == 14}
    assert {link: ratio for link, ratio, _, _ in rows} == expected
    assert all(hour == 14 and length > 0 and 0 <= ratio <= 1 for _, ratio, hour, length in rows)
