"""CoolingPath services implementation."""

import streamlit as st
import requests
import os
import math
from datetime import datetime
from zoneinfo import ZoneInfo


def search_place_kakao(query):
    api_key = os.environ.get("KAKAO_API_KEY", "")
    if not api_key:
        try:
            api_key = st.secrets.get("KAKAO_API_KEY", "")
        except FileNotFoundError:
            pass
    if not api_key:
        st.error("장소 검색 API가 설정되지 않았습니다. 관리자에게 문의해 주세요.")
        return None
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {api_key}"}
    params = {"query": query}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        response.raise_for_status()
        res = response.json()
    except (requests.RequestException, ValueError):
        st.error("장소 검색에 실패했습니다. 잠시 후 다시 시도해 주세요.")
        return None
    if not res.get("documents"):
        return None
    doc = res["documents"][0]
    return (float(doc["y"]), float(doc["x"]), doc["place_name"])


def build_hot_demo_weather():
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
    return {"raw_forecast": forecast, "mode": "hot_demo"}


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
    return {"raw_forecast": forecast, "mode": "rain_demo"}


def get_realtime_weather_forecast(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": True,
        "hourly": "temperature_2m,precipitation,relative_humidity_2m",
        "timezone": "Asia/Seoul",
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        forecast = parse_weather_forecast(response.json())
        return {"raw_forecast": forecast, "mode": "realtime"}
    except (requests.RequestException, ValueError, TypeError, KeyError):
        st.warning("기상 정보를 가져오지 못했습니다. Demo 모드를 선택해 주세요.")
        return {}


def parse_weather_forecast(payload, today=None):
    """Validate Open-Meteo hourly data before exposing it to routing/UI."""
    if not isinstance(payload, dict) or not isinstance(payload.get("hourly"), dict):
        raise ValueError("Missing hourly weather object")
    hourly = payload["hourly"]
    keys = ("time", "temperature_2m", "precipitation", "relative_humidity_2m")
    arrays = [hourly[key] for key in keys]
    if any(not isinstance(values, list) or not values for values in arrays):
        raise ValueError("Hourly fields must be nonempty arrays")
    if len({len(values) for values in arrays}) != 1:
        raise ValueError("Hourly arrays must have equal lengths")
    zone = ZoneInfo("Asia/Seoul")
    today = today or datetime.now(zone).date()
    forecast = []
    seen = set()
    for timestamp, temp, rain, humidity in zip(*arrays):
        dt = datetime.fromisoformat(timestamp)
        if dt.tzinfo is not None:
            dt = dt.astimezone(zone)
        if dt.minute or dt.second or dt.microsecond:
            raise ValueError("Weather timestamps must be hourly")
        slot = (dt.date(), dt.hour)
        if slot in seen:
            raise ValueError("Duplicate weather hour")
        seen.add(slot)
        values = (temp, rain, humidity)
        if any(isinstance(v, bool) or not isinstance(v, (int, float))
               or not math.isfinite(v) for v in values):
            raise ValueError("Weather values must be finite numbers")
        if rain < 0 or not 0 <= humidity <= 100:
            raise ValueError("Invalid precipitation or relative humidity")
        if dt.date() == today and 8 <= dt.hour <= 19:
            forecast.append({
                "time": f"{dt.hour:02d}:00", "hour": dt.hour,
                "temp": float(temp), "rain": float(rain), "humidity": float(humidity),
            })
    if not forecast:
        raise ValueError("No daytime forecast for today")
    return sorted(forecast, key=lambda row: row["hour"])


def get_env_at_time(env, time_slot):
    for f in env["raw_forecast"]:
        if f["hour"] == time_slot:
            return f
    return env["raw_forecast"][0]
