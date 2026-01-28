import base64
import os

# 이미지를 HTML에서 쓸 수 있게 텍스트로 변환
def get_img_as_base64(file_path):
    if not os.path.exists(file_path): return None
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# UI 스타일 시트
MAIN_STYLE = """
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
"""
