"""Build an offline QGIS portfolio project from repository data.

Run with a Python interpreter that provides PyQGIS (not the app virtualenv).
Input shadows are produced by scripts.preprocessing.generate_shadows.
"""
import argparse
import csv
import os
from xml.dom import minidom
from zipfile import ZipFile, ZIP_DEFLATED
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from qgis.core import (
    Qgis, QgsApplication, QgsCoordinateReferenceSystem, QgsFeature,
    QgsField, QgsFillSymbol, QgsGraduatedSymbolRenderer, QgsLayoutExporter,
    QgsLayoutItemLabel, QgsLayoutItemLegend, QgsLayoutItemMap,
    QgsLayoutPoint, QgsLayoutSize, QgsLineSymbol, QgsPrintLayout,
    QgsProject, QgsRectangle, QgsRendererRange,
    QgsVectorFileWriter, QgsVectorLayer,
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QFont

ROOT = Path(__file__).resolve().parents[2]


def load_layer(path, name, table=None):
    uri = str(path) + (f'|layername={table}' if table else '')
    layer = QgsVectorLayer(uri, name, 'ogr')
    if not layer.isValid() or layer.featureCount() == 0:
        raise ValueError(f'Invalid or empty layer: {name}')
    if layer.crs().authid() != 'EPSG:5179':
        raise ValueError(f'Expected EPSG:5179 for {name}')
    return layer


def write_layer(layer, output, table, first=False):
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = 'GPKG'
    options.layerName = table
    options.actionOnExistingFile = (
        QgsVectorFileWriter.CreateOrOverwriteFile if first
        else QgsVectorFileWriter.CreateOrOverwriteLayer
    )
    error = QgsVectorFileWriter.writeAsVectorFormatV3(
        layer, str(output), QgsProject.instance().transformContext(), options
    )
    if error[0] != QgsVectorFileWriter.NoError:
        raise RuntimeError(f'Cannot write {table}: {error[1]}')


def create_showcase(shadow_path, output):
    """Copy only the chosen hour and public analysis attributes."""
    source = load_layer(shadow_path, 'Generated shadows', 'hourly_shadows')
    shadows = QgsVectorLayer('MultiPolygon?crs=EPSG:5179', 'Shadows', 'memory')
    provider = shadows.dataProvider()
    provider.addAttributes([QgsField('build_id', QVariant.String),
                            QgsField('time_slot', QVariant.Int)])
    shadows.updateFields()
    for original in source.getFeatures():
        if original['time_slot'] != 14:
            continue
        if original['timestamp'].toString('yyyy-MM-dd HH:mm') != '2025-07-08 14:00':
            raise ValueError('Expected the 2025-07-08 14:00 KST scenario')
        feature = QgsFeature(shadows.fields())
        geometry = original.geometry()
        geometry.convertToMultiType()
        feature.setGeometry(geometry)
        feature.setAttributes([str(original['build_id']), 14])
        if not provider.addFeatures([feature])[0]:
            raise RuntimeError('Cannot copy shadow geometry')
    shadows.updateExtents()
    if shadows.featureCount() != 1392:
        raise ValueError('Expected 1,392 building shadows at 14:00')
    write_layer(shadows, output, 'shadows_20250708_1400', first=True)

    source = load_layer(ROOT / 'data/processed/non_buffered_roads.shp', 'Roads')
    with (ROOT / 'data/processed/hourly_link_stat_20250708.csv').open() as handle:
        ratios = {int(row['link_id']): float(row['shadow_ratio'])
                  for row in csv.DictReader(handle) if int(row['time_slot']) == 14}
    roads = QgsVectorLayer('MultiLineString?crs=EPSG:5179', 'Roads', 'memory')
    provider = roads.dataProvider()
    provider.addAttributes([QgsField('link_id', QVariant.LongLong),
                            QgsField('length_m', QVariant.Double),
                            QgsField('time_slot', QVariant.Int),
                            QgsField('shadow_ratio', QVariant.Double)])
    roads.updateFields()
    for original in source.getFeatures():
        link_id = int(original['link_id'])
        ratio = ratios[link_id]
        if not 0 <= ratio <= 1:
            raise ValueError('Invalid shade ratio')
        feature = QgsFeature(roads.fields())
        geometry = original.geometry()
        geometry.convertToMultiType()
        feature.setGeometry(geometry)
        feature.setAttributes([link_id, float(original['length']), 14, ratio])
        if not provider.addFeatures([feature])[0]:
            raise RuntimeError('Cannot copy road geometry')
    roads.updateExtents()
    if roads.featureCount() != 971:
        raise ValueError('Expected 971 road links')
    write_layer(roads, output, 'roads_shade_20250708_1400')


def sanitize_project_metadata(path):
    # QGIS 3.40 writes absolute fallback sources for pinned layout layers even
    # with relative project paths. Use the already-relative primary sources.
    with ZipFile(path) as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}
    name = next(name for name in entries if name.endswith('.qgs'))
    xml = minidom.parseString(entries[name])
    sources = {}
    for layer in xml.getElementsByTagName('maplayer'):
        layer_id = layer.getElementsByTagName('id')[0].firstChild.nodeValue
        source = layer.getElementsByTagName('datasource')[0].firstChild.nodeValue
        sources[layer_id] = source
    for layer in xml.getElementsByTagName('Layer'):
        if layer.hasAttribute('source') and layer.firstChild:
            layer_id = layer.firstChild.nodeValue
            if layer_id in sources:
                layer.setAttribute('source', sources[layer_id])
    xml.documentElement.setAttribute('saveUser', '')
    xml.documentElement.setAttribute('saveUserFull', '')
    entries[name] = xml.toxml(encoding='UTF-8')
    temporary = path.with_suffix('.tmp')
    with ZipFile(temporary, 'w', compression=ZIP_DEFLATED) as archive:
        for entry, content in entries.items():
            archive.writestr(entry, content)
    temporary.replace(path)


