import os

# API Key
KAKAO_API_KEY = "your-kakao-map-api-key"

# Paths
DATA_DIR = "data"
ROADS_SHP = os.path.join(DATA_DIR, "non_buffered_roads.shp")
SHADOW_CSV = os.path.join(DATA_DIR, "hourly_link_stat_20250708.csv")
SHELTER_CSV = os.path.join(DATA_DIR, "gangnamgu_shade_shelters.csv")

# Visualization
ROUTE_COLOR_MAP = {
    "cooling": {"label": "❄️ 쿨링 경로", "color": "#00FFFF", "desc": "그늘과 시원함을 우선한 경로"},
    "shortest": {"label": "⏱️ 최단 경로", "color": "#333333", "desc": "이동 거리를 최소화한 경로"},
    "main": {"label": "🛣️ 큰길 우선", "color": "#9E9E9E", "desc": "넓고 안정적인 보행로 중심"},
    "personal": {"label": "🎯 나만의 경로", "color": "#845EF7", "desc": "나의 선호도를 반영한 맞춤 경로"}
}
