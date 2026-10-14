# Architecture

`app.py`는 Streamlit 진입점이며 `src/coolingpath/ui/app.py`가 화면과 사용자 흐름을 구성합니다.

| 모듈 | 책임 |
| --- | --- |
| `config.py` | 저장소 기준 경로·페르소나·색상 설정 |
| `data.py` | 도로·그늘 통계·그늘막 로딩 |
| `services.py` | Kakao 장소 검색·Open-Meteo·Demo 기상 |
| `routing.py` | 노드 인덱스·그래프·비용·제약 경로 탐색 |
| `metrics.py` | 길이 가중 그늘 비율·시간·KPI·등급 |
| `ui/components.py` | 지도·카드·캐릭터 렌더링 |

전처리 단계에서 생성된 그늘 통계를 실행 시 도로 그래프에 결합합니다. 탐색 그래프에도 도로 형상은 포함됩니다. 분리 대상은 그림자 Polygon이며, 모든 형상 정보를 제거한 그래프는 아닙니다.

기존 `docs/diagrams/`의 Mermaid 원문과 `docs/assets/CoolingPath_*` 이미지는 인턴 당시 설계 기록입니다. 시간 +14% 필터 등 과거 기획은 현재 구현과 차이가 있습니다. 현재 일반 쿨링 경로는 가중 최단 경로, 개인화 경로는 거리 제한 내 후보 탐색을 사용합니다.
