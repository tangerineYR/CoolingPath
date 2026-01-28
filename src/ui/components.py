import streamlit as st
from src.ui.styles import get_img_as_base64

# ======================================
# 캐릭터 패널 렌더링 로직
# ======================================
def render_cat_panel_large(text, mood="normal"):
    emoji_map = {"angry": "😾", "thinking": "😿", "happy": "😺", "normal": "😺"}
    img_path = f"images/cat_{mood if mood != 'normal' else 'happy'}.png"

    img_b64 = get_img_as_base64(img_path)
    img_tag = f'<img src="data:image/png;base64,{img_b64}" style="width: 100%;">' if img_b64 else f'<h1>{emoji_map[mood]}</h1>'
    
    st.markdown(f"""
    <div class="cat-panel">
        {img_tag}
        <div style="background: white; padding: 15px; border-radius: 20px; border: 2px solid #E3D5F5;">
            <small>🐈‍ 까망이</small><br><b>{text}</b>
        </div>
    </div>
    """, unsafe_allow_html=True)
