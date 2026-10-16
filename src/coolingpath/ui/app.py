"""CoolingPath ui.app implementation."""

import streamlit as st
import folium
from streamlit_folium import st_folium
import time
import networkx as nx
import os
import pandas as pd
import copy
import altair as alt
from coolingpath.data import load_roads, load_shade_shelters, load_shadow_data
from coolingpath.services import (
    build_hot_demo_weather,
    build_rain_demo_weather,
    get_env_at_time,
    get_realtime_weather_forecast,
    search_place_kakao,
)
from coolingpath.routing import (
    apply_costs,
    apply_personal_costs,
    apply_shadow_ratio,
    build_base_graph_with_shadow,
    build_node_index,
    find_constrained_best_path,
    get_nearest_node,
    is_heatwave,
)
from coolingpath.metrics import (
    build_forecast_for_graph,
    calc_avg_shadow,
    calculate_kpis,
    calculate_route_grade,
    count_obstacles,
)
from coolingpath.ui.components import (
    build_kpi_story,
    draw_marker_and_connector,
    draw_obstacle_icons,
    draw_path_layer,
    get_grade_label,
    get_img_as_base64,
    render_cat_panel_large,
    render_kpi_card,
    render_multi_route_summary,
    render_obstacle_badges,
    render_route_legend,
)
from coolingpath.config import PERSONA_PRESETS, ASSET_DIR


