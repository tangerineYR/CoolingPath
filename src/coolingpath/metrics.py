"""CoolingPath metrics implementation."""

import networkx as nx
from coolingpath.routing import calc_indoor_penalty


def build_forecast_for_graph(env, avg_shadow, time_slot):
    graph_data = []
    for f in env["raw_forecast"]:
        base = f["temp"]
        feels = base - avg_shadow * 5.0
        graph_data.append(
            {
                "time": f["time"],
                "hour": f["hour"],
                "temp": base,
                "feels_like": round(feels, 1),
                "rain": f["rain"],
                "humidity": f["humidity"],
            }
        )
    return graph_data


def calc_path_length(G, path):
    return nx.path_weight(G, path, weight="length")


def calc_avg_shadow(G, path):
    if not path or len(path) < 2:
        return 0.0
    total_len = 0.0
    shadow_sum = 0.0
    for i in range(len(path) - 1):
        u, v = (path[i], path[i + 1])
        d = G[u][v]
        length = float(d.get("length", 0.0))
        shadow = float(d.get("shadow_ratio", 0.0))
        total_len += length
        shadow_sum += length * shadow
    return shadow_sum / total_len if total_len > 0 else 0.0


def calc_edge_time(d, base_speed=1.2, rain_mm=0.0):
    length = float(d.get("length", 0.0))
    time_sec = length / base_speed
    indoor_time, _ = calc_indoor_penalty(d)
    time_sec += indoor_time
    if d.get("crosswalk", 0):
        time_sec += 30
    if d.get("footbridge", 0):
        time_sec += 20
    if rain_mm >= 3:
        time_sec *= 1.15
    elif rain_mm >= 1:
        time_sec *= 1.08
    return time_sec


def calc_path_time(G, path, rain_mm=0.0):
    total_time = 0.0
    for i in range(len(path) - 1):
        u, v = (path[i], path[i + 1])
        d = G[u][v]
        total_time += calc_edge_time(d, rain_mm=rain_mm)
    return total_time


def calc_humidity_discomfort(humidity):
    if humidity >= 85:
        return (3, "매우 높음")
    elif humidity >= 75:
        return (2, "높음")
    elif humidity >= 65:
        return (1, "보통")
    else:
        return (0, "쾌적")


def count_obstacles(G, path):
    counts = {"crosswalk": 0, "footbridge": 0, "tunnel": 0, "indoor": 0}
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


def calculate_kpis(G, path_shortest, path_target, base_temp, rain_mm, humidity):
    len_short = calc_path_length(G, path_shortest)
    len_target = calc_path_length(G, path_target)
    detour_ratio = (len_target - len_short) / len_short
    time_short = calc_path_time(G, path_shortest, rain_mm)
    time_target = calc_path_time(G, path_target, rain_mm)
    time_ratio = (time_target - time_short) / time_short
    shadow_short = calc_avg_shadow(G, path_shortest)
    shadow_target = calc_avg_shadow(G, path_target)
    shadow_gain = shadow_target - shadow_short
    temp_short = base_temp - shadow_short * 5.0
    temp_target = base_temp - shadow_target * 5.0
    temp_diff = temp_target - temp_short
    humidity_score, humidity_label = calc_humidity_discomfort(humidity)
    obstacles = count_obstacles(G, path_target)
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


def score_detour(detour_ratio):
    if detour_ratio <= 0.1:
        return 100
    elif detour_ratio <= 0.14:
        return 80
    elif detour_ratio <= 0.2:
        return 60
    else:
        return 30


def score_time(time_ratio):
    if time_ratio <= 0.05:
        return 100
    elif time_ratio <= 0.1:
        return 80
    elif time_ratio <= 0.2:
        return 60
    else:
        return 30


def score_shadow(shadow_gain):
    if shadow_gain >= 0.2:
        return 100
    elif shadow_gain >= 0.1:
        return 80
    elif shadow_gain >= 0.05:
        return 60
    else:
        return 30


def score_cooling(temp_diff):
    if temp_diff <= -2.0:
        return 100
    elif temp_diff <= -1.0:
        return 80
    elif temp_diff <= -0.5:
        return 60
    else:
        return 30


def calculate_route_grade(kpi, mode="cooling", pref=None):
    s_cool = score_cooling(kpi["temperature"]["diff"])
    s_shadow = score_shadow(kpi["shadow"]["gain"])
    s_detour = score_detour(kpi["length"]["detour_ratio"])
    s_time = score_time(kpi["time"]["time_ratio"])
    if mode == "cooling":
        w = dict(cool=0.35, shadow=0.3, detour=0.2, time=0.15)
    elif mode == "shortest":
        w = dict(cool=0.15, shadow=0.1, detour=0.35, time=0.4)
    elif mode == "main":
        w = dict(cool=0.2, shadow=0.15, detour=0.25, time=0.25)
    elif mode == "personal" and pref:
        cw = pref["cooling_weight"]
        w = dict(
            cool=0.15 + 0.4 * cw,
            shadow=0.15 + 0.3 * cw,
            detour=0.35 * (1 - cw),
            time=0.35 * (1 - cw),
        )
    total = (
        s_cool * w["cool"]
        + s_shadow * w["shadow"]
        + s_detour * w["detour"]
        + s_time * w["time"]
    )
    grade = "A" if total >= 85 else "B" if total >= 70 else "C" if total >= 55 else "D"
    return {"score": round(total, 1), "grade": grade}