def check_project(path):
    project = QgsProject()
    if not project.read(str(path)):
        raise ValueError('Cannot open project')
    if project.crs().authid() != 'EPSG:5179' or len(project.mapLayers()) != 4:
        raise ValueError('Wrong project CRS or layer inventory')
    expected = [971, 971, 1392, 1392]
    layers = list(project.mapLayers().values())
    assert sorted(layer.featureCount() for layer in layers) == expected
    for layer in layers:
        assert layer.isValid() and layer.providerType() == 'ogr'
        assert layer.crs().authid() == 'EPSG:5179'
        assert layer.extent().width() > 0 and layer.extent().height() > 0
    print('Project verified: four valid local layers; CRS EPSG:5179; counts match')
    return project


def build(shadow_path):
    output = ROOT / 'docs/qgis'
    output.mkdir(parents=True, exist_ok=True)
    gpkg = output / 'CoolingPath_showcase.gpkg'
    project_file = output / 'CoolingPath_QGIS.qgz'
    if gpkg.exists() or project_file.exists():
        raise FileExistsError('Move existing showcase/project outputs before rebuilding')
    create_showcase(shadow_path, gpkg)
    project = QgsProject.instance()
    project.setFileName(str(project_file))
    project.setCrs(QgsCoordinateReferenceSystem('EPSG:5179'))
    project.setFilePathStorage(Qgis.FilePathType.Relative)
    project.setTitle('CoolingPath | Offline spatial analysis showcase')
    buildings = load_layer(ROOT / 'data/processed/processed_buildings.shp', 'Buildings')
    buffers = load_layer(ROOT / 'data/processed/processed_roads.shp', 'Road buffers | 2 m')
    shadows = load_layer(gpkg, 'Shadows | 14:00 KST', 'shadows_20250708_1400')
    roads = load_layer(gpkg, 'Walking links | shade at 14:00', 'roads_shade_20250708_1400')
    buildings.renderer().setSymbol(QgsFillSymbol.createSimple({
        'color': '#657181', 'outline_color': '#465362', 'outline_width': '0.12'}))
    buffers.renderer().setSymbol(QgsFillSymbol.createSimple({
        'color': '#f5ead6', 'outline_style': 'no'}))
    shadows.renderer().setSymbol(QgsFillSymbol.createSimple({
        'color': '107,95,156,95', 'outline_style': 'no'}))
    ranges = []
    for lower, upper, color in [(0, .2, '#d85e43'), (.2, .4, '#eaa65f'),
                                (.4, .6, '#dfce7b'), (.6, .8, '#79b6a1'),
                                (.8, 1, '#247d79')]:
        symbol = QgsLineSymbol.createSimple({'line_color': color, 'line_width': '0.65'})
        ranges.append(QgsRendererRange(lower, upper, symbol, f'{lower:.0%} – {upper:.0%}'))
    roads.setRenderer(QgsGraduatedSymbolRenderer('shadow_ratio', ranges))
    # Adding in reverse draw order puts walking links on top.
    for layer in [buffers, shadows, buildings, roads]:
        project.addMapLayer(layer)
    layers = [roads, buildings, shadows, buffers]
    extent = QgsRectangle(buildings.extent())
    extent.combineExtentWith(roads.extent())
    extent.scale(1.04)
    from qgis.core import QgsReferencedRectangle
    project.viewSettings().setDefaultViewExtent(QgsReferencedRectangle(extent, project.crs()))

    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName('Offline portfolio overview')
    layout.pageCollection().pages()[0].setPageSize(QgsLayoutSize(297, 210))
    map_item = QgsLayoutItemMap(layout)
    layout.addLayoutItem(map_item)
    map_item.attemptMove(QgsLayoutPoint(8, 24))
    map_item.attemptResize(QgsLayoutSize(207, 175))
    map_item.setLayers(layers)
    map_item.setKeepLayerSet(True)
    map_item.zoomToExtent(extent)
    title = QgsLayoutItemLabel(layout)
    title.setText('COOLINGPATH  /  SHADE & WALKING NETWORK')
    title.setFont(QFont('DejaVu Sans', 16))
    layout.addLayoutItem(title)
    title.attemptMove(QgsLayoutPoint(8, 4))
    title.attemptResize(QgsLayoutSize(280, 12))
    subtitle = QgsLayoutItemLabel(layout)
    subtitle.setText('Gangnam, Seoul  |  08 July 2025 · 14:00 KST  |  EPSG:5179')
    subtitle.setFont(QFont('DejaVu Sans', 9))
    layout.addLayoutItem(subtitle)
    subtitle.attemptMove(QgsLayoutPoint(8, 16))
    subtitle.attemptResize(QgsLayoutSize(280, 7))
    legend = QgsLayoutItemLegend(layout)
    legend.setTitle('LAYERS & SHADE')
    legend.setLinkedMap(map_item)
    legend.setAutoUpdateModel(False)
    legend.model().rootGroup().clear()
    for layer in layers:
        legend.model().rootGroup().addLayer(layer)
    layout.addLayoutItem(legend)
    legend.attemptMove(QgsLayoutPoint(219, 28))
    legend.attemptResize(QgsLayoutSize(70, 100))
    note = QgsLayoutItemLabel(layout)
    note.setText('Offline QGIS render\n\n1,392 buildings / 971 road links\nDiscrete shadow ghosting (7 steps)\n\nRoad colors: historical CSV ratios.\nCross-building overlaps were summed\nin that historical calculation.\n\nThis is a simulation, not field validation.\nNo basemap or remote services.')
    note.setFont(QFont('DejaVu Sans', 8))
    layout.addLayoutItem(note)
    note.attemptMove(QgsLayoutPoint(219, 112))
    note.attemptResize(QgsLayoutSize(73, 80))
    project.layoutManager().addLayout(layout)
    if not project.write(str(project_file)):
        raise RuntimeError('Cannot write project')
    preview = output / 'screenshots/qgis-overview.png'
    preview.parent.mkdir(exist_ok=True)
    settings = QgsLayoutExporter.ImageExportSettings()
    settings.dpi = 150
    settings.exportMetadata = False
    if QgsLayoutExporter(layout).exportToImage(str(preview), settings) != QgsLayoutExporter.Success:
        raise RuntimeError('Cannot render preview')
    sanitize_project_metadata(project_file)
    check_project(project_file)
    print('Created portable project, minimal showcase GeoPackage and QGIS-rendered preview')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--shadows', type=Path)
    group.add_argument('--check', type=Path)
    args = parser.parse_args()
    app = QgsApplication([], False)
    app.initQgis()
    if args.check:
        check_project(args.check)
    else:
        build(args.shadows)
    # QGIS objects are released during interpreter shutdown, after rendering completes.


if __name__ == '__main__':
    main()
