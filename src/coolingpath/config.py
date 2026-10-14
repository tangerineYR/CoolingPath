"""Repository-relative paths and UI presets."""

from pathlib import Path
import os

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("COOLINGPATH_DATA_DIR", ROOT_DIR / "data" / "processed"))
ASSET_DIR = ROOT_DIR / "assets" / "images"

ROUTE_COLOR_MAP = {
    "cooling": {
        "label": "❄️ 쿨링 경로",
        "color": "#00FFFF",
        "desc": "그늘과 시원함을 우선한 경로",
    },
    "shortest": {
        "label": "⏱️ 최단 경로",
        "color": "#333333",
        "desc": "이동 거리를 최소화한 경로",
    },
    "main": {
        "label": "🛣️ 큰길 우선",
        "color": "#9E9E9E",
        "desc": "넓고 안정적인 보행로 중심",
    },
    "personal": {
        "label": "🎯 나만의 경로",
        "color": "#845EF7",
        "desc": "나의 선호도를 반영한 맞춤 경로",
    },
}

PERSONA_PRESETS = {
    "custom": {
        "label": "🛠️ 직접 설정 (Custom)",
        "desc": "집사야, 원하는 대로 골라봐! (가중치 자유 조절)",
        "cw": 0.5,
        "dl": 0.2,
        "af": False,
        "at": False,
        "ai": True,
    },
    "2030": {
        "label": "🏃 2030 효율 모드",
        "desc": "적당히 시원하면서 빠른 길로 안내할게!",
        "cw": 0.5,
        "dl": 0.2,
        "af": False,
        "at": False,
        "ai": True,
    },
    "elderly": {
        "label": "👴 편안한 산책 모드 (노약자)",
        "desc": "계단은 힘들잖아. 편안한 길로 가자.",
        "cw": 0.8,
        "dl": 0.4,
        "af": True,
        "at": True,
        "ai": True,
    },
    "office": {
        "label": "💼 뽀송 출퇴근 모드 (직장인)",
        "desc": "땀 흘리기 싫지? 실내랑 지하 통로로 쏙쏙 피해 가자.",
        "cw": 0.7,
        "dl": 0.15,
        "af": False,
        "at": True,
        "ai": False,
    },
    "health": {
        "label": "❤️ 햇빛 완전 차단 모드",
        "desc": "조금 돌아가더라도 무조건! 제일 시원한 그늘로만 갈 거야.",
        "cw": 1.0,
        "dl": 0.5,
        "af": True,
        "at": True,
        "ai": False,
    },
}
