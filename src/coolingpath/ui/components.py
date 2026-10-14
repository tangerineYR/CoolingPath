"""CoolingPath ui.components implementation."""

import streamlit as st
import folium
import geopandas as gpd
import os
from shapely.geometry import Point
import branca.colormap as cm
import base64
from coolingpath.services import get_env_at_time
from coolingpath.metrics import calculate_kpis, calculate_route_grade
from coolingpath.config import ROUTE_COLOR_MAP, ASSET_DIR


def get_img_as_base64(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()


def render_obstacle_badges(obs):

    def badge(icon, label, value, warn=False):
        bg = "#FFF3CD" if warn else "#F1F3F5"
        border = "#FFC107" if warn else "#DEE2E6"
        return f'\n        <div style="\n            display:inline-flex;\n            align-items:center;\n            gap:8px;\n            padding:6px 10px;\n            margin:4px 6px 4px 0;\n            background:{bg};\n            border:1px solid {border};\n            border-radius:16px;\n            font-size:13px;\n            font-weight:500;\n        ">\n            <span style="font-size:16px">{icon}</span>\n            <span>{label}</span>\n            <span style="font-weight:700">{value}</span>\n        </div>\n        '

    html = ""
    html += badge("🚦", "횡단보도", f"{obs['crosswalk']}회", obs["crosswalk"] > 0)
    html += badge("🌉", "육교", f"{obs['footbridge']}회", obs["footbridge"] > 0)
    html += badge(
        "🕳️", "터널", "있음" if obs["tunnel"] > 0 else "없음", obs["tunnel"] > 0
    )
    html += badge(
        "🏬", "실내", "있음" if obs["indoor"] > 0 else "없음", obs["indoor"] > 0
    )
    st.markdown("#### 🚧 경로 환경 요소")
    st.markdown(html, unsafe_allow_html=True)


def build_kpi_story(kpi):
    story = {}
    time_diff = kpi["time"]["time_ratio"]
    if time_diff <= -0.05:
        story["time"] = {
            "tone": "positive",
            "text": "⏱️ 생각보다 빨리 도착한다냥! 신난다 💨",
        }
    elif time_diff <= 0.05:
        story["time"] = {
            "tone": "neutral",
            "text": "⏱️ 시간은 비슷해. 무리 없이 걸을 수 있어.",
        }
    else:
        story["time"] = {
            "tone": "warning",
            "text": "⏱️ 조금 돌아가지만, 그만큼 덜 덥고 쾌적할 거야.",
        }
    temp_diff = kpi["temperature"]["diff"]
    if temp_diff <= -1.5:
        story["temperature"] = {
            "tone": "positive",
            "text": "🌡️ 완전 시원해! 에어컨 켠 줄 알았다냥 ❄️",
        }
    elif temp_diff <= -0.5:
        story["temperature"] = {
            "tone": "positive",
            "text": "🌡️ 그늘 적당해! 한여름엔 이 차이가 꽤 크게 느껴질걸?",
        }
    elif temp_diff <= 0.5:
        story["temperature"] = {
            "tone": "neutral",
            "text": "🌡️ 온도는 비슷해. 그래도 최단거리보단 낫겠지?",
        }
    else:
        story["temperature"] = {
            "tone": "warning",
            "text": "🌡️ 으아, 여긴 좀 더울 수도 있어. 조심해!",
        }
    detour = kpi["length"]["detour_ratio"]
    if detour <= 0.1:
        story["detour"] = {
            "tone": "positive",
            "text": "📏 거리도 가깝고 시원하고! 완전 럭키잖아? 🍀",
        }
    elif detour <= 0.2:
        story["detour"] = {
            "tone": "neutral",
            "text": "📏 조금 더 걷긴 하는데, 산책한다고 생각하자냥.",
        }
    else:
        story["detour"] = {
            "tone": "warning",
            "text": "📏 꽤 많이 돌아가야 해. 그래도 시원함이 중요하다면!",
        }
    shadow_gain = kpi["shadow"]["gain"]
    if shadow_gain >= 0.15:
        story["shadow"] = {
            "tone": "positive",
            "text": "🌳 그늘 천국이야! 내 발바닥 절대 지켜 🐾",
        }
    elif shadow_gain >= 0.05:
        story["shadow"] = {
            "tone": "positive",
            "text": "🌳 그늘이 꽤 있어. 햇빛 피하기 딱 좋아.",
        }
    else:
        story["shadow"] = {
            "tone": "neutral",
            "text": "🌳 그늘 양은 비슷해. 모자나 양산 챙겼어?",
        }
    humidity_label = kpi["humidity"]["label"]
    humidity_story = {
        "쾌적": "💧 털이 뽀송뽀송해지는 쾌적한 날씨야!",
        "보통": "💧 조금 눅눅하지만 참을 만해.",
        "높음": "💧 으, 끈적거려. 물 자주 마셔냥!",
        "매우 높음": "💧 공기가 물 먹은 솜 같아... 무리하지 마.",
    }
    story["humidity"] = {
        "tone": "warning" if humidity_label in ["높음", "매우 높음"] else "neutral",
        "text": humidity_story[humidity_label],
    }
    return story


def render_kpi_card(
    col,
    title,
    value,
    delta_text,
    delta_positive=True,
    is_humidity=False,
    story_text=None,
    story_tone="neutral",
):
    delta_color = "#20C997" if delta_positive else "#FA5252"
    if is_humidity:
        delta_arrow = ""
    elif delta_positive:
        delta_arrow = "▲"
    else:
        delta_arrow = "▼"
    bg_map = {"positive": "#E6FCF5", "neutral": "#F8F9FA", "warning": "#FFF4E6"}
    border_map = {"positive": "#20C997", "neutral": "#ADB5BD", "warning": "#FAB005"}
    col.markdown(
        f'\n    <div style="padding:8px 4px;">\n      <div style="font-size:20px; font-weight:600;">{title}</div>\n\n      <div style="font-size:30px; font-weight:700; margin-top:2px;">\n        {value}\n      </div>\n\n      <div style="\n        font-size:15px;\n        font-weight:600;\n        color:{delta_color};\n        margin-top:2px;\n      ">\n        {delta_arrow} {delta_text}\n      </div>\n\n      <div style="\n        margin-top:8px;\n        background:{bg_map[story_tone]};\n        border-left:5px solid {border_map[story_tone]};\n        padding:10px 12px;\n        border-radius:8px;\n        font-size:14px;\n      ">\n        {story_text}\n      </div>\n    </div>\n    ',
        unsafe_allow_html=True,
    )


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


def render_multi_route_summary(paths, G, env, time_slot, personal_pref=None):
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
            humidity=env_at_time["humidity"],
        )
        grade = calculate_route_grade(
            kpi, mode=key, pref=personal_pref if key == "personal" else None
        )
        story = get_route_summary_story(key, kpi)
        title = {
            "cooling": "❄️ 쿨링",
            "shortest": "⏱️ 최단",
            "main": "🛣️ 큰길",
            "personal": "🎯 나의 경로",
        }[key]
        cols[i].markdown(
            f"""\n            <div style="\n              padding:14px;\n              border-radius:12px;\n              background:#F8F9FA;\n              border:1px solid #DEE2E6;\n              text-align:center;\n            ">\n              <div style="font-size:18px;font-weight:700">{title}</div>\n              <div style="margin-top:6px;font-size:28px;font-weight:800">\n                {grade["grade"]}\n              </div>\n              <div style="font-size:15px;color:#495057">\n                {grade["score"]}점\n              </div>\n\n              <!-- 🔹 한 줄 스토리 -->\n              <div style="\n                margin-top:6px;\n                font-size:13px;\n                color:#343A40;\n                background:#FFFFFF;\n                padding:6px 8px;\n                border-radius:8px;\n              ">\n                {story}\n              </div>\n\n              <hr style="margin:8px 0">\n\n              <div style="font-size:15px">📏 {kpi["length"]["target"]:.0f}m</div>\n              <div style="font-size:15px">⏱ {kpi["time"]["target"] / 60:.1f}분</div>\n              <div style="font-size:15px">🌳 {kpi["shadow"]["target"] * 100:.0f}%</div>\n              <div style="font-size:15px">🌡 {kpi["temperature"]["target"]:.1f}℃</div>\n\n            </div>\n            """,
            unsafe_allow_html=True,
        )
        i += 1
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)


