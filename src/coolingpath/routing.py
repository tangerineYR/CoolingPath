"""CoolingPath routing implementation."""

import streamlit as st
import networkx as nx
import geopandas as gpd
from scipy.spatial import KDTree
from shapely.geometry import Point
import itertools
import warnings


def build_node_index(roads_gdf):
    node_coords = {}
    for _, row in roads_gdf.iterrows():
        geom = row.geometry
        if geom.geom_type != "LineString":
            continue
        coords = list(geom.coords)
        node_coords[row["u"]] = coords[0]
        node_coords[row["v"]] = coords[-1]
    node_ids = list(node_coords.keys())
    node_xy = list(node_coords.values())
    tree = KDTree(node_xy)
    return (tree, node_ids, node_xy)


def get_nearest_node(lat, lon, tree, node_ids, node_xy):
    pt = gpd.GeoDataFrame(geometry=[Point(lon, lat)], crs="EPSG:4326").to_crs(
        "EPSG:5179"
    )
    x, y = (pt.geometry.iloc[0].x, pt.geometry.iloc[0].y)
    dist, idx = tree.query((x, y))
    return node_ids[idx]


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


@st.cache_resource
def build_base_graph_with_shadow(_roads_gdf, _shadow_df):
    G = nx.Graph()
    # Explicit simple-graph policy: shortest link, then stable link_id order.
    # Keep an audit of omitted alternatives instead of silently overwriting.
    if _roads_gdf["link_id"].duplicated().any():
        raise ValueError("Road link_id values must be unique")
    omitted = []
    rows = sorted(_roads_gdf.iterrows(),
                  key=lambda item: (float(item[1]["length"]), str(item[1]["link_id"])))
    for _, row in rows:
        if G.has_edge(row["u"], row["v"]):
            retained = G[row["u"]][row["v"]]["link_id"]
            omitted.append({"retained": retained, "omitted": row["link_id"]})
            continue
        G.add_edge(
            row["u"],
            row["v"],
            link_id=row["link_id"],
            length=row["length"],
            geometry=row.geometry,
            footbridge=row.get("footbridge", 0),
            tunnel=row.get("tunnel", 0),
            indoor=row.get("indoor", 0),
            crosswalk=row.get("crosswalk", 0),
        )
    G.graph["parallel_edge_policy"] = "minimum length, then lexical link_id"
    G.graph["omitted_parallel_links"] = omitted
    if omitted:
        warnings.warn(
            f"Parallel road policy omitted {len(omitted)} link(s); "
            "shade alternatives are not exhaustive. See graph metadata.",
            UserWarning, stacklevel=2,
        )
    attach_shadow_by_hour(G, _shadow_df)
    return G


def apply_shadow_ratio(G, time_slot, rain_mm):
    for _, _, d in G.edges(data=True):
        if rain_mm > 0:
            d["shadow_ratio"] = 0.0
        else:
            d["shadow_ratio"] = d["shadow_by_hour"][time_slot]


def is_heatwave(temp, threshold=33.0):
    return temp >= threshold


def calc_rain_penalty(rain_mm):
    if rain_mm >= 3:
        return 0.6
    elif rain_mm >= 1:
        return 0.3
    else:
        return 0.0


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


def classify_indoor_type(d):
    if not d.get("indoor", 0):
        return None
    length = d.get("length", 0)
    if length >= 60:
        return "station_or_underground"
    else:
        return "semi_indoor"


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
    return (time_penalty, fatigue_penalty)


def apply_costs(G, rain_mm=0.0):
    rain_penalty = calc_rain_penalty(rain_mm)
    for _, _, d in G.edges(data=True):
        length = float(d.get("length", 1.0))
        shadow = float(d.get("shadow_ratio", 0.0))
        tunnel = bool(d.get("tunnel", 0))
        footbridge = bool(d.get("footbridge", 0))
        indoor = bool(d.get("indoor", 0))
        total_penalty = rain_penalty + calc_facility_penalty(d, "shortest")
        d["cost_walkability"] = length * (1 + total_penalty)
        is_main = length >= 100 and (not tunnel) and (not footbridge) and (not indoor)
        main_factor = 1.0 if is_main else 1.5
        total_penalty = rain_penalty + calc_facility_penalty(d, "main")
        d["cost_main"] = length * main_factor * (1 + total_penalty)
        heat_penalty = (1 - shadow) * 2.0
        _, fatigue_penalty = calc_indoor_penalty(d)
        cooling_penalty = heat_penalty + fatigue_penalty
        total_penalty = rain_penalty + calc_facility_penalty(d, "cooling")
        d["cost_cooling"] = length * (1 + cooling_penalty + total_penalty)


def apply_personal_costs(G, rain_mm, pref):
    cw = pref["cooling_weight"]
    for _, _, d in G.edges(data=True):
        length = float(d.get("length", 1.0))
        shadow = float(d.get("shadow_ratio", 0.0))
        tunnel = bool(d.get("tunnel", 0))
        footbridge = bool(d.get("footbridge", 0))
        indoor = bool(d.get("indoor", 0))
        rain_penalty = calc_rain_penalty(rain_mm)
        facility_penalty = 0.0
        if pref["avoid_tunnel"] and tunnel:
            facility_penalty += 0.6
        if pref["avoid_footbridge"] and footbridge:
            facility_penalty += 0.4
        if pref["avoid_indoor"] and indoor:
            facility_penalty += 0.5
        heat_penalty = (1 - shadow) * 2.0 * cw
        time_penalty = 1 - cw
        d["cost_personal"] = length * (
            1 + heat_penalty + time_penalty + rain_penalty + facility_penalty
        )


def find_constrained_best_path(
    G, u_node, v_node, base_path, cost_key, detour_limit=0.14, max_candidates=30
):
    base_length = nx.path_weight(G, base_path, "length")
    max_length = base_length * (1 + detour_limit)
    path_gen = nx.shortest_simple_paths(G, u_node, v_node, weight=cost_key)
    best_path = None
    best_cost = float("inf")
    for path in itertools.islice(path_gen, max_candidates):
        path_length = nx.path_weight(G, path, "length")
        if path_length > max_length:
            continue
        cost = nx.path_weight(G, path, cost_key)
        if cost < best_cost:
            best_cost = cost
            best_path = path
    return best_path if best_path else base_path
