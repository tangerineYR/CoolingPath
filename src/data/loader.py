import streamlit as st
import geopandas as gpd
import pandas as pd
import os
from scipy.spatial import KDTree

@st.cache_data
def load_roads():
    gdf = gpd.read_file("data/non_buffered_roads.shp")
    if gdf.crs is None: gdf = gdf.set_crs(epsg=5179)
    return gdf.to_crs(epsg=5179)

@st.cache_data
def load_shadow_data():
    return pd.read_csv("data/hourly_link_stat_20250708.csv")

@st.cache_data
def load_shade_shelters():
    path = "data/gangnamgu_shade_shelters.csv"
    if os.path.exists(path):
        return pd.read_csv(path, encoding='cp949')
    return pd.DataFrame()

def build_node_index(roads_gdf):
    node_coords = {}
    for _, row in roads_gdf.iterrows():
        geom = row.geometry
        coords = list(geom.coords)
        node_coords[row["u"]] = coords[0]
        node_coords[row["v"]] = coords[-1]
    
    node_ids = list(node_coords.keys())
    node_xy = list(node_coords.values())
    return KDTree(node_xy), node_ids, node_xy