def get_grade_label(view_mode):
    return {
        "❄️ 쿨링 경로": "❄️ 쿨링 경로 등급",
        "⏱️ 최단 경로": "⏱️ 이동 효율 등급",
        "🛣️ 큰길 우선": "🛣️ 안정 보행 등급",
        "🎯 나만의 경로": "🎯 나의 기준 등급",
    }.get(view_mode, "경로 종합 등급")


def grade_story(grade):
    return {
        "A": "🏆 대박! 그늘이 꽉 찬 최고의 산책로야. 당장 출발해! 🐾",
        "B": "👍 꽤 괜찮은데? 시원함과 거리의 밸런스가 좋아.",
        "C": "🙂 쏘쏘~ 무난하지만 땀은 조금 날 수도 있어.",
        "D": "⚠️ 앗, 뜨거! 이 길은 햇빛이 너무 많아. 다시 생각해봐.",
    }[grade]


def render_route_legend(show_personal=False):
    items = []
    for key in ["cooling", "shortest", "main"]:
        item = ROUTE_COLOR_MAP[key]
        items.append(
            f"""\n        <div style="display:flex;align-items:center;gap:8px;margin-right:16px;">\n          <div style="\n            width:18px;height:4px;\n            background:{item["color"]};\n            border-radius:2px;\n          "></div>\n          <div style="font-size:13px;font-weight:600;">\n            {item["label"]}\n          </div>\n        </div>\n        """
        )
    if show_personal:
        item = ROUTE_COLOR_MAP["personal"]
        items.append(
            f"""\n        <div style="display:flex;align-items:center;gap:8px;margin-right:16px;">\n          <div style="\n            width:18px;height:4px;\n            background:{item["color"]};\n            border-radius:2px;\n          "></div>\n          <div style="font-size:13px;font-weight:600;">\n            {item["label"]}\n          </div>\n        </div>\n        """
        )
    st.markdown(
        f"""\n        <div style="\n          display:flex;\n          align-items:center;\n          padding:10px 14px;\n          background:#F8F9FA;\n          border:1px solid #DEE2E6;\n          border-radius:10px;\n          margin:12px 0 6px 0;\n          flex-wrap:wrap;\n        ">\n          {"".join(items)}\n        </div>\n        """,
        unsafe_allow_html=True,
    )


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
    colormap = None
    if is_gradient and (not hasattr(m, "_shadow_colormap")):
        colormap = cm.LinearColormap(
            colors=["#d73027", "#fc8d59", "#fee08b", "#d9ef8b", "#91cf60", "#1a9850"],
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
        u, v = (path[i], path[i + 1])
        if not graph.has_edge(u, v):
            continue
        data = graph[u][v]
        geom = data.get("geometry")
        shadow = data.get("shadow_ratio", 0.0)
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
            line_color = colormap(shadow) if is_gradient else color
            line_tooltip = f"그늘 비율: {shadow * 100:.0f}%" if is_gradient else tooltip
            folium.PolyLine(
                coords,
                color=line_color,
                weight=weight,
                opacity=opacity,
                tooltip=line_tooltip,
            ).add_to(m)
            bounds_coords.extend(coords)
    return bounds_coords


def draw_marker_and_connector(m, user_lat, user_lon, node_xy_5179, popup, color):
    pt = gpd.GeoDataFrame(geometry=[Point(node_xy_5179)], crs="EPSG:5179").to_crs(
        "EPSG:4326"
    )
    node_lat = pt.geometry.iloc[0].y
    node_lon = pt.geometry.iloc[0].x
    folium.Marker(
        [user_lat, user_lon], popup=popup, icon=folium.Icon(color=color)
    ).add_to(m)
    if abs(user_lat - node_lat) > 1e-06 or abs(user_lon - node_lon) > 1e-06:
        folium.PolyLine(
            [(user_lat, user_lon), (node_lat, node_lon)],
            color=color,
            weight=2,
            opacity=0.7,
            dash_array="5,5",
        ).add_to(m)


def get_edge_midpoint(geom):
    try:
        gdf = gpd.GeoDataFrame(geometry=[geom], crs="EPSG:5179").to_crs("EPSG:4326")
        line = gdf.geometry.iloc[0]
        midpoint = line.interpolate(0.5, normalized=True)
        return (midpoint.y, midpoint.x)
    except Exception:
        return None


def draw_obstacle_icons(m, G, path):
    for i in range(len(path) - 1):
        u, v = (path[i], path[i + 1])
        if not G.has_edge(u, v):
            continue
        d = G[u][v]
        geom = d.get("geometry")
        pos = get_edge_midpoint(geom)
        if not pos:
            continue
        lat, lon = pos
        if d.get("crosswalk", 0):
            folium.Marker(
                [lat, lon],
                icon=folium.DivIcon(html="<div style='font-size:20px'>🚦</div>"),
                tooltip="횡단보도 (신호 대기)",
            ).add_to(m)
        if d.get("footbridge", 0):
            folium.Marker(
                [lat, lon],
                icon=folium.DivIcon(html="<div style='font-size:20px'>🌉</div>"),
                tooltip="육교 (직사광선 · 계단)",
            ).add_to(m)
        if d.get("tunnel", 0):
            folium.Marker(
                [lat, lon],
                icon=folium.DivIcon(html="<div style='font-size:20px'>🕳️</div>"),
                tooltip="터널 (매연 · 시야 저하)",
            ).add_to(m)
        if d.get("indoor", 0):
            folium.Marker(
                [lat, lon],
                icon=folium.DivIcon(html="<div style='font-size:20px'>🏬</div>"),
                tooltip="실내 보행 (그늘 100%)",
            ).add_to(m)


def render_cat_panel_large(text, mood="normal"):
    if mood == "angry":
        filename, emoji = ("cat_angry.png", "😾")
    elif mood == "thinking":
        filename, emoji = ("cat_thinking.png", "😿")
    else:
        filename, emoji = ("cat_happy.png", "😺")
    img_path = os.path.join(ASSET_DIR, filename)
    img_tag = ""
    if os.path.exists(img_path):
        b64 = get_img_as_base64(img_path)
        img_tag = f'<img src="data:image/png;base64,{b64}" style="width: 100%; height: auto; filter: drop-shadow(0px 4px 6px rgba(0,0,0,0.1));">'
    else:
        img_tag = f'<div style="font-size: 100px;">{emoji}</div>'
    html_code = f'\n    <div class="cat-panel">\n        <div style="margin-bottom: 10px;">{img_tag}</div>\n        <div style="background-color: #ffffff; padding: 16px 22px; border-radius: 25px 25px 25px 3px; border: 2px solid #E3D5F5; box-shadow: 2px 2px 8px rgba(0,0,0,0.05); position: relative; bottom: 10px;">\n        <div style="font-size: 13px; color: #9C27B0; font-weight: 700; margin-bottom: 5px;">🐈\u200d 까망이 (Shadow Cat)</div>\n        <div style="font-size: 16px; color: #424242; line-height: 1.5; font-weight: 400;">{text}</div>\n        </div>\n    </div>\n    '
    st.markdown(html_code, unsafe_allow_html=True)
