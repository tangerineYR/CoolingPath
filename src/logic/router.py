import networkx as nx
import itertools

# ======================================
# 비용 함수 로직 (쿨링/최단/큰길)
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
# 우회율 범위 내 최적 경로 탐색 함수
# ======================================
def find_constrained_best_path(G, u_node, v_node, base_path, cost_key, detour_limit=0.14, max_candidates=30):
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