def main():
    st.set_page_config(
        page_title="태·피·소 - 까망이의 태양 피하기 소동",
        layout="wide",
        page_icon=str(ASSET_DIR / "logo.png")
        if os.path.exists(str(ASSET_DIR / "logo.png"))
        else "🐈\u200d⬛",
    )
    if os.path.exists(str(ASSET_DIR / "logo.png")):
        title_img_path = str(ASSET_DIR / "logo.png")
    elif os.path.exists(str(ASSET_DIR / "cat_happy.png")):
        title_img_path = str(ASSET_DIR / "cat_happy.png")
    else:
        title_img_path = None
    if title_img_path:
        logo_b64 = get_img_as_base64(title_img_path)
        st.markdown(
            f'\n    <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 10px;">\n        <img src="data:image/png;base64,{logo_b64}" style="width: 50px; height: 50px; border-radius: 10px;">\n        <h1 style="margin: 0; padding: 0; color: #333; font-size: 38px;">태·피·소 - 까망이의 태양 피하기 소동</h1>\n    </div>\n    ',
            unsafe_allow_html=True,
        )
    else:
        st.title("🐈\u200d 태·피·소 - 까망이의 태양 피하기 소동")
    st.caption("햇빛은 피하고, 시원함만 밟고 가자! AI 고양이 까망이의 산책 네비게이션")
    st.markdown(
        '\n<style>\n    /* 1. 전체 배경 및 폰트 (크림 화이트) */\n    .stApp {\n        background-color: #FDFBF7;\n        font-family: \'Apple SD Gothic Neo\', \'Malgun Gothic\', sans-serif;\n    }\n\n    /* [NEW] 상단 헤더(햄버거 메뉴 라인) 배경색 통일 */\n    [data-testid="stHeader"] {\n        background-color: #FDFBF7;\n    }\n\n    /* 2. 메인 컨테이너 여백 조정 (제목 잘림 방지) */\n    .block-container {\n        padding-top: 6rem; /* 기존 2rem에서 늘림 */\n        padding-bottom: 5rem;\n    }\n\n    /* 3. 카드(Card) 스타일 */\n    .css-card {\n        background-color: #FFFFFF;\n        border-radius: 20px;\n        padding: 20px;\n        box-shadow: 0 4px 15px rgba(0,0,0,0.05);\n        margin-bottom: 20px;\n        border: 1px solid #F0F0F0;\n    }\n\n    /* 4. 라디오 버튼 아래 불필요한 여백 제거 */\n    div[role="radiogroup"] {\n        margin-bottom: -10px;\n    }\n\n    /* 5. 버튼 스타일 */\n    .stButton>button {\n        background-color: #7E57C2;\n        color: white;\n        border-radius: 15px;\n        border: none;\n        height: 50px;\n        font-weight: bold;\n        width: 100%;\n        transition: all 0.3s;\n        box-shadow: 0 4px 6px rgba(126, 87, 194, 0.3);\n    }\n    .stButton>button:hover {\n        background-color: #673AB7;\n        transform: translateY(-2px);\n    }\n\n    /* 6. 사이드바 스타일 */\n    [data-testid="stSidebar"] {\n        background-color: #F8F9FA;\n        border-right: 1px solid #E9ECEF;\n    }\n</style>\n',
        unsafe_allow_html=True,
    )
    if "route_ready" not in st.session_state:
        st.session_state.route_ready = False
    if "route_result" not in st.session_state:
        st.session_state.route_result = None
    if "selected_persona" not in st.session_state:
        st.session_state.selected_persona = "custom"
    with st.sidebar:
        st.header("📍 경로 설정")
        start_query = st.text_input("출발지", "역삼역 8번 출구")
        end_query = st.text_input("도착지", "KT플라자 강남점")
        st.divider()
        st.subheader("🕒 시간대 설정")
        time_slot = st.slider(
            "보행 시작 시간", min_value=8, max_value=19, value=14, step=1, format="%d시"
        )
        st.divider()
        st.subheader("🎯 퍼스널 경로 설정")
        use_personal_mode = st.toggle(
            "퍼스널 모드 사용",
            value=False,
            help="나만의 선호도에 따라 경로를 추천합니다.",
        )
        st.session_state.use_personal_mode = use_personal_mode
        if use_personal_mode != st.session_state.get("use_personal_mode_prev", False):
            st.session_state.personal_route_ready = False
        st.session_state.use_personal_mode_prev = use_personal_mode
        if use_personal_mode:
            persona_key = st.selectbox(
                "나에게 맞는 모드 선택",
                options=list(PERSONA_PRESETS.keys()),
                format_func=lambda x: PERSONA_PRESETS[x]["label"],
            )
            preset = PERSONA_PRESETS[persona_key]
            st.session_state.selected_persona = persona_key
            st.caption(f"💡 {preset['desc']}")
            is_disabled = persona_key != "custom"
            cooling_weight = st.slider(
                "❄️ 시원함 선호도", 0.0, 1.0, preset["cw"], 0.1, disabled=is_disabled
            )
            detour_limit = st.slider(
                "📏 최대 우회 허용", 0.0, 1.0, preset["dl"], 0.1, disabled=is_disabled
            )
            c1, c2, c3 = st.columns(3)
            avoid_footbridge = c1.checkbox(
                "육교 피하기", value=preset["af"], disabled=is_disabled
            )
            avoid_tunnel = c2.checkbox(
                "터널 피하기", value=preset["at"], disabled=is_disabled
            )
            avoid_indoor = c3.checkbox(
                "실내 피하기", value=preset["ai"], disabled=is_disabled
            )
            st.session_state.personal_pref = {
                "cooling_weight": cooling_weight,
                "detour_limit": detour_limit,
                "avoid_footbridge": avoid_footbridge,
                "avoid_tunnel": avoid_tunnel,
                "avoid_indoor": avoid_indoor,
            }
        submit = st.button("경로 탐색", type="primary")
        st.divider()
        st.subheader("🌡️ 기상 시나리오 선택")
        weather_mode = st.radio(
            "기온 데이터 모드", ["실시간", "폭염 (demo)", "폭염 + 강수 (demo)"], index=0
        )
        st.session_state.weather_mode = weather_mode
    roads_gdf = load_roads()
    shadow_df = load_shadow_data()
    shade_shelters_df = load_shade_shelters()
    base_G = build_base_graph_with_shadow(roads_gdf, shadow_df)
    if base_G.graph.get("omitted_parallel_links"):
        st.caption(
            "같은 두 지점을 잇는 도로는 가장 짧은 링크를 대표로 사용합니다. "
            "일부 평행 도로의 그늘 대안은 비교에서 제외됩니다."
        )
    node_tree, node_ids, node_xy = build_node_index(roads_gdf)
    if submit:
        st.session_state.is_loading = True
        st.session_state.last_submit_time = time.time()
        start = search_place_kakao(start_query)
        end = search_place_kakao(end_query)
        if not start or not end:
            st.error("출발지 또는 도착지를 찾을 수 없습니다.")
            st.stop()
        start_lat, start_lon, start_name = start
        end_lat, end_lon, end_name = end
        u_node = get_nearest_node(start_lat, start_lon, node_tree, node_ids, node_xy)
        v_node = get_nearest_node(end_lat, end_lon, node_tree, node_ids, node_xy)
        new_input = {
            "start": {
                "name": start_name,
                "lat": start_lat,
                "lon": start_lon,
                "node": u_node,
            },
            "end": {"name": end_name, "lat": end_lat, "lon": end_lon, "node": v_node},
            "time_slot": time_slot,
        }
        if st.session_state.get("route_input") != new_input:
            st.session_state.route_result = None
        st.session_state.route_input = new_input
        mode = st.session_state.weather_mode
        if mode == "실시간":
            env = get_realtime_weather_forecast(start_lat, start_lon)
        elif mode == "폭염 (demo)":
            env = build_hot_demo_weather()
        elif mode == "폭염 + 강수 (demo)":
            env = build_rain_demo_weather()
        st.session_state.env = env
        if not env.get("raw_forecast"):
            st.session_state.is_loading = False
            st.error(
                "기상 정보를 가져오지 못했습니다. Demo 모드를 선택하거나 다시 시도해 주세요."
            )
            st.stop()
        env_at_time = get_env_at_time(env, time_slot)
        G = copy.deepcopy(base_G)
        rain_mm = env_at_time["rain"]
        apply_shadow_ratio(G, time_slot, rain_mm)
        apply_costs(G, rain_mm=rain_mm)
        if st.session_state.use_personal_mode:
            apply_personal_costs(G, rain_mm, st.session_state.personal_pref)
        path_shortest = nx.shortest_path(G, u_node, v_node, weight="length")
        path_cooling = nx.shortest_path(G, u_node, v_node, weight="cost_cooling")
        path_main = nx.shortest_path(G, u_node, v_node, weight="cost_main")
        if st.session_state.use_personal_mode:
            detour_limit = st.session_state.personal_pref.get("detour_limit", 0.2)
            path_personal = find_constrained_best_path(
                G,
                u_node,
                v_node,
                base_path=path_shortest,
                cost_key="cost_personal",
                detour_limit=detour_limit,
            )
        else:
            path_personal = None
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
        if path_personal is not None:
            avg_shadow["personal"] = calc_avg_shadow(G, path_personal)
        st.session_state.avg_shadow = avg_shadow
        base_temp = env_at_time["temp"]
        heatwave = is_heatwave(base_temp)
        st.session_state.heatwave = {"active": heatwave, "temp": base_temp}
        st.session_state.route_ready = True
        st.session_state.personal_route_ready = st.session_state.use_personal_mode
        st.session_state.is_loading = False
    if st.session_state.get("is_loading"):
        st.markdown(
            '\n        <div style="\n            background:#EEF6FF;\n            border-left:6px solid #339AF0;\n            padding:12px 16px;\n            border-radius:8px;\n            margin-bottom:12px;\n            font-weight:600;\n        ">\n        🔄 경로를 다시 계산하고 있어요…<br>\n        <span style="font-weight:400">\n        날씨·시간·보행 환경을 반영 중입니다.\n        </span>\n        </div>\n        ',
            unsafe_allow_html=True,
        )
    if st.session_state.get("route_ready") and (not st.session_state.get("is_loading")):
        s = st.session_state.route_input["start"]
        e = st.session_state.route_input["end"]
        center = [(s["lat"] + e["lat"]) / 2, (s["lon"] + e["lon"]) / 2]
        result = st.session_state.route_result
        G = result["graph"]
        paths = result["paths"]
        path_shortest = paths.get("shortest")
        path_cooling = paths.get("cooling")
        path_main = paths.get("main")
        path_personal = paths.get("personal")
        env_at_time = get_env_at_time(st.session_state.env, time_slot)
        rain_mm = env_at_time["rain"]
        heatwave = st.session_state.get("heatwave", {}).get("active", False)
        if heatwave and rain_mm == 0:
            default_view = "❄️ 쿨링 경로"
        else:
            default_view = "🔍 모든 경로 비교"
        view_options = [
            "🔍 모든 경로 비교",
            "❄️ 쿨링 경로",
            "⏱️ 최단 경로",
            "🛣️ 큰길 우선",
        ]
        if st.session_state.get("use_personal_mode"):
            view_options.insert(1, "🎯 나만의 경로")
            default_view = "🎯 나만의 경로"
        if default_view not in view_options:
            default_view = view_options[0]
        st.markdown("### 🗺️ 경로 지도")
        if heatwave and rain_mm == 0:
            st.markdown(
                f"""\n          <div style="background-color:#FFE5E5; border-left:6px solid #FF4B4B; padding:12px 16px; border-radius:8px; margin-bottom:12px; font-weight:600;">\n          🔥 으악! 지금 밖은 찜통이야! ({st.session_state.heatwave["temp"]:.1f}℃)<br>\n          <span style="font-weight:400"><b>쿨링패스</b>로 안 가면 큰일 난다냥! 🐾</span>\n          </div>\n          """,
                unsafe_allow_html=True,
            )
        if rain_mm > 0:
            st.markdown(
                f'\n          <div style="background-color:#E3FAFC; border-left:6px solid #15AABF; padding:12px 16px; border-radius:8px; margin-bottom:12px; font-weight:600;">\n          ☔ 비가 오고 있어! (강수량 {rain_mm}mm)<br>\n          <span style="font-weight:400">우산을 쓰니까 <b>그늘은 신경 안 써도 돼.</b> 대신 미끄러지지 않게 조심!</span>\n          </div>\n          ',
                unsafe_allow_html=True,
            )
        view_mode = st.radio(
            "지도 보기 모드",
            view_options,
            index=view_options.index(default_view),
            horizontal=True,
            label_visibility="collapsed",
        )
        if rain_mm > 0:
            target_key = "shortest"
        elif view_mode == "🔍 모든 경로 비교":
            target_key = None
        else:
            target_key = {
                "❄️ 쿨링 경로": "cooling",
                "⏱️ 최단 경로": "shortest",
                "🛣️ 큰길 우선": "main",
                "🎯 나만의 경로": "personal",
            }[view_mode]
        target_path = paths.get(target_key)
        kpi = calculate_kpis(
            G,
            paths["shortest"],
            target_path if target_path else paths["cooling"],
            env_at_time["temp"],
            rain_mm,
            env_at_time["humidity"],
        )
        grade_info = calculate_route_grade(
            kpi,
            mode=target_key if target_key else "cooling",
            pref=st.session_state.get("personal_pref"),
        )
        grade = grade_info["grade"]
        if target_key:
            st.markdown(
                f"\n        <div style='background:#f8f9fa; border-radius:10px; padding:10px; margin-top:10px; text-align:center;'>\n          <div style='font-size:12px; color:#888;'>선택 경로 등급</div>\n          <div style='font-size:24px; font-weight:bold; color:#7E57C2;'>{grade} <span style='font-size:14px;'>({grade_info['score']}점)</span></div>\n        </div>\n        ",
                unsafe_allow_html=True,
            )
        col_map, col_cat = st.columns([2, 1], gap="medium")
        with col_map:
            if view_mode == "🔍 모든 경로 비교":
                render_route_legend(
                    show_personal=st.session_state.get("use_personal_mode", False)
                )
            m = folium.Map(location=center, zoom_start=16.5)
            folium.TileLayer(
                tiles="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
                attr="CARTO",
                name="Gray",
                control=False,
            ).add_to(m)
            if view_mode == "🔍 모든 경로 비교":
                draw_path_layer(
                    m,
                    G,
                    path_main,
                    color="#9E9E9E",
                    weight=5,
                    opacity=0.85,
                    tooltip="큰길 우선",
                )
                draw_path_layer(
                    m,
                    G,
                    path_shortest,
                    color="#333333",
                    weight=6,
                    opacity=0.9,
                    tooltip="최단 경로",
                )
                cool_color = "#00FFFF" if rain_mm == 0 else "#15AABF"
                draw_path_layer(
                    m,
                    G,
                    path_cooling,
                    color=cool_color,
                    weight=8,
                    opacity=1.0,
                    tooltip="쿨링 경로",
                )
                if path_personal:
                    draw_path_layer(
                        m,
                        G,
                        path_personal,
                        color="#845EF7",
                        weight=7,
                        opacity=0.95,
                        tooltip="나만의 경로",
                    )
            elif target_key and target_path:
                is_grad = rain_mm == 0
                color = (
                    None
                    if is_grad
                    else "#15AABF"
                    if target_key == "cooling"
                    else "#333333"
                )
                draw_path_layer(
                    m,
                    G,
                    target_path,
                    weight=9,
                    opacity=0.95,
                    is_gradient=is_grad,
                    color=color,
                )
                draw_obstacle_icons(m, G, target_path)
            if not shade_shelters_df.empty:
                for _, row in shade_shelters_df.iterrows():
                    folium.Marker(
                        [row["위도"], row["경도"]],
                        icon=folium.Icon(color="green", icon="umbrella", prefix="fa"),
                        tooltip="⛱️ 그늘막",
                    ).add_to(m)
            draw_marker_and_connector(
                m,
                s["lat"],
                s["lon"],
                node_xy[node_ids.index(s["node"])],
                popup=f"출발: {s['name']}",
                color="green",
            )
            draw_marker_and_connector(
                m,
                e["lat"],
                e["lon"],
                node_xy[node_ids.index(e["node"])],
                popup=f"도착: {e['name']}",
                color="red",
            )
            st_folium(m, height=600, use_container_width=True)
        with col_cat:
            comment, mood = ("", "normal")
            if rain_mm > 0:
                comment = "비가 와서 그늘은 소용없어. ☔<br>대신 미끄러지지 않게 조심해서 걷자냥!"
                mood = "thinking"
            elif target_key == "personal":
                pk = st.session_state.get("selected_persona", "custom")
                if pk == "health":
                    comment = "햇빛을 피해 제일 안전한 길로 골랐어.<br>건강이 최고니까!"
                else:
                    comment, mood = (
                        "집사가 원한 딱 그 길이야!<br>얼른 가보자냥 🐾",
                        "happy",
                    )
            if not comment:
                if grade == "A":
                    comment, mood = (
                        "완벽해! 발바닥이 하나도 안 뜨거운<br>최고의 그늘길이야. 🐾",
                        "happy",
                    )
                elif grade == "B":
                    comment, mood = (
                        "나쁘지 않아.<br>적당히 시원하게 걸을 수 있겠어.",
                        "normal",
                    )
                elif grade == "C":
                    comment, mood = (
                        "음... 조금 애매한데?<br>땀이 좀 날 수도 있겠다.",
                        "thinking",
                    )
                else:
                    comment, mood = (
                        "으아, 여긴 털 탈 것 같아! 🔥<br>너무 뜨거우니까 다른 길로 가자.",
                        "angry",
                    )
            render_cat_panel_large(comment, mood)
        if (
            st.session_state.use_personal_mode
            and (not st.session_state.personal_route_ready)
            and (target_key == "personal")
        ):
            st.info(
                "사이드바에서 집사가 원하는 모드로 설정해줘! 내가 딱 맞는 경로를 추천해줄게."
            )
        elif target_key:
            title_map = {
                "cooling": "❄️ 쿨링 경로 분석",
                "shortest": "⏱️ 최단 경로 분석",
                "main": "🛣️ 큰길 경로 분석",
                "personal": "🎯 나만의 경로 분석",
            }
            st.markdown(f"### {title_map[target_key]}")
            kpi_story = build_kpi_story(kpi)
            comment, mood = ("", "normal")
            if rain_mm > 0:
                comment = "비가 와서 그늘은 소용없어. ☔ 대신 미끄러지지 않게 조심해서 걷자냥!"
                mood = "thinking"
            elif target_key == "personal":
                pk = st.session_state.get("selected_persona", "custom")
                if pk == "elderly" and grade in ["A", "B"]:
                    comment, mood = (
                        "경사가 완만하고 그늘이 많아서 걷기 편해. 천천히 다녀와!",
                        "happy",
                    )
                elif pk == "office":
                    comment, mood = (
                        "이 정도면 셔츠 젖을 걱정은 없겠다. 쾌적하게 가자!",
                        "happy",
                    )
                elif pk == "health":
                    comment = "햇빛을 피해 제일 안전한 길로 골랐어. 건강이 최고니까!"
            if not comment:
                if grade == "A":
                    comment, mood = (
                        "완벽해! 발바닥이 하나도 안 뜨거운 최고의 그늘길이야. 🐾",
                        "happy",
                    )
                elif grade == "B":
                    comment, mood = (
                        "나쁘지 않아. 적당히 시원하게 걸을 수 있겠어.",
                        "normal",
                    )
                elif grade == "C":
                    comment, mood = (
                        "음... 조금 애매한데? 땀이 좀 날 수도 있겠다.",
                        "thinking",
                    )
                else:
                    comment, mood = (
                        "으아, 여긴 털 탈 것 같아! 🔥 너무 뜨거우니까 다른 길로 가자.",
                        "angry",
                    )
            if rain_mm == 0:
                grade_label = get_grade_label(view_mode)
                st.markdown(
                    f"""\n                <div style="display:inline-block; padding:6px 14px; border-radius:20px; background:#E3FAFC; color:#0B7285; font-weight:700; margin-bottom:15px;">\n                {grade_label} {grade_info["grade"]} · {grade_info["score"]}점\n                </div>\n                """,
                    unsafe_allow_html=True,
                )
            c1, c2, c3, c4, c5 = st.columns(5)
            render_kpi_card(
                c1,
                "📏 이동 거리",
                f"{kpi['length']['target']:.0f}m",
                f"{abs(kpi['length']['detour_ratio'] * 100):.1f}%",
                False,
                story_text=kpi_story["detour"]["text"],
                story_tone=kpi_story["detour"]["tone"],
            )
            render_kpi_card(
                c2,
                "⏱ 소요시간",
                f"{kpi['time']['target'] / 60:.1f}분",
                f"{abs(kpi['time']['time_ratio'] * 100):.1f}%",
                False,
                story_text=kpi_story["time"]["text"],
                story_tone=kpi_story["time"]["tone"],
            )
            render_kpi_card(
                c3,
                "🌳 그늘확보",
                f"{kpi['shadow']['target'] * 100:.1f}%",
                f"{abs(kpi['shadow']['gain'] * 100):.1f}%p",
                True,
                story_text=kpi_story["shadow"]["text"],
                story_tone=kpi_story["shadow"]["tone"],
            )
            render_kpi_card(
                c4,
                "🌡 그늘 보정 온도",
                f"{kpi['temperature']['target']:.1f}℃",
                f"{abs(kpi['temperature']['diff']):.1f}℃",
                False,
                story_text=kpi_story["temperature"]["text"],
                story_tone=kpi_story["temperature"]["tone"],
            )
            hum = kpi["humidity"]
            h_label = hum["label"]
            h_pos = h_label in ["쾌적", "보통"]
            h_emoji = {"쾌적": "😊", "보통": "🙂", "높음": "😓", "매우 높음": "🥵"}[
                h_label
            ]
            render_kpi_card(
                c5,
                "💧 습도",
                f"{hum['value']:.0f}%",
                f"{h_emoji} {h_label}",
                h_pos,
                True,
                story_text=kpi_story["humidity"]["text"],
                story_tone=kpi_story["humidity"]["tone"],
            )
            obs = count_obstacles(G, target_path)
            render_obstacle_badges(obs)
        else:
            render_multi_route_summary(
                paths,
                G,
                st.session_state.env,
                time_slot,
                st.session_state.get("personal_pref"),
            )
        if target_key and "env" in st.session_state:
            st.markdown("---")
            st.markdown("### 🌡 시간대별 기온 예보 & 그늘 보정 온도 (08~19시)")
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
                    st.info(
                        f"⏳ {max_hour - time_slot:.0f}시간 뒤에 제일 뜨거워져! 얼른 움직이자! 🐾"
                    )
                elif time_slot > max_hour:
                    st.info("🌆 더위가 좀 가라앉았네! 아까보단 걷기 편할 거야.")
                else:
                    st.info(
                        "🔥 으악! 지금이 **제일 더운 시간**이야. 꼭 쿨링 경로로 가야 해!"
                    )
                y_min = df[["temp", "shade_adjusted_temp"]].min().min() - 1
                y_max = df[["temp", "shade_adjusted_temp"]].max().max() + 1
                base = alt.Chart(df.reset_index()).encode(
                    x=alt.X("hour:O", title="시간")
                )
                line_temp = base.mark_line(color="#FF6B6B").encode(
                    y=alt.Y(
                        "temp:Q",
                        scale=alt.Scale(domain=[y_min, y_max]),
                        title="기온(℃)",
                    )
                )
                line_shade = base.mark_line(color="#339AF0").encode(
                    y=alt.Y("shade_adjusted_temp:Q", title="그늘 보정 온도(℃)")
                )
                vline = (
                    alt.Chart(pd.DataFrame({"hour": [time_slot]}))
                    .mark_rule(color="black", strokeDash=[4, 4])
                    .encode(x="hour:O")
                )
                peak_point = (
                    alt.Chart(pd.DataFrame({"hour": [max_hour], "temp": [max_temp]}))
                    .mark_point(size=160, filled=True, color="#FF6B6B")
                    .encode(x="hour:O", y="temp:Q")
                )
                peak_label = (
                    alt.Chart(
                        pd.DataFrame(
                            {
                                "hour": [max_hour],
                                "temp": [max_temp],
                                "label": [f"🔥 최고 {max_temp:.1f}℃"],
                            }
                        )
                    )
                    .mark_text(dy=-18, fontSize=14, fontWeight="bold", color="#C92A2A")
                    .encode(x="hour:O", y="temp:Q", text="label")
                )
                chart = (
                    line_temp + line_shade + vline + peak_point + peak_label
                ).properties(height=400, background="#FDFBF7")
                st.altair_chart(chart, use_container_width=True)
                st.caption(f"🌡️ {max_hour:.0f}시에 최고기온 {max_temp:.1f}℃ 예상됩니다.")
                st.caption("그늘 보정 온도 = 기온 − 평균 그늘 비율 × 5℃인 가정 기반 지표입니다. Heat Index·WBGT·UTCI가 아니며, 시간별 그늘 변화는 반영하지 않습니다.")
            else:
                st.info("기온 예보 데이터를 불러올 수 없습니다.")
    else:
        c1, c2 = st.columns([1, 1.5])
        with c1:
            if os.path.exists(str(ASSET_DIR / "cat_happy.png")):
                st.image(str(ASSET_DIR / "cat_happy.png"), use_container_width=True)
            else:
                st.markdown(
                    "<div style='font-size:150px; text-align:center;'>🐈\u200d</div>",
                    unsafe_allow_html=True,
                )
        with c2:
            st.markdown(
                "\n        <div style='margin-top: 30px;'>\n            <div style=\"display: flex; align-items: center; gap: 15px; margin-bottom: 10px;\">\n                <img src=\"data:image/png;base64,{}\" style=\"width: 55px; height: 55px; border-radius: 10px; display: {};\"> \n                <h1 style='color:#333; margin:0; font-size:42px;'>태·피·소 🐾</h1>\n            </div>\n            <h3 style='color:#7E57C2; margin-top:10px; font-weight:700;'>까망이의 <span style='color:#FF6B6B'>태</span>양 <span style='color:#339AF0'>피</span>하기 <span style='color:#51CF66'>소</span>동!</h3>\n            <p style='font-size:18px; color:#666; line-height:1.6;'>\n                \"큰일 났다냥! 밖은 지금 용광로야! 🔥<br>\n                나랑 같이 <b>가장 시원한 대피소(그늘 길)</b>로 도망가자.<br>\n                내 발자국만 따라오면 절대 타지 않는다냥!\"\n            </p>\n            <br>\n            <div style='background:#F1F3F5; padding:20px; border-radius:15px; color:#555; border:1px solid #E9ECEF;'>\n                🚨 <b>작전 개시 방법</b><br>\n                👈 왼쪽에서 <b>출발지와 목적지</b>를 입력하고 <b>[경로 탐색]</b>을 눌러라 냥!\n            </div>\n        </div>\n        ".format(
                    get_img_as_base64(str(ASSET_DIR / "logo.png"))
                    if os.path.exists(str(ASSET_DIR / "logo.png"))
                    else "",
                    "block" if os.path.exists(str(ASSET_DIR / "logo.png")) else "none",
                ),
                unsafe_allow_html=True,
            )
