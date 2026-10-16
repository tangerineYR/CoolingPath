# 레이어 목록과 정리 내역

정리본은 네 레이어만 사용합니다. 프로젝트 CRS와 모든 레이어 CRS는 EPSG:5179입니다.
원본 QGZ의 프로젝트 CRS(EPSG:5186)를 그대로 유지한 것이 아니라 분석 레이어에
맞춰 명시적으로 정리했습니다. 각 입력 형상의 좌표를 무조건 새 CRS로 간주한 것은 아닙니다.

| 표시 이름 | 프로젝트 기준 상대경로 | 피처 수 | 용도 |
| --- | --- | ---: | --- |
| Walking links · shade at 14:00 | `./CoolingPath_showcase.gpkg`, `roads_shade_20250708_1400` | 971 | 기존 그늘 통계를 조인한 보행 도로 |
| Buildings | `../../data/processed/processed_buildings.shp` | 1,392 | 건물 입력 |
| Shadows · 14:00 KST | `./CoolingPath_showcase.gpkg`, `shadows_20250708_1400` | 1,392 | 재현 스크립트로 생성한 14시 그림자 |
| Road buffers · 2 m | `../../data/processed/processed_roads.shp` | 971 | 면적 교차 분석용 도로 버퍼 |

## 제공된 원본 24개 레이어의 처리

| 원본 레이어 | 처리·이유 |
| --- | --- |
| `processed_buildings`, `processed_buildings2` | 동일 입력 중복을 하나의 Buildings 레이어로 정리 |
| `processed_roads` | 저장소의 실제 가공 SHP를 상대경로로 연결 |
| `non_buffered_roads2` | 외부 파일을 추측 연결하지 않고 저장소 `non_buffered_roads.shp`에서 색칠용 도로를 재생성 |
| `processed_shadows` | 누락된 SHP를 추측 복원하지 않고 Notebook 기반 재현 그림자로 대체 |
| `Roads_Teheran_5179` | 건물 파일을 참조하는 이름 불일치와 외부 경로 때문에 제외 |
| `Shadow_KT_Fixed_5179`, `Buildings_Teheran_5179` | 외부 수동 편집 파일의 출처·재현 상태를 확정할 수 없어 제외 |
| `Roads_Buffered_2m`, `Roads_Clean_5179` | 외부 중간 산출물 대신 저장소의 가공 도로 사용 |
| `Roads_Buffered` | CRS 선언이 빈 외부 CSV로, 검증된 입력으로 대체 |
| `Roads_Shadow_Parts`, `Roads_Shadowed_Only` | 외부 중간 교차 결과라 제외; 전처리 스크립트로 집계 과정 제공 |
| `Shadow_2026_0708_1400`, `Shadow_Real_2026` | 2025-07-08 시나리오와 이름·날짜가 다르고 외부 참조이므로 제외 |
| `Teheran_Block_Buildings`, `Teheran_Roads_Network` | 외부 원천·중간 레이어로, 공개 가공 데이터로 범위 제한 |
| `AL_D010_11_20260104`, `BND_SIGUNGU_PG`, `fixed_AL_D010`, `gangnam_str`, `gangnamgu` | 저장소에 없는 원천·행정경계·보정 파일은 추가 공개하지 않음 |
| `서울시 자치구별 도보 네트워크 공간정보` | 외부 원천 CSV 대신 가공된 보행 네트워크 사용 |
| `OpenStreetMap` | 외부 요청 없이 열리도록 온라인 배경지도 제외 |

새 GeoPackage는 기존에 공개된 형상에서 파생됐으며 API 키, 로컬 계정 경로,
원본 Notebook 출력 또는 QGIS 인증 설정을 복사하지 않습니다. 원본 QGZ 자체는
공개 파일에 포함하지 않았습니다.
