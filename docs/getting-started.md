# Getting Started


Python **3.11 이상**에서 저장소 루트를 기준으로 실행합니다.

```bash
git clone https://github.com/tangerineYR/CoolingPath.git
cd CoolingPath
python -m venv .venv
```

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
source .venv/bin/activate
```

```bash
python -m pip install -r requirements.txt
```

Kakao REST API 키를 환경변수로 설정하거나, `.streamlit/secrets.toml.example`을 `.streamlit/secrets.toml`로 복사해 본인의 키를 입력합니다. `.env.example`은 설정명 안내용이며 자동으로 로드하지 않습니다.

```powershell
# Windows PowerShell
$env:KAKAO_API_KEY = "YOUR_KAKAO_REST_API_KEY"
```

```bash
# macOS / Linux
export KAKAO_API_KEY="YOUR_KAKAO_REST_API_KEY"
```

```bash
python -m streamlit run app.py
```

출발지·도착지와 시간대를 선택해 경로를 탐색합니다. 폭염 Demo로 과거 시나리오를 확인할 수 있으며, Demo에서도 장소 검색에는 네트워크와 API 키가 필요합니다.

<details>
<summary>Docker 실행</summary>

```bash
docker build -t coolingpath .
docker run --rm -p 8501:8501 -e KAKAO_API_KEY coolingpath
```

</details>

