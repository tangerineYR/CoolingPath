"""CoolingPath data implementation."""

import streamlit as st
import geopandas as gpd
import os
import pandas as pd
from coolingpath.config import DATA_DIR


@st.cache_data
def load_roads():
    shp_path = str(DATA_DIR / "non_buffered_roads.shp")
    if not os.path.exists(shp_path):
        st.error(f"도로 데이터 파일을 찾을 수 없습니다: {shp_path}")
        st.stop()
    gdf = gpd.read_file(shp_path)
    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=5179)
    elif gdf.crs.to_epsg() != 5179:
        gdf = gdf.to_crs(epsg=5179)
    return gdf


@st.cache_data
def load_shadow_data():
    csv_path = str(DATA_DIR / "hourly_link_stat_20250708.csv")
    if not os.path.exists(csv_path):
        st.error(f"그림자 데이터 파일을 찾을 수 없습니다: {csv_path}")
        st.stop()
    df = pd.read_csv(csv_path)
    required_cols = {"link_id", "time_slot", "shadow_ratio"}
    if not required_cols.issubset(df.columns):
        st.error(f"그림자 데이터 컬럼이 올바르지 않습니다: {df.columns.tolist()}")
        st.stop()
    return df


@st.cache_data
def load_shade_shelters():
    path = str(DATA_DIR / "gangnamgu_shade_shelters.csv")
    try:
        if os.path.exists(path):
            try:
                return pd.read_csv(path, encoding="cp949")
            except:
                try:
                    return pd.read_csv(path, encoding="euc-kr")
                except:
                    return pd.read_csv(path, encoding="utf-8")
    except Exception as e:
        st.warning(f"그늘막 데이터 로드 중 오류 발생: {e}")
        return pd.DataFrame()

    return pd.DataFrame()
