# 페르소나별 가중치 및 멘트
PERSONA_PRESETS = {
    "custom": {
        "label": "🛠️ 직접 설정",
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
