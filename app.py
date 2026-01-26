
import streamlit as st
import folium
from streamlit_folium import st_folium
import time
import networkx as nx
import geopandas as gpd
import os
import pandas as pd
from scipy.spatial import KDTree
from shapely.geometry import Point
import requests
import branca.colormap as cm
import copy
from datetime import datetime
import altair as alt
import itertools
import base64


# ======================================
# 페이지 설정
# ======================================
st.set_page_config(
    page_title="태·피·소 - 까망이의 태양 피하기 소동",
    layout="wide",  # <--- [중요] 여기에 추가해야 화면이 넓어집니다!
    page_icon="images/logo.png" if os.path.exists("images/logo.png") else "🐈‍⬛"
)

# ======================================
# 기본 설정
# ======================================
# [이미지 처리 헬퍼 함수] 이미지를 HTML에서 쓸 수 있게 텍스트로 변환
def get_img_as_base64(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()
# [수정] 메인 타이틀 영역 (이미지 로고 + 텍스트)

# 로고 이미지 경로 설정 (로고가 없으면 고양이 행복한 표정 사용)
if os.path.exists("images/logo.png"):
    title_img_path = "images/logo.png"
elif os.path.exists("images/cat_happy.png"):
    title_img_path = "images/cat_happy.png"
else:
    title_img_path = None


# HTML 타이틀 생성
if title_img_path:
    # 이미지를 Base64로 변환
    logo_b64 = get_img_as_base64(title_img_path)

    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 10px;">
        <img src="data:image/png;base64,{logo_b64}" style="width: 50px; height: 50px; border-radius: 10px;">
        <h1 style="margin: 0; padding: 0; color: #333; font-size: 38px;">태·피·소 - 까망이의 태양 피하기 소동</h1>
    </div>
    """, unsafe_allow_html=True)
else:
    # 이미지가 없을 경우 텍스트만
    st.title("🐈‍ 태·피·소 - 까망이의 태양 피하기 소동")

st.caption("햇빛은 피하고, 시원함만 밟고 가자! AI 고양이 까망이의 산책 네비게이션")


# ======================================
# [NEW] CSS 스타일링 (앱 디자인 적용)
# ======================================
st.markdown("""
<style>
    /* 1. 전체 배경 및 폰트 (크림 화이트) */
    .stApp {
        background-color: #FDFBF7;
        font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;
    }

    /* [NEW] 상단 헤더(햄버거 메뉴 라인) 배경색 통일 */
    [data-testid="stHeader"] {
        background-color: #FDFBF7;
    }

    /* 2. 메인 컨테이너 여백 조정 (제목 잘림 방지) */
    .block-container {
        padding-top: 6rem; /* 기존 2rem에서 늘림 */
        padding-bottom: 5rem;
    }

    /* 3. 카드(Card) 스타일 */
    .css-card {
        background-color: #FFFFFF;
        border-radius: 20px;
        padding: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        border: 1px solid #F0F0F0;
    }

    /* 4. 라디오 버튼 아래 불필요한 여백 제거 */
    div[role="radiogroup"] {
        margin-bottom: -10px;
    }

    /* 5. 버튼 스타일 */
    .stButton>button {
        background-color: #7E57C2;
        color: white;
        border-radius: 15px;
        border: none;
        height: 50px;
        font-weight: bold;
        width: 100%;
        transition: all 0.3s;
        box-shadow: 0 4px 6px rgba(126, 87, 194, 0.3);
    }
    .stButton>button:hover {
        background-color: #673AB7;
        transform: translateY(-2px);
    }

    /* 6. 사이드바 스타일 */
    [data-testid="stSidebar"] {
        background-color: #F8F9FA;
        border-right: 1px solid #E9ECEF;
    }
</style>
""", unsafe_allow_html=True)


# ======================================
# Session State 초기화
# ======================================
if "route_ready" not in st.session_state:
    st.session_state.route_ready = False

if "route_result" not in st.session_state:
    st.session_state.route_result = None

if "selected_persona" not in st.session_state:
    st.session_state.selected_persona = "custom"

# ======================================
# Kakao Map API
# ======================================
KAKAO_API_KEY = "6377f890b2b93c7882eaed31d9107544"

def search_place_kakao(query):
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    params = {"query": query}

    res = requests.get(url, headers=headers, params=params).json()

    if not res.get("documents"):
        return None

    doc = res["documents"][0]
    return float(doc["y"]), float(doc["x"]), doc["place_name"]


# ======================================
# 도로 데이터 로드
# ======================================
@st.cache_data
def load_roads():
    shp_path = "data/non_buffered_roads.shp"   # ← PoC 구역용
    # shp_path = "data/processed_roads.shp"    # ← 버퍼 적용 버전

    if not os.path.exists(shp_path):
        st.error(f"도로 데이터 파일을 찾을 수 없습니다: {shp_path}")
        st.stop()

    gdf = gpd.read_file(shp_path)

    # 좌표계 통일 (중요)
    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=5179)
    elif gdf.crs.to_epsg() != 5179:
        gdf = gdf.to_crs(epsg=5179)

    return gdf


# =========================
# 그림자 데이터 로드
# =========================
@st.cache_data
def load_shadow_data():
    csv_path = "data/hourly_link_stat_20250708.csv"

    if not os.path.exists(csv_path):
        st.error(f"그림자 데이터 파일을 찾을 수 없습니다: {csv_path}")
        st.stop()

    df = pd.read_csv(csv_path)

    # 컬럼 체크 (PoC 안정성)
    required_cols = {"link_id", "time_slot", "shadow_ratio"}
    if not required_cols.issubset(df.columns):
        st.error(f"그림자 데이터 컬럼이 올바르지 않습니다: {df.columns.tolist()}")
        st.stop()

    return df


# =========================
# 그늘막 데이터 로드
# =========================
@st.cache_data
def load_shade_shelters():
    # 파일 경로 확인
    path = "data/gangnamgu_shade_shelters.csv"

    try:
        if os.path.exists(path):
                try: return pd.read_csv(path, encoding='cp949')
                except: 
                    try: return pd.read_csv(path, encoding='euc-kr')
                    except: return pd.read_csv(path, encoding='utf-8')

    except Exception as e:
        st.warning(f"그늘막 데이터 로드 중 오류 발생: {e}")
        return pd.DataFrame()

# ====================================
# KDTree용 노드 좌표 만들기 (한 번만)
# ====================================
def build_node_index(roads_gdf):
    node_coords = {}

    for _, row in roads_gdf.iterrows():
        geom = row.geometry
        if geom.geom_type != "LineString":
            continue

        coords = list(geom.coords)
        node_coords[row["u"]] = coords[0]     # 시작점
        node_coords[row["v"]] = coords[-1]    # 끝점

    node_ids = list(node_coords.keys())
    node_xy  = list(node_coords.values())

    tree = KDTree(node_xy)
    return tree, node_ids, node_xy


# ======================================
# 사용자 좌표 -> 가장 가까운 노드 찾기
# ======================================
def get_nearest_node(lat, lon, tree, node_ids, node_xy):
    # Kakao 좌표 → TM좌표
    pt = gpd.GeoDataFrame(
        geometry=[Point(lon, lat)],
        crs="EPSG:4326"
    ).to_crs("EPSG:5179")

    x, y = pt.geometry.iloc[0].x, pt.geometry.iloc[0].y

    dist, idx = tree.query((x, y))
    return node_ids[idx]


# ===============================================
# 시간대별 그림자 반영 함수
# ===============================================
def attach_shadow_by_hour(G, shadow_df):
    for hour in range(8, 20):
        df_h = shadow_df[shadow_df["time_slot"] == hour]
        ratio_map = df_h.set_index("link_id")["shadow_ratio"].to_dict()

        for _, _, d in G.edges(data=True):
            if "shadow_by_hour" not in d:
                d["shadow_by_hour"] = {}

            if d.get("indoor") or d.get("tunnel"):
                d["shadow_by_hour"][hour] = 1.0
            else:
                d["shadow_by_hour"][hour] = ratio_map.get(d["link_id"], 0.0)


# ===============================================
# 시간대별 그림자 반영된 Base Graph 생성 (1회만)
# ===============================================
@st.cache_resource
def build_base_graph_with_shadow(_roads_gdf, _shadow_df):
    G = nx.Graph()

    for _, row in _roads_gdf.iterrows():
        G.add_edge(
            row["u"], row["v"],
            link_id=row["link_id"],
            length=row["length"],
            geometry=row.geometry,
            footbridge=row.get("footbridge", 0),
            tunnel=row.get("tunnel", 0),
            indoor=row.get("indoor", 0),
        )

    attach_shadow_by_hour(G, _shadow_df)

    return G


# ======================================
# 선택 시간대의 shadow_ratio 적용
# ======================================
def apply_shadow_ratio(G, time_slot, rain_mm):
    for _, _, d in G.edges(data=True):
        if rain_mm > 0:
            d["shadow_ratio"] = 0.0
        else:
            d["shadow_ratio"] = d["shadow_by_hour"][time_slot]


# ========================================
# 폭염 데모용 forecast 빌드 함수
# ========================================
def build_hot_demo_weather():
    # 2025.07.08 강남구 폭염 (고정 시나리오)

    forecast = [
        {"time": "08:00", "hour": 8, "temp": 30.0, "rain": 0.0, "humidity": 70},
        {"time": "09:00", "hour": 9, "temp": 32.6, "rain": 0.0, "humidity": 68},
        {"time": "10:00", "hour": 10, "temp": 34.1, "rain": 0.0, "humidity": 65},
        {"time": "11:00", "hour": 11, "temp": 35.0, "rain": 0.0, "humidity": 60},
        {"time": "12:00", "hour": 12, "temp": 36.4, "rain": 0.0, "humidity": 55},
        {"time": "13:00", "hour": 13, "temp": 36.5, "rain": 0.0, "humidity": 50},
        {"time": "14:00", "hour": 14, "temp": 36.7, "rain": 0.0, "humidity": 48},
        {"time": "15:00", "hour": 15, "temp": 38.2, "rain": 0.0, "humidity": 50},
        {"time": "16:00", "hour": 16, "temp": 37.5, "rain": 0.0, "humidity": 52},
        {"time": "17:00", "hour": 17, "temp": 38.1, "rain": 0.0, "humidity": 55},
        {"time": "18:00", "hour": 18, "temp": 36.4, "rain": 0.0, "humidity": 58},
        {"time": "19:00", "hour": 19, "temp": 32.7, "rain": 0.0, "humidity": 60},
        {"time": "20:00", "hour": 20, "temp": 29.0, "rain": 0.0, "humidity": 62},
        {"time": "21:00", "hour": 21, "temp": 29.0, "rain": 0.0, "humidity": 65},
        {"time": "22:00", "hour": 22, "temp": 29.2, "rain": 0.0, "humidity": 68},
        {"time": "23:00", "hour": 23, "temp": 29.4, "rain": 0.0, "humidity": 70},
    ]

    return {
      "raw_forecast": forecast,
      "mode": "hot_demo"
    }


# ======================================
# 강수 데모 데이터 빌드 함수
# ======================================
def build_rain_demo_weather():
    forecast = [
        {"time": "08:00", "hour": 8, "temp": 27.8, "rain": 0.0, "humidity": 75},
        {"time": "09:00", "hour": 9, "temp": 29.5, "rain": 0.0, "humidity": 78},
        {"time": "10:00", "hour": 10, "temp": 31.2, "rain": 0.0, "humidity": 80},
        {"time": "11:00", "hour": 11, "temp": 33.0, "rain": 1.2, "humidity": 85},
        {"time": "12:00", "hour": 12, "temp": 34.2, "rain": 2.5, "humidity": 88},
        {"time": "13:00", "hour": 13, "temp": 35.0, "rain": 4.0, "humidity": 90},
        {"time": "14:00", "hour": 14, "temp": 35.6, "rain": 6.0, "humidity": 92},
        {"time": "15:00", "hour": 15, "temp": 35.2, "rain": 5.5, "humidity": 93},
        {"time": "16:00", "hour": 16, "temp": 34.6, "rain": 4.0, "humidity": 90},
        {"time": "17:00", "hour": 17, "temp": 33.8, "rain": 3.0, "humidity": 88},
        {"time": "18:00", "hour": 18, "temp": 32.5, "rain": 2.0, "humidity": 85},
        {"time": "19:00", "hour": 19, "temp": 31.2, "rain": 1.0, "humidity": 82},
        {"time": "20:00", "hour": 20, "temp": 30.0, "rain": 0.5, "humidity": 80},
        {"time": "21:00", "hour": 21, "temp": 29.5, "rain": 0.0, "humidity": 78},
        {"time": "22:00", "hour": 22, "temp": 29.0, "rain": 0.0, "humidity": 76},
        {"time": "23:00", "hour": 23, "temp": 28.6, "rain": 0.0, "humidity": 75},
    ]

    return {
      "raw_forecast": forecast,
      "mode": "rain_demo"
    }


# ======================================
# 기온 API 함수
# ======================================
def get_realtime_weather_forecast(lat, lon):
    # 실시간 기온 + 향후 6시간 기온/강수 반환
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": True,
        "hourly": "temperature_2m,precipitation,relative_humidity_2m",
        "timezone": "Asia/Seoul",
    }

    try:
        res = requests.get(url, params=params, timeout=5).json()

        times = res["hourly"]["time"]
        temps = res["hourly"]["temperature_2m"]
        rains = res["hourly"]["precipitation"]
        humidities = res["hourly"]["relative_humidity_2m"]

        # --- 8~19시 forecast ---
        forecast = []
        today = datetime.now().date()

        for t, temp, rain, hum in zip(times, temps, rains, humidities):
            dt = datetime.fromisoformat(t)
            hour = dt.hour

            # 오늘 + 08~19시만
            if dt.date() == today and 8 <= hour <= 19:
                forecast.append({
                    "time": f"{hour:02d}:00",  # HH:MM
                    "hour": hour,
                    "temp": float(temp),
                    "rain": float(rain),  #mm
                    "humidity": float(hum), #%
                })

        return {
          "raw_forecast": forecast,
          "mode": "realtime"
        }

    except Exception as e:
        st.warning("기온 API 호출 실패")
        return {}

# ======================================
# time_slot 기준 env 선택 함수
# ======================================
def get_env_at_time(env, time_slot):
    for f in env["raw_forecast"]:
        if f["hour"] == time_slot:
            return f

    # fallback
    return env["raw_forecast"][0]


# ======================================
# 체감온도 포함 그래프 데이터 빌드 함수
# ======================================
def build_forecast_for_graph(env, avg_shadow, time_slot):
    graph_data = []

    for f in env["raw_forecast"]:
        base = f["temp"]
        feels = base - avg_shadow * 5.0

        graph_data.append({
            "time": f["time"],
            "hour": f["hour"],
            "temp": base,
            "feels_like": round(feels, 1),
            "rain": f["rain"],
            "humidity": f["humidity"],
        })

    return graph_data


# ======================================
# 폭염 판단 함수
# ======================================
def is_heatwave(temp, threshold=33.0):
    return temp >= threshold


# ======================================
# 강수 페널티(경로) 함수
# ======================================
def calc_rain_penalty(rain_mm):
    if rain_mm >= 3:
        return 0.6
    elif rain_mm >= 1:
        return 0.3
    else:
        return 0.0


# ======================================
# 시설 페널티
# ======================================
def calc_facility_penalty(d, mode):
    tunnel = bool(d.get("tunnel", 0))
    footbridge = bool(d.get("footbridge", 0))
    crosswalk = bool(d.get("crosswalk", 0))

    penalty = 0.0

    if tunnel:
        penalty += 0.4

    if crosswalk:
        penalty += 0.2

    if footbridge:
        penalty += 0.3 if mode != "cooling" else 1.0

    return penalty


# ======================================
# 실내 유형 구분 함수
# ======================================
def classify_indoor_type(d):
    if not d.get("indoor", 0):
        return None

    length = d.get("length", 0)

    if length >= 60:
        return "station_or_underground"
    else:
        return "semi_indoor"  # 필로티, 아케이드 추정


# ======================================
# 실내 페널티
# ======================================
def calc_indoor_penalty(d):
    indoor_type = classify_indoor_type(d)

    time_penalty = 0.0
    fatigue_penalty = 0.0

    if indoor_type == "station_or_underground":
        time_penalty += 40
        fatigue_penalty += 0.6
    elif indoor_type == "semi_indoor":
        time_penalty += 8
        fatigue_penalty += 0.1

    return time_penalty, fatigue_penalty

# ======================================
# 비용 함수 (쿨링/최단/큰길)
# ======================================
def apply_costs(G, rain_mm=0.0):
    rain_penalty = calc_rain_penalty(rain_mm)

    for _, _, d in G.edges(data=True):
        # ---------- 기본 값 ----------
        length = float(d.get("length", 1.0))
        shadow = float(d.get("shadow_ratio", 0.0))

        tunnel = bool(d.get("tunnel", 0))
        footbridge = bool(d.get("footbridge", 0))
        indoor = bool(d.get("indoor", 0))

        # 1️⃣ 최단 경로
        total_penalty = rain_penalty + calc_facility_penalty(d, "shortest")
        d["cost_shortest"] = length * (1 + total_penalty)

        # 2️⃣ 큰길 우선
        is_main = (length >= 100 and not tunnel and not footbridge and not indoor)
        main_factor = 1.0 if is_main else 1.5
        total_penalty = rain_penalty + calc_facility_penalty(d, "main")
        d["cost_main"] = length * main_factor * (1 + total_penalty)

        # ------------------
        # 3️⃣ 쿨링 경로
        # ------------------
        heat_penalty = (1 - shadow) * 2.0
        _, fatigue_penalty = calc_indoor_penalty(d)
        cooling_penalty = heat_penalty + fatigue_penalty

        total_penalty = rain_penalty + calc_facility_penalty(d, "cooling")
        d["cost_cooling"] = length * (1 + cooling_penalty + total_penalty)


# ======================================
# 퍼스널 비용 함수
# ======================================
def apply_personal_costs(G, rain_mm, pref):
    cw = pref["cooling_weight"]

    for _, _, d in G.edges(data=True):
        length = float(d.get("length", 1.0))
        shadow = float(d.get("shadow_ratio", 0.0))

        tunnel = bool(d.get("tunnel", 0))
        footbridge = bool(d.get("footbridge", 0))
        indoor = bool(d.get("indoor", 0))

        # --- 기본 패널티 ---
        rain_penalty = calc_rain_penalty(rain_mm)
        facility_penalty = 0.0

        if pref["avoid_tunnel"] and tunnel:
            facility_penalty += 0.6
        if pref["avoid_footbridge"] and footbridge:
            facility_penalty += 0.4
        if pref["avoid_indoor"] and indoor:
            facility_penalty += 0.5

        # --- 시원함 패널티 ---
        heat_penalty = (1 - shadow) * 2.0 * cw

        # --- 시간 패널티 ---
        time_penalty = (1 - cw)

        d["cost_personal"] = length * (
            1 + heat_penalty + time_penalty + rain_penalty + facility_penalty
        )


# ======================================
# 우회율 범위 내 최적 경로 탐색 함수
# ======================================


def find_constrained_best_path(
    G,
    u_node,
    v_node,
    base_path,
    cost_key,
    detour_limit=0.14,
    max_candidates=30
):
    # base_path 대비 우회율 제한 내에서 cost_key 기준 최적 경로 선택

    # 1. 기준 길이
    base_length = nx.path_weight(G, base_path, "length")
    max_length = base_length * (1 + detour_limit)

    # 2. 후보 경로 생성 (길이 기준)
    path_gen = nx.shortest_simple_paths(G, u_node, v_node, weight=cost_key)

    best_path = None
    best_cost = float("inf")

    for path in itertools.islice(path_gen, max_candidates):
        path_length = nx.path_weight(G, path, "length")

        # 3. 우회율 초과 → 스킵
        if path_length > max_length:
            continue

        # 4. 목적 cost 계산
        cost = nx.path_weight(G, path, cost_key)

        if cost < best_cost:
            best_cost = cost
            best_path = path

    # 5. fallback (안전장치)
    return best_path if best_path else base_path


# ======================================
# KPI 보조 함수 (길이, 그늘 계산)
# ======================================
def calc_path_length(G, path):
    return nx.path_weight(G, path, weight="length")

#그늘 평균 계산 함수
def calc_avg_shadow(G, path):
    if not path or len(path) < 2:
        return 0.0

    # 길이 가중 평균 shadow_ratio
    total_len = 0.0
    shadow_sum = 0.0

    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        d = G[u][v]

        length = float(d.get("length", 0.0))
        shadow = float(d.get("shadow_ratio", 0.0))

        total_len += length
        shadow_sum += length * shadow

    return shadow_sum / total_len if total_len > 0 else 0.0


# 링크별 시간 계산 함수
def calc_edge_time(d, base_speed=1.2, rain_mm=0.0):
    # d: edge data, return: seconds

    length = float(d.get("length", 0.0))
    time_sec = length / base_speed

    # 1️⃣ 실내 시간 페널티
    indoor_time, _ = calc_indoor_penalty(d)
    time_sec += indoor_time

    # 2️⃣ 횡단보도 신호대기
    if d.get("crosswalk", 0):
        time_sec += 30  # 평균 신호대기 30초 (PoC 기준)

    # 3️⃣ 육교 계단
    if d.get("footbridge", 0):
        time_sec += 20

    # 4️⃣ 강수 시 보행 속도 감소
    if rain_mm >= 3:
        time_sec *= 1.15
    elif rain_mm >= 1:
        time_sec *= 1.08

    return time_sec


# 경로 전체 소요시간 계산 함수
def calc_path_time(G, path, rain_mm=0.0):
    total_time = 0.0
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        d = G[u][v]
        total_time += calc_edge_time(d, rain_mm=rain_mm)
    return total_time


# 습도에 따른 불쾌도 산정 함수
def calc_humidity_discomfort(humidity):
    if humidity >= 85:
        return 3, "매우 높음"
    elif humidity >= 75:
        return 2, "높음"
    elif humidity >= 65:
        return 1, "보통"
    else:
        return 0, "쾌적"


# 경로 내 장애물 집계 함수
def count_obstacles(G, path):
    counts = {
        "crosswalk": 0,
        "footbridge": 0,
        "tunnel": 0,
        "indoor": 0,
    }

    for i in range(len(path) - 1):
        d = G[path[i]][path[i + 1]]

        if d.get("crosswalk"):
            counts["crosswalk"] += 1
        if d.get("footbridge"):
            counts["footbridge"] += 1
        if d.get("tunnel"):
            counts["tunnel"] += 1
        if d.get("indoor"):
            counts["indoor"] += 1

    return counts

# 장애물 아이콘+ 배지 렌더링 함수
def render_obstacle_badges(obs):
    def badge(icon, label, value, warn=False):
        bg = "#FFF3CD" if warn else "#F1F3F5"
        border = "#FFC107" if warn else "#DEE2E6"
        return f"""
        <div style="
            display:inline-flex;
            align-items:center;
            gap:8px;
            padding:6px 10px;
            margin:4px 6px 4px 0;
            background:{bg};
            border:1px solid {border};
            border-radius:16px;
            font-size:13px;
            font-weight:500;
        ">
            <span style="font-size:16px">{icon}</span>
            <span>{label}</span>
            <span style="font-weight:700">{value}</span>
        </div>
        """

    html = ""
    html += badge("🚦", "횡단보도", f"{obs['crosswalk']}회", obs["crosswalk"] > 0)
    html += badge("🌉", "육교", f"{obs['footbridge']}회", obs["footbridge"] > 0)
    html += badge("🕳️", "터널", "있음" if obs["tunnel"] > 0 else "없음", obs["tunnel"] > 0)
    html += badge("🏬", "실내", "있음" if obs["indoor"] > 0 else "없음", obs["indoor"] > 0)

    st.markdown("#### 🚧 경로 환경 요소")
    st.markdown(html, unsafe_allow_html=True)



# ======================================
# KPI 계산 함수 (핵심)
# ======================================
def calculate_kpis(
    G,
    path_shortest,
    path_target,        # 쿨링 or 큰길
    base_temp,
    rain_mm,
    humidity
):
    # -----------------------------
    # 1. 거리
    # -----------------------------
    len_short = calc_path_length(G, path_shortest)
    len_target = calc_path_length(G, path_target)

    detour_ratio = (len_target - len_short) / len_short

    # -----------------------------
    # 2. 소요시간
    # -----------------------------
    time_short = calc_path_time(G, path_shortest, rain_mm)
    time_target = calc_path_time(G, path_target, rain_mm)

    time_ratio = (time_target - time_short) / time_short

    # -----------------------------
    # 3. 그늘 확보율
    # -----------------------------
    shadow_short = calc_avg_shadow(G, path_shortest)
    shadow_target = calc_avg_shadow(G, path_target)

    shadow_gain = shadow_target - shadow_short

    # -----------------------------
    # 4. 체감온도
    # - shadow_ratio 1.0 → -5℃
    # -----------------------------
    temp_short = base_temp - shadow_short * 5.0
    temp_target = base_temp - shadow_target * 5.0

    temp_diff = temp_target - temp_short  # 음수면 더 시원

    # -----------------------------
    # 5. 습도
    # -----------------------------
    humidity_score, humidity_label = calc_humidity_discomfort(humidity)

    # -----------------------------
    # 6. 장애물
    # -----------------------------
    obstacles = count_obstacles(G, path_target)


    # -----------------------------
    # 7. 결과
    # -----------------------------

    return {
        "length": {
            "shortest": len_short,
            "target": len_target,
            "detour_ratio": detour_ratio,
        },
        "time": {
            "shortest": time_short,
            "target": time_target,
            "time_ratio": time_ratio,
        },
        "shadow": {
            "shortest": shadow_short,
            "target": shadow_target,
            "gain": shadow_gain,
        },
        "temperature": {
            "shortest": temp_short,
            "target": temp_target,
            "diff": temp_diff,
        },
        "humidity": {
            "value": humidity,
            "score": humidity_score,
            "label": humidity_label,
        },
        "obstacles": obstacles,
    }


# ======================================
# KPI 설명 함수
# ======================================
def build_kpi_story(kpi):
    story = {}

    # =========================
    # 1. 소요시간
    # =========================
    time_diff = kpi["time"]["time_ratio"]

    if time_diff <= -0.05:
        story["time"] = {
            "tone": "positive",
            "text": "⏱️ 생각보다 빨리 도착한다냥! 신난다 💨"
        }
    elif time_diff <= 0.05:
        story["time"] = {
            "tone": "neutral",
            "text": "⏱️ 시간은 비슷해. 무리 없이 걸을 수 있어."
        }
    else:
        story["time"] = {
            "tone": "warning",
            "text": "⏱️ 조금 돌아가지만, 그만큼 덜 덥고 쾌적할 거야."
        }

    # =========================
    # 2. 체감온도
    # =========================
    temp_diff = kpi["temperature"]["diff"]

    if temp_diff <= -1.5:
        story["temperature"] = {
            "tone": "positive",
            "text": "🌡️ 완전 시원해! 에어컨 켠 줄 알았다냥 ❄️"
        }
    elif temp_diff <= -0.5:
        story["temperature"] = {
            "tone": "positive",
            "text": "🌡️ 그늘 적당해! 한여름엔 이 차이가 꽤 크게 느껴질걸?"
        }
    elif temp_diff <= 0.5:
        story["temperature"] = {
            "tone": "neutral",
            "text": "🌡️ 온도는 비슷해. 그래도 최단거리보단 낫겠지?"
        }
    else:
        story["temperature"] = {
            "tone": "warning",
            "text": "🌡️ 으아, 여긴 좀 더울 수도 있어. 조심해!"
        }

    # =========================
    # 3. 거리
    # =========================
    detour = kpi["length"]["detour_ratio"]

    if detour <= 0.1:
        story["detour"] = {
            "tone": "positive",
            "text": "📏 거리도 가깝고 시원하고! 완전 럭키잖아? 🍀"
        }
    elif detour <= 0.2:
        story["detour"] = {
            "tone": "neutral",
            "text": "📏 조금 더 걷긴 하는데, 산책한다고 생각하자냥."
        }
    else:
        story["detour"] = {
            "tone": "warning",
            "text": "📏 꽤 많이 돌아가야 해. 그래도 시원함이 중요하다면!"
        }

    # =========================
    # 4. 그늘 확보
    # =========================
    shadow_gain = kpi["shadow"]["gain"]

    if shadow_gain >= 0.15:
        story["shadow"] = {
            "tone": "positive",
            "text": "🌳 그늘 천국이야! 내 발바닥 절대 지켜 🐾"
        }
    elif shadow_gain >= 0.05:
        story["shadow"] = {
            "tone": "positive",
            "text": "🌳 그늘이 꽤 있어. 햇빛 피하기 딱 좋아."
        }
    else:
        story["shadow"] = {
            "tone": "neutral",
            "text": "🌳 그늘 양은 비슷해. 모자나 양산 챙겼어?"
        }

    # =========================
    # 5. 습도
    # =========================
    humidity_label = kpi["humidity"]["label"]

    humidity_story = {
        "쾌적": "💧 털이 뽀송뽀송해지는 쾌적한 날씨야!",
        "보통": "💧 조금 눅눅하지만 참을 만해.",
        "높음": "💧 으, 끈적거려. 물 자주 마셔냥!",
        "매우 높음": "💧 공기가 물 먹은 솜 같아... 무리하지 마."
    }

    story["humidity"] = {
        "tone": "warning" if humidity_label in ["높음", "매우 높음"] else "neutral",
        "text": humidity_story[humidity_label]
    }

    return story


# ======================================
# KPI 지표별 카드 렌더링 함수
# ======================================
def render_kpi_card(
    col,
    title,
    value,
    delta_text,
    delta_positive=True,
    is_humidity=False,
    story_text=None,
    story_tone="neutral"
):
    delta_color = "#20C997" if delta_positive else "#FA5252"

    if is_humidity:
        delta_arrow = ""
    elif delta_positive:
        delta_arrow = "▲"
    else:
        delta_arrow = "▼"

    bg_map = {
        "positive": "#E6FCF5",
        "neutral": "#F8F9FA",
        "warning": "#FFF4E6",
    }
    border_map = {
        "positive": "#20C997",
        "neutral": "#ADB5BD",
        "warning": "#FAB005",
    }

    col.markdown(
    f"""
    <div style="padding:8px 4px;">
      <div style="font-size:20px; font-weight:600;">{title}</div>

      <div style="font-size:30px; font-weight:700; margin-top:2px;">
        {value}
      </div>

      <div style="
        font-size:15px;
        font-weight:600;
        color:{delta_color};
        margin-top:2px;
      ">
        {delta_arrow} {delta_text}
      </div>

      <div style="
        margin-top:8px;
        background:{bg_map[story_tone]};
        border-left:5px solid {border_map[story_tone]};
        padding:10px 12px;
        border-radius:8px;
        font-size:14px;
      ">
        {story_text}
      </div>
    </div>
    """,
    unsafe_allow_html=True
    )


# ======================================
# 경로 타입별 스토리 생성
# ======================================
def get_route_summary_story(key, kpi):
    if key == "cooling":
        return "❄️ 더위 사냥 성공! 제일 시원한 길이야."
    elif key == "shortest":
        return "⏱️ 더워도 빨리 가는 게 최고라면 이 길!"
    elif key == "main":
        return "🛣️ 넓은 길로 맘 편하게 가고 싶을 때 추천해."
    elif key == "personal":
        return "🎯 집사 취향 100% 반영한 맞춤 경로야."
    else:
        return ""



# ======================================
# 모든 경로 KPI 비교
# ======================================
def render_multi_route_summary(
    paths,
    G,
    env,
    time_slot,
    personal_pref=None
):
    st.markdown("### 🔍 경로별 요약 비교")
    st.caption("각 경로의 특성을 한눈에 비교해보세요.")

    env_at_time = get_env_at_time(env, time_slot)

    cols = st.columns(len([p for p in paths.values() if p is not None]))

    i = 0
    for key, path in paths.items():
        if path is None:
            continue

        kpi = calculate_kpis(
            G,
            path_shortest=paths["shortest"],
            path_target=path,
            base_temp=env_at_time["temp"],
            rain_mm=env_at_time["rain"],
            humidity=env_at_time["humidity"]
        )

        grade = calculate_route_grade(
            kpi,
            mode=key,
            pref=personal_pref if key == "personal" else None
        )

        story = get_route_summary_story(key, kpi)

        title = {
            "cooling": "❄️ 쿨링",
            "shortest": "⏱️ 최단",
            "main": "🛣️ 큰길",
            "personal": "🎯 나의 경로",
        }[key]

        cols[i].markdown(
            f"""
            <div style="
              padding:14px;
              border-radius:12px;
              background:#F8F9FA;
              border:1px solid #DEE2E6;
              text-align:center;
            ">
              <div style="font-size:18px;font-weight:700">{title}</div>
              <div style="margin-top:6px;font-size:28px;font-weight:800">
                {grade['grade']}
              </div>
              <div style="font-size:15px;color:#495057">
                {grade['score']}점
              </div>

              <!-- 🔹 한 줄 스토리 -->
              <div style="
                margin-top:6px;
                font-size:13px;
                color:#343A40;
                background:#FFFFFF;
                padding:6px 8px;
                border-radius:8px;
              ">
                {story}
              </div>

              <hr style="margin:8px 0">

              <div style="font-size:15px">📏 {kpi['length']['target']:.0f}m</div>
              <div style="font-size:15px">⏱ {kpi['time']['target']/60:.1f}분</div>
              <div style="font-size:15px">🌳 {kpi['shadow']['target']*100:.0f}%</div>
              <div style="font-size:15px">🌡 {kpi['temperature']['target']:.1f}℃</div>

            </div>
            """,
            unsafe_allow_html=True
        )

        i += 1

    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)


# ======================================
# 경로 점수화 로직
# ======================================
# ----- 우회율 -----
def score_detour(detour_ratio):
    if detour_ratio <= 0.10:
        return 100
    elif detour_ratio <= 0.14:
        return 80
    elif detour_ratio <= 0.20:
        return 60
    else:
        return 30

# ----- 소요 시간 -----
def score_time(time_ratio):
    if time_ratio <= 0.05:
        return 100
    elif time_ratio <= 0.10:
        return 80
    elif time_ratio <= 0.20:
        return 60
    else:
        return 30


# ----- 그늘 비율 -----
def score_shadow(shadow_gain):
    if shadow_gain >= 0.20:
        return 100
    elif shadow_gain >= 0.10:
        return 80
    elif shadow_gain >= 0.05:
        return 60
    else:
        return 30


# ----- 체감 온도 -----
def score_cooling(temp_diff):
    # temp_diff: target - shortest (음수면 시원)
    if temp_diff <= -2.0:
        return 100
    elif temp_diff <= -1.0:
        return 80
    elif temp_diff <= -0.5:
        return 60
    else:
        return 30


# ----- 가중 평균 (기본 모드 기준) -----
def calculate_route_grade(kpi, mode="cooling", pref=None):

    # mode: cooling | shortest | main | personal
    # pref: 퍼스널 모드일 때만 사용


    # --- 기본 점수 ---
    s_cool = score_cooling(kpi["temperature"]["diff"])
    s_shadow = score_shadow(kpi["shadow"]["gain"])
    s_detour = score_detour(kpi["length"]["detour_ratio"])
    s_time = score_time(kpi["time"]["time_ratio"])

    # --- 모드별 가중치 ---
    if mode == "cooling":
        w = dict(cool=0.35, shadow=0.30, detour=0.20, time=0.15)

    elif mode == "shortest":
        w = dict(cool=0.15, shadow=0.10, detour=0.35, time=0.40)

    elif mode == "main":
        w = dict(cool=0.20, shadow=0.15, detour=0.25, time=0.25)

    elif mode == "personal" and pref:
        cw = pref["cooling_weight"]
        w = dict(
            cool=0.15 + 0.4 * cw,
            shadow=0.15 + 0.3 * cw,
            detour=0.35 * (1 - cw),
            time=0.35 * (1 - cw),
        )

    total = (
        s_cool * w["cool"] +
        s_shadow * w["shadow"] +
        s_detour * w["detour"] +
        s_time * w["time"]
    )

    grade = (
        "A" if total >= 85 else
        "B" if total >= 70 else
        "C" if total >= 55 else
        "D"
    )

    return {"score": round(total, 1), "grade": grade}



# ======================================
# 경로 유형별 등급 이름 분리
# ======================================
def get_grade_label(view_mode):
    return {
        "❄️ 쿨링 경로": "❄️ 쿨링 경로 등급",
        "⏱️ 최단 경로": "⏱️ 이동 효율 등급",
        "🛣️ 큰길 우선": "🛣️ 안정 보행 등급",
        "🎯 나만의 경로": "🎯 나의 기준 등급",
    }.get(view_mode, "경로 종합 등급")


# ======================================
# 경로 등급 및 해석
# ======================================
def grade_story(grade):
    return {
        "A": "🏆 대박! 그늘이 꽉 찬 최고의 산책로야. 당장 출발해! 🐾",
        "B": "👍 꽤 괜찮은데? 시원함과 거리의 밸런스가 좋아.",
        "C": "🙂 쏘쏘~ 무난하지만 땀은 조금 날 수도 있어.",
        "D": "⚠️ 앗, 뜨거! 이 길은 햇빛이 너무 많아. 다시 생각해봐."
    }[grade]


# ======================================
# 모든 경로 지도 범례 렌더링
# ======================================
ROUTE_COLOR_MAP = {
    "cooling": {
        "label": "❄️ 쿨링 경로",
        "color": "#00FFFF",
        "desc": "그늘과 시원함을 우선한 경로"
    },
    "shortest": {
        "label": "⏱️ 최단 경로",
        "color": "#333333",
        "desc": "이동 거리를 최소화한 경로"
    },
    "main": {
        "label": "🛣️ 큰길 우선",
        "color": "#9E9E9E",
        "desc": "넓고 안정적인 보행로 중심"
    },
    "personal": {
        "label": "🎯 나만의 경로",
        "color": "#845EF7",
        "desc": "나의 선호도를 반영한 맞춤 경로"
    }
}


def render_route_legend(show_personal=False):
    items = []

    for key in ["cooling", "shortest", "main"]:
        item = ROUTE_COLOR_MAP[key]
        items.append(f"""
        <div style="display:flex;align-items:center;gap:8px;margin-right:16px;">
          <div style="
            width:18px;height:4px;
            background:{item['color']};
            border-radius:2px;
          "></div>
          <div style="font-size:13px;font-weight:600;">
            {item['label']}
          </div>
        </div>
        """)

    if show_personal:
        item = ROUTE_COLOR_MAP["personal"]
        items.append(f"""
        <div style="display:flex;align-items:center;gap:8px;margin-right:16px;">
          <div style="
            width:18px;height:4px;
            background:{item['color']};
            border-radius:2px;
          "></div>
          <div style="font-size:13px;font-weight:600;">
            {item['label']}
          </div>
        </div>
        """)

    st.markdown(
        f"""
        <div style="
          display:flex;
          align-items:center;
          padding:10px 14px;
          background:#F8F9FA;
          border:1px solid #DEE2E6;
          border-radius:10px;
          margin:12px 0 6px 0;
          flex-wrap:wrap;
        ">
          {''.join(items)}
        </div>
        """,
        unsafe_allow_html=True
    )


# ======================================
# 경로 시각화 함수
# ======================================
def draw_path_layer(
    m,
    graph,
    path,
    color="#0066FF",
    weight=6,
    opacity=0.9,
    tooltip="경로",
    is_gradient=False,
):
    if not path or len(path) < 2:
        return []

    # 그라데이션 컬러맵
    colormap = None
    if is_gradient and not hasattr(m, "_shadow_colormap"):
        colormap = cm.LinearColormap(
          colors=["#d73027", "#fc8d59", "#fee08b",
                "#d9ef8b", "#91cf60", "#1a9850"],
          vmin=0.0,
          vmax=1.0,
          caption="그늘 비율 (Shadow Ratio)",
        )
        colormap.add_to(m)
        m._shadow_colormap = colormap
    else:
        colormap = getattr(m, "_shadow_colormap", None)


    bounds_coords = []

    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        if not graph.has_edge(u, v):
            continue

        data = graph[u][v]
        geom = data.get("geometry")
        shadow = data.get("shadow_ratio", 0.0)

        # 5179 → 4326 변환
        try:
            gdf = gpd.GeoDataFrame(geometry=[geom], crs="EPSG:5179").to_crs("EPSG:4326")
        except Exception:
            continue

        for g in gdf.geometry:
            coords = []

            if g.geom_type == "LineString":
                coords = [(y, x) for x, y in g.coords]

            elif g.geom_type == "Polygon":
                coords = [(y, x) for x, y in g.exterior.coords]

            elif g.geom_type == "MultiLineString":
                for part in g.geoms:
                    coords = [(y, x) for x, y in part.coords]


            else:
                continue

            # 색상 결정
            line_color = colormap(shadow) if is_gradient else color
            line_tooltip = (
                f"그늘 비율: {shadow * 100:.0f}%" if is_gradient else tooltip
            )

            folium.PolyLine(
                coords,
                color=line_color,
                weight=weight,
                opacity=opacity,
                tooltip=line_tooltip,
            ).add_to(m)

            bounds_coords.extend(coords)

    return bounds_coords


# ======================================
# 마커 + 점선 연결 함수
# ======================================
def draw_marker_and_connector(
    m,
    user_lat, user_lon,
    node_xy_5179,
    popup,
    color
):
    # 스냅 노드 → WGS84
    pt = gpd.GeoDataFrame(
        geometry=[Point(node_xy_5179)],
        crs="EPSG:5179"
    ).to_crs("EPSG:4326")

    node_lat = pt.geometry.iloc[0].y
    node_lon = pt.geometry.iloc[0].x

    # 마커
    folium.Marker(
        [user_lat, user_lon],
        popup=popup,
        icon=folium.Icon(color=color)
    ).add_to(m)

    # 좌표 차이가 있으면 점선 연결
    if abs(user_lat - node_lat) > 1e-6 or abs(user_lon - node_lon) > 1e-6:
        folium.PolyLine(
            [(user_lat, user_lon), (node_lat, node_lon)],
            color=color,
            weight=2,
            opacity=0.7,
            dash_array="5,5"
        ).add_to(m)


# ======================================
# 경로 내 장애물 아이콘 오버레이 함수
# ======================================

# 엣지 중간 좌표 계산 함수 (핵심)
def get_edge_midpoint(geom):
    # LineString geometry → (lat, lon)
    try:
        gdf = gpd.GeoDataFrame(geometry=[geom], crs="EPSG:5179").to_crs("EPSG:4326")
        line = gdf.geometry.iloc[0]
        midpoint = line.interpolate(0.5, normalized=True)
        return midpoint.y, midpoint.x
    except Exception:
        return None

# 장애물 아이콘 오버레이 함수
def draw_obstacle_icons(m, G, path):
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        if not G.has_edge(u, v):
            continue

        d = G[u][v]
        geom = d.get("geometry")
        pos = get_edge_midpoint(geom)

        if not pos:
            continue

        lat, lon = pos

        # ---------- 횡단보도 ----------
        if d.get("crosswalk", 0):
            folium.Marker(
                [lat, lon],
                icon=folium.DivIcon(
                    html="<div style='font-size:20px'>🚦</div>"
                ),
                tooltip="횡단보도 (신호 대기)"
            ).add_to(m)

        # ---------- 육교 ----------
        if d.get("footbridge", 0):
            folium.Marker(
                [lat, lon],
                icon=folium.DivIcon(
                    html="<div style='font-size:20px'>🌉</div>"
                ),
                tooltip="육교 (직사광선 · 계단)"
            ).add_to(m)

        # ---------- 터널 ----------
        if d.get("tunnel", 0):
            folium.Marker(
                [lat, lon],
                icon=folium.DivIcon(
                    html="<div style='font-size:20px'>🕳️</div>"
                ),
                tooltip="터널 (매연 · 시야 저하)"
            ).add_to(m)

        # ---------- 실내 ----------
        if d.get("indoor", 0):
            folium.Marker(
                [lat, lon],
                icon=folium.DivIcon(
                    html="<div style='font-size:20px'>🏬</div>"
                ),
                tooltip="실내 보행 (그늘 100%)"
            ).add_to(m)


# ======================================
# 페르소나 데이터 (고양이 말투)
# ======================================
PERSONA_PRESETS = {
    "custom": {
        "label": "🛠️ 직접 설정 (Custom)",
        "desc": "집사야, 원하는 대로 골라봐! (가중치 자유 조절)",
        "cw": 0.5, "dl": 0.2, "af": False, "at": False, "ai": True
    },
    "2030": {
        "label": "🏃 2030 효율 모드",
        "desc": "적당히 시원하면서 빠른 길로 안내할게!",
        "cw": 0.5, "dl": 0.2, "af": False, "at": False, "ai": True
    },
    "elderly": {
        "label": "👴 편안한 산책 모드 (노약자)",
        "desc": "계단은 힘들잖아. 편안한 길로 가자.",
        "cw": 0.8, "dl": 0.4, "af": True, "at": True, "ai": True
    },
    "office": {
        "label": "💼 뽀송 출퇴근 모드 (직장인)",
        "desc": "땀 흘리기 싫지? 실내랑 지하 통로로 쏙쏙 피해 가자.",
        "cw": 0.7, "dl": 0.15, "af": False, "at": True, "ai": False 
    },
    "health": {
        "label": "❤️ 햇빛 완전 차단 모드",
        "desc": "조금 돌아가더라도 무조건! 제일 시원한 그늘로만 갈 거야.",
        "cw": 1.0, "dl": 0.5, "af": True, "at": True, "ai": False
    }
}


# [수정] 고양이 캐릭터 말풍선 함수 (들여쓰기 문제 해결)
def render_cat_comment(text, mood="normal"):
    # 1. 이미지/이모지 설정
    if mood == "angry":
        filename = "cat_angry.png"
        emoji = "😾"
    elif mood == "thinking":
        filename = "cat_thinking.png"
        emoji = "😿"
    else: # normal, happy
        filename = "cat_happy.png"
        emoji = "😺"

    img_path = os.path.join("images", filename)

    # 2. 이미지 Base64 변환
    img_tag = ""
    if os.path.exists(img_path):
        img_base64 = get_img_as_base64(img_path)
        img_tag = f'<img src="data:image/png;base64,{img_base64}" style="width: 85px; height: auto; margin-right: 15px; filter: drop-shadow(2px 4px 6px rgba(0,0,0,0.1));">'
    else:
        img_tag = f'<div style="font-size: 60px; margin-right: 15px;">{emoji}</div>'

    # 3. HTML 코드 (★중요: 들여쓰기를 없애고 한 줄로 붙이거나, 왼쪽 벽에 붙여야 함)
    # 아래처럼 f-string 안의 태그들을 왼쪽 끝으로 당겼습니다.
    html_code = f"""
<div style="display: flex; align-items: flex-end; margin-top: 10px; margin-bottom: 20px;">
<div style="flex-shrink: 0;">{img_tag}</div>
<div style="background-color: #ffffff; padding: 16px 22px; border-radius: 25px 25px 25px 3px; border: 2px solid #E3D5F5; box-shadow: 2px 2px 8px rgba(0,0,0,0.05); max-width: 75%; position: relative; bottom: 10px;">
<div style="font-size: 13px; color: #9C27B0; font-weight: 700; margin-bottom: 5px;">🐈‍ 까망이 (Shadow Cat)</div>
<div style="font-size: 16px; color: #424242; line-height: 1.5; font-weight: 400;">{text}</div>
</div>
</div>"""

    st.markdown(html_code, unsafe_allow_html=True)



# ======================================
# 사이드바 (입력 영역)
# ======================================
with st.sidebar:
    # 1. 로고 이미지 표시 (너비 조절 가능)
    if os.path.exists("images/logo.png"):
        st.image("images/logo.png", width=180) # 로고 크기에 맞춰 조절

    # 2. 캐릭터 프로필
    st.markdown("""
    ### 🐾 까망이 (Shadow Cat)
    > **"야옹, 거긴 너무 뜨거워! 이쪽 그늘로 와."**

    강남구 골목골목 그늘만 찾아다니는
    길냥이 **까망이**가 시원한 길을 알려줄게.
    """)
    st.divider()

    st.header("📍 경로 설정")

    start_query = st.text_input("출발지", "역삼역 8번 출구")
    end_query = st.text_input("도착지", "KT플라자 강남점")


    st.subheader("🌡️ 기상 시나리오 선택")

    weather_mode = st.radio(
        "기온 데이터 모드",
        ["실시간", "폭염 (demo)", "폭염 + 강수 (demo)"],
        index = 0
    )

    st.session_state.weather_mode = weather_mode


    st.divider()
    st.subheader("🕒 시간대 설정")

    time_slot = st.slider(
        "보행 시작 시간",
        min_value=8,
        max_value=19,
        value=14,
        step=1,
        format="%d시"
    )


    st.divider()
    st.subheader("🎯 퍼스널 경로 설정")

    use_personal_mode = st.toggle(
        "퍼스널 모드 사용",
        value = False,
        help = "나만의 선호도에 따라 경로를 추천합니다."
    )

    st.session_state.use_personal_mode = use_personal_mode

    if use_personal_mode != st.session_state.get("use_personal_mode_prev", False):
        st.session_state.personal_route_ready = False

    st.session_state.use_personal_mode_prev = use_personal_mode


    if use_personal_mode:

        # 페르소나 선택 박스
        persona_key = st.selectbox(
            "나에게 맞는 모드 선택",
            options=list(PERSONA_PRESETS.keys()),
            format_func=lambda x: PERSONA_PRESETS[x]["label"]
        )

        # 선택된 프리셋 값 가져오기
        preset = PERSONA_PRESETS[persona_key]
        st.session_state.selected_persona = persona_key # 나중에 멘트에 쓰기 위해 저장
        st.caption(f"💡 {preset['desc']}")

        # 슬라이더/체크박스 (프리셋 값으로 설정하되, custom이 아니면 비활성화하여 UX 단순화)
        is_disabled = (persona_key != "custom")

        cooling_weight = st.slider("❄️ 시원함 선호도", 0.0, 1.0, preset["cw"], 0.1, disabled=is_disabled)
        detour_limit = st.slider("📏 최대 우회 허용", 0.0, 1.0, preset["dl"], 0.1, disabled=is_disabled)

        c1, c2, c3 = st.columns(3)
        avoid_footbridge = c1.checkbox("육교 피하기", value=preset["af"], disabled=is_disabled)
        avoid_tunnel = c2.checkbox("터널 피하기", value=preset["at"], disabled=is_disabled)
        avoid_indoor = c3.checkbox("실내 피하기", value=preset["ai"], disabled=is_disabled)

        st.session_state.personal_pref = {
          "cooling_weight": cooling_weight, "detour_limit": detour_limit,
          "avoid_footbridge": avoid_footbridge, "avoid_tunnel": avoid_tunnel,
          "avoid_indoor": avoid_indoor,
        }


    submit = st.button("경로 탐색", type="primary")


# =========================
# 데이터 로드 (앱 시작 시 1회)
# =========================
roads_gdf = load_roads()
shadow_df = load_shadow_data()
shade_shelters_df = load_shade_shelters()

base_G = build_base_graph_with_shadow(roads_gdf, shadow_df)
node_tree, node_ids, node_xy = build_node_index(roads_gdf)


# ======================================
# 검색 버튼 클릭 시 (상태 변경은 여기서만!)
# ======================================
if submit:
    st.session_state.is_loading = True
    st.session_state.last_submit_time = time.time()
    # 1. Kakao 장소 검색
    start = search_place_kakao(start_query)
    end   = search_place_kakao(end_query)

    if not start or not end:
        st.error("출발지 또는 도착지를 찾을 수 없습니다.")
        st.stop()

    start_lat, start_lon, start_name = start
    end_lat, end_lon, end_name = end

    # 2. 좌표 → 네트워크 노드 스냅
    u_node = get_nearest_node(start_lat, start_lon, node_tree, node_ids, node_xy)
    v_node = get_nearest_node(end_lat, end_lon, node_tree, node_ids, node_xy)

    new_input = {
        "start": {
            "name": start_name,
            "lat": start_lat,
            "lon": start_lon,
            "node": u_node,
        },
        "end": {
            "name": end_name,
            "lat": end_lat,
            "lon": end_lon,
            "node": v_node,
        },
        "time_slot": time_slot,
    }

    # 🔴 input이 이전과 다르면
    if st.session_state.get("route_input") != new_input:
        st.session_state.route_result = None  # 결과 무효화

    st.session_state.route_input = new_input

    # --- 환경 조건 ---
    mode = st.session_state.weather_mode

    if mode == "실시간":
        env = get_realtime_weather_forecast(start_lat, start_lon)
    elif mode == "폭염 (demo)":
        env = build_hot_demo_weather()
    elif mode == "폭염 + 강수 (demo)":
        env = build_rain_demo_weather()

    st.session_state.env = env

    env_at_time = get_env_at_time(env, time_slot)

    # --- 경로 계산 ---
    G = copy.deepcopy(base_G)

    # 3. 그림자 비율 적용
    rain_mm = env_at_time["rain"]
    apply_shadow_ratio(G, time_slot, rain_mm)

    # 💡 여기서 비용 계산
    apply_costs(G)

    if st.session_state.use_personal_mode:
        apply_personal_costs(G, rain_mm, st.session_state.personal_pref)


    # 4. 경로 계산 (여기서 nx.shortest_path 사용)
    path_shortest = nx.shortest_path(
        G, u_node, v_node, weight="cost_shortest"
    )
    path_cooling = nx.shortest_path(
        G, u_node, v_node, weight="cost_cooling"
    )
    path_main = nx.shortest_path(
        G, u_node, v_node, weight="cost_main"
    )

    if st.session_state.use_personal_mode:
        detour_limit = st.session_state.personal_pref.get("detour_limit", 0.2)
        path_personal = find_constrained_best_path(
            G, u_node, v_node, base_path=path_shortest, cost_key="cost_personal", detour_limit=detour_limit
        )
    else:
        path_personal = None

    # 5. 세션에 저장
    st.session_state.route_result = {
        "paths": {
            "shortest": path_shortest,
            "cooling": path_cooling,
            "main": path_main,
        },
        "graph": G,
    }
    if path_personal is not None:
        st.session_state.route_result["paths"]["personal"] = path_personal


    avg_shadow = {
        "shortest": calc_avg_shadow(G, path_shortest),
        "cooling": calc_avg_shadow(G, path_cooling),
        "main": calc_avg_shadow(G, path_main),
    }
    # 퍼스널 경로는 존재할 때만
    if path_personal is not None:
        avg_shadow["personal"] = calc_avg_shadow(G, path_personal)

    st.session_state.avg_shadow = avg_shadow

    # --- heatwave 판단 ---
    base_temp = env_at_time["temp"]
    heatwave = is_heatwave(base_temp)

    st.session_state.heatwave = {
      "active": heatwave,
      "temp": base_temp,
    }

    st.session_state.route_ready = True
    st.session_state.personal_route_ready = st.session_state.use_personal_mode
    st.session_state.is_loading = False


# ===============================
# 결과 렌더링 영역 (submit 이후)
# ===============================
if st.session_state.get("is_loading"):
    st.markdown(
        """
        <div style="
            background:#EEF6FF;
            border-left:6px solid #339AF0;
            padding:12px 16px;
            border-radius:8px;
            margin-bottom:12px;
            font-weight:600;
        ">
        🔄 경로를 다시 계산하고 있어요…<br>
        <span style="font-weight:400">
        날씨·시간·보행 환경을 반영 중입니다.
        </span>
        </div>
        """,
        unsafe_allow_html=True
    )

if st.session_state.get("route_ready") and not st.session_state.get("is_loading"):
    # ===============================
    # 결과 렌더링 영역 (순서 변경: 지도 -> 멘트 -> KPI)
    # ===============================

    # ---------- 입력 정보 ----------
    s = st.session_state.route_input["start"]
    e = st.session_state.route_input["end"]

    center = [
        (s["lat"] + e["lat"]) / 2,
        (s["lon"] + e["lon"]) / 2,
    ]

    # ---------- 결과 정보 ----------
    result = st.session_state.route_result
    G = result["graph"]
    paths = result["paths"]

    path_shortest = paths.get("shortest")
    path_cooling  = paths.get("cooling")
    path_main     = paths.get("main")
    path_personal = paths.get("personal")



    # ---------- 1. 뷰 모드 선택 (라디오 버튼) ----------
    rain_mm = st.session_state.env.get("rain_mm", 0.0)
    heatwave = st.session_state.get("heatwave", {}).get("active", False)

    if heatwave and rain_mm == 0:
        default_view = "❄️ 쿨링 경로"
    else:
        default_view = "🔍 모든 경로 비교"

    view_options = ["🔍 모든 경로 비교", "❄️ 쿨링 경로", "⏱️ 최단 경로", "🛣️ 큰길 우선"]

    if st.session_state.get("use_personal_mode"):
        view_options.insert(1, "🎯 나만의 경로")
        default_view = "🎯 나만의 경로"

    if default_view not in view_options:
        default_view = view_options[0]

    st.markdown("### 🗺️ 경로 지도")

    # (A) [수정] 폭염 경고 배지 (까망이 말투 적용)
    if heatwave and rain_mm == 0:
         st.markdown(f"""
          <div style="background-color:#FFE5E5; border-left:6px solid #FF4B4B; padding:12px 16px; border-radius:8px; margin-bottom:12px; font-weight:600;">
          🔥 으악! 지금 밖은 찜통이야! ({st.session_state.heatwave['temp']:.1f}℃)<br>
          <span style="font-weight:400"><b>쿨링패스</b>로 안 가면 큰일 난다냥! 🐾</span>
          </div>
          """, unsafe_allow_html=True)

    # (B) [추가] 강수 안내 배지 (비 올 때 표시)
    if rain_mm > 0:
        st.markdown(f"""
          <div style="background-color:#E3FAFC; border-left:6px solid #15AABF; padding:12px 16px; border-radius:8px; margin-bottom:12px; font-weight:600;">
          ☔ 비가 오고 있어! (강수량 {rain_mm}mm)<br>
          <span style="font-weight:400">우산을 쓰니까 <b>그늘은 신경 안 써도 돼.</b> 대신 미끄러지지 않게 조심!</span>
          </div>
          """, unsafe_allow_html=True)

    view_mode = st.radio("지도 보기 모드", view_options, index=view_options.index(default_view), horizontal=True, label_visibility="collapsed")


    # ---------- 타겟 설정 ----------
    if rain_mm > 0:
        target_key = "shortest"
    elif view_mode == "🔍 모든 경로 비교":
        target_key = None
    else:
        target_key = {
            "❄️ 쿨링 경로": "cooling", "⏱️ 최단 경로": "shortest", 
            "🛣️ 큰길 우선": "main", "🎯 나만의 경로": "personal",
        }[view_mode]

    target_path = paths.get(target_key)


    # ---------- 2. 지도 렌더링 (가장 먼저!) ----------

    with st.container():
        if view_mode == "🔍 모든 경로 비교":
            render_route_legend(show_personal=st.session_state.get("use_personal_mode", False))

        m = folium.Map(location=center, zoom_start=16.5)
        folium.TileLayer(tiles="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", attr="CARTO", name="Gray", control=False).add_to(m)

        # 경로 그리기
        if view_mode == "🔍 모든 경로 비교":
            draw_path_layer(m, G, path_main, color="#9E9E9E", weight=5, opacity=0.85, tooltip="큰길 우선")
            draw_path_layer(m, G, path_shortest, color="#333333", weight=6, opacity=0.9, tooltip="최단 경로")
            # 비 올 때는 쿨링 경로도 그냥 파란색 실선으로 표시 (그늘 의미 없음)
            cool_color = "#00FFFF" if rain_mm == 0 else "#15AABF"
            draw_path_layer(m, G, path_cooling, color=cool_color, weight=8, opacity=1.0, tooltip="쿨링 경로")
            if path_personal:
                draw_path_layer(m, G, path_personal, color="#845EF7", weight=7, opacity=0.95, tooltip="나만의 경로")
        elif target_key and target_path:
            is_grad = (rain_mm == 0)
            color = None if is_grad else ("#15AABF" if target_key=="cooling" else "#333333")
            draw_path_layer(m, G, target_path, weight=9, opacity=0.95, is_gradient=is_grad, color=color)
            draw_obstacle_icons(m, G, target_path)

        # 그늘막 & 출발/도착 마커
        if not shade_shelters_df.empty:
            for _, row in shade_shelters_df.iterrows():
                folium.Marker([row['위도'], row['경도']], icon=folium.Icon(color='green', icon='umbrella', prefix='fa'), tooltip=f"⛱️ 그늘막").add_to(m)

        draw_marker_and_connector(m, s["lat"], s["lon"], node_xy[node_ids.index(s["node"])], popup=f"출발: {s['name']}", color="green")
        draw_marker_and_connector(m, e["lat"], e["lon"], node_xy[node_ids.index(e["node"])], popup=f"도착: {e['name']}", color="red")

        st_folium(m, height=450, use_container_width=True)




    # ---------- 3. 상세 분석 (캐릭터 멘트 + KPI) ----------

    if st.session_state.use_personal_mode and not st.session_state.personal_route_ready and target_key == "personal":
         st.info("사이드바에서 집사가 원하는 모드로 설정해줘! 내가 딱 맞는 경로를 추천해줄게.")

    elif target_key: # 단일 경로 모드일 때만 상세 분석 표시
        title_map = {"cooling": "❄️ 쿨링 경로 분석", "shortest": "⏱️ 최단 경로 분석", "main": "🛣️ 큰길 경로 분석", "personal": "🎯 나만의 경로 분석"}

        st.markdown(f"### {title_map[target_key]}")

        # KPI 미리 계산 (멘트 생성을 위해)
        env_at_time = get_env_at_time(st.session_state.env, time_slot)
        kpi = calculate_kpis(G, path_shortest, target_path, env_at_time["temp"], env_at_time["rain"], env_at_time["humidity"])
        kpi_story = build_kpi_story(kpi)
        grade_info = calculate_route_grade(kpi, mode=target_key, pref=st.session_state.get("personal_pref"))

        # (A) 캐릭터 멘트 생성 및 표시
        grade = grade_info['grade']
        comment, mood = "", "normal"

        # 1순위: 비가 올 때
        if rain_mm > 0:
            comment = "비가 와서 그늘은 소용없어. ☔ 대신 미끄러지지 않게 조심해서 걷자냥!"
            mood = "thinking"

        elif target_key == "personal":
            pk = st.session_state.get("selected_persona", "custom")
            if pk == "elderly" and grade in ["A", "B"]: comment, mood = "경사가 완만하고 그늘이 많아서 걷기 편해. 천천히 다녀와!", "happy"
            elif pk == "office": comment, mood = "이 정도면 셔츠 젖을 걱정은 없겠다. 쾌적하게 가자!", "happy"
            elif pk == "health": comment = "햇빛을 피해 제일 안전한 길로 골랐어. 건강이 최고니까!"

        if not comment:
            if grade == "A": comment, mood = "완벽해! 발바닥이 하나도 안 뜨거운 최고의 그늘길이야. 🐾", "happy"
            elif grade == "B": comment, mood = "나쁘지 않아. 적당히 시원하게 걸을 수 있겠어.", "normal"
            elif grade == "C": comment, mood = "음... 조금 애매한데? 땀이 좀 날 수도 있겠다.", "thinking"
            else: comment, mood = "으아, 여긴 털 탈 것 같아! 🔥 너무 뜨거우니까 다른 길로 가자.", "angry"

        render_cat_comment(comment, mood)

        # (B) 등급 배지 (비 올 땐 등급 의미가 적으므로 설명 생략하거나 변경 가능)
        if rain_mm == 0:
            grade_label = get_grade_label(view_mode)
            st.markdown(f"""
                <div style="display:inline-block; padding:6px 14px; border-radius:20px; background:#E3FAFC; color:#0B7285; font-weight:700; margin-bottom:15px;">
                {grade_label} {grade_info['grade']} · {grade_info['score']}점
                </div>
                """, unsafe_allow_html=True)


        # (C) KPI 카드 렌더링
        c1, c2, c3, c4, c5 = st.columns(5)
        render_kpi_card(c1, "📏 이동 거리", f"{kpi['length']['target']:.0f}m", f"{abs(kpi['length']['detour_ratio']*100):.1f}%", False, story_text=kpi_story["detour"]["text"], story_tone=kpi_story["detour"]["tone"])
        render_kpi_card(c2, "⏱ 소요시간", f"{kpi['time']['target']/60:.1f}분", f"{abs(kpi['time']['time_ratio']*100):.1f}%", False, story_text=kpi_story["time"]["text"], story_tone=kpi_story["time"]["tone"])
        render_kpi_card(c3, "🌳 그늘확보", f"{kpi['shadow']['target']*100:.1f}%", f"{abs(kpi['shadow']['gain']*100):.1f}%p", True, story_text=kpi_story["shadow"]["text"], story_tone=kpi_story["shadow"]["tone"])
        render_kpi_card(c4, "🌡 체감온도", f"{kpi['temperature']['target']:.1f}℃", f"{abs(kpi['temperature']['diff']):.1f}℃", False, story_text=kpi_story["temperature"]["text"], story_tone=kpi_story["temperature"]["tone"])

        hum = kpi["humidity"]
        h_label = hum["label"]
        h_pos = h_label in ["쾌적", "보통"]
        h_emoji = {"쾌적":"😊","보통":"🙂","높음":"😓","매우 높음":"🥵"}[h_label]
        render_kpi_card(c5, "💧 습도", f"{hum['value']:.0f}%", f"{h_emoji} {h_label}", h_pos, True, story_text=kpi_story["humidity"]["text"], story_tone=kpi_story["humidity"]["tone"])

        # 장애물 배지
        obs = count_obstacles(G, target_path)
        render_obstacle_badges(obs)

    else:
        # 비교 모드일 때
        render_multi_route_summary(paths, G, st.session_state.env, time_slot, st.session_state.get("personal_pref"))


    # ---------- 4. 그래프 (맨 아래) ----------
    if target_key and "env" in st.session_state:
        st.markdown("---")
        st.markdown("### 🌡 시간대별 기온 & 체감온도 예보 (08~19시)")


        env = st.session_state.env
        avg_shadow = st.session_state.avg_shadow.get(target_key)

        if avg_shadow is None:
                st.info("선택한 경로의 정보를 계산 중이다냥.")
                st.stop()


        graph_data = build_forecast_for_graph(env, avg_shadow, time_slot)

        if graph_data:
            df = pd.DataFrame(graph_data).set_index("time")

            max_row = df.loc[df["temp"].idxmax()]
            max_hour = max_row["hour"]
            max_temp = max_row["temp"]

            if time_slot < max_hour:
                st.info(f"⏳ {(max_hour-time_slot):.0f}시간 뒤에 제일 뜨거워져! 얼른 움직이자! 🐾")
            elif time_slot > max_hour:
                st.info("🌆 더위가 좀 가라앉았네! 아까보단 걷기 편할 거야.")
            else:
                st.info("🔥 으악! 지금이 **제일 더운 시간**이야. 꼭 쿨링 경로로 가야 해!")

            y_min = df[["temp","feels_like"]].min().min() - 1
            y_max = df[["temp","feels_like"]].max().max() + 1


            base = alt.Chart(df.reset_index()).encode(
                x=alt.X("hour:O", title="시간"),
            )

            line_temp = base.mark_line(color="#FF6B6B").encode(
                y=alt.Y("temp:Q", scale=alt.Scale(domain=[y_min, y_max]), title="기온(℃)"),
            )

            line_feels = base.mark_line(color="#339AF0").encode(
                y=alt.Y("feels_like:Q", title="체감온도(℃)"),
            )

            vline = alt.Chart(pd.DataFrame({"hour":[time_slot]})).mark_rule(
                color="black",
                strokeDash=[4,4]
            ).encode(x="hour:O")


            # --- 최고기온 포인트 강조 ---
            peak_point = alt.Chart(
                pd.DataFrame({
                    "hour": [max_hour],
                    "temp": [max_temp]
                })
            ).mark_point(
                size=160,
                filled=True,
                color="#FF6B6B"
            ).encode(
                x="hour:O",
                y="temp:Q"
            )

            peak_label = alt.Chart(
                pd.DataFrame({
                    "hour": [max_hour],
                    "temp": [max_temp],
                    "label": [f"🔥 최고 {max_temp:.1f}℃"]
                })
            ).mark_text(
                dy=-18,
                fontSize=14,
                fontWeight="bold",
                color="#C92A2A"
            ).encode(
                x="hour:O",
                y="temp:Q",
                text="label"
            )

            # 순서 중요
            chart = (line_temp + line_feels + vline + peak_point + peak_label).properties(height=400, background='#FDFBF7')

            st.altair_chart(chart, use_container_width=True)

            st.caption(f"🌡️ {max_hour:.0f}시에 최고기온 {max_temp:.1f}℃ 예상됩니다.")
            st.caption("체감온도는 선택한 경로의 평균 그늘 비율을 반영합니다.")
        else:
            st.info("기온 예보 데이터를 불러올 수 없습니다.")


# 안내 메시지 (초기 상태)
else:
    # 웰컴 랜딩 페이지
    c1, c2 = st.columns([1, 1.5])
    with c1:
        if os.path.exists("images/cat_happy.png"):
            st.image("images/cat_happy.png", use_container_width=True)
        else:
            st.markdown("<div style='font-size:150px; text-align:center;'>🐈‍</div>", unsafe_allow_html=True)

    with c2:
        # [수정] 태·피·소 컨셉 적용
        st.markdown("""
        <div style='margin-top: 30px;'>
            <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 10px;">
                <img src="data:image/png;base64,{}" style="width: 55px; height: 55px; border-radius: 10px; display: {};"> 
                <h1 style='color:#333; margin:0; font-size:42px;'>태·피·소 🐾</h1>
            </div>
            <h3 style='color:#7E57C2; margin-top:10px; font-weight:700;'>까망이의 <span style='color:#FF6B6B'>태</span>양 <span style='color:#339AF0'>피</span>하기 <span style='color:#51CF66'>소</span>동!</h3>
            <p style='font-size:18px; color:#666; line-height:1.6;'>
                "큰일 났다냥! 밖은 지금 용광로야! 🔥<br>
                나랑 같이 <b>가장 시원한 대피소(그늘 길)</b>로 도망가자.<br>
                내 발자국만 따라오면 절대 타지 않는다냥!"
            </p>
            <br>
            <div style='background:#F1F3F5; padding:20px; border-radius:15px; color:#555; border:1px solid #E9ECEF;'>
                🚨 <b>작전 개시 방법</b><br>
                👈 왼쪽에서 <b>출발지와 목적지</b>를 입력하고 <b>[경로 탐색]</b>을 눌러라 냥!
            </div>
        </div>
        """.format(
            get_img_as_base64("images/logo.png") if os.path.exists("images/logo.png") else "",
            "block" if os.path.exists("images/logo.png") else "none"
        ), unsafe_allow_html=True)
