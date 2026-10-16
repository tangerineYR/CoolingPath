# CoolingPath QGIS 포트폴리오 프로젝트

저장소를 내려받은 뒤 **`docs/qgis/CoolingPath_QGIS.qgz`** 를 QGIS에서 엽니다.
QGZ 파일 하나만 내려받으면 건물·도로 SHP를 찾을 수 없으므로 저장소 디렉터리
구조를 유지해야 합니다. QGIS 3.40.6에서 개방과 렌더링을 확인했습니다.
앱 설치, API 키, 인터넷 배경지도는 필요하지 않습니다.

![QGIS에서 렌더링한 공간 분석 개요](screenshots/qgis-overview.png)

이 이미지는 실제 QGIS 인쇄 레이아웃의 렌더링 결과이며, 과거 작업 당시의
GUI 스크린샷은 아닙니다. 프로젝트의 `Offline portfolio overview` 인쇄 레이아웃에서
다시 내보낼 수 있습니다. 지도는 북쪽이 위이며 프로젝트와 분석 레이어 CRS는
EPSG:5179(미터)입니다.

## 무엇을 보여주는가

- 가공된 건물과 보행 도로의 공간적 관계
- 2025-07-08 14:00 KST의 건물별 Ghosting 그림자
- 기존 CSV의 14시 그늘 비율로 색칠한 보행 링크
- 그림자 교차 분석에 사용한 2m 도로 버퍼

이는 제공된 원본 프로젝트를 참고해 **공개된 입력으로 다시 구성한 정리본**입니다.
원본의 모든 레이어·스타일·수동 작업을 보존한 복원본은 아닙니다. 최적 경로를
계산하는 프로젝트도 아니며, 경로 비교는 Streamlit 앱에서 수행합니다.

도로 색상은 앱과 비교하기 위해 기존 `hourly_link_stat_20250708.csv`를 사용합니다.
그 통계는 건물 간 겹친 그림자를 합산한 역사적 방식입니다. 새 전처리의 기본
`union` 결과로 교체한 값이 아니며, 정확도 개선이 검증된 현장 관측값도 아닙니다.
원본 971개 링크를 모두 표시하므로 앱의 대표 링크 선정 정책과도 구분됩니다.

## 파일과 관리 범위

`CoolingPath_showcase.gpkg`에는 14시 그림자와 색칠용 보행 링크만 담았습니다.
원본 건물·도로 속성을 통째로 복제하지 않고 ID·길이·시간·그늘 비율 등 필요한
필드만 사용합니다. 건물과 도로 버퍼는 기존 저장소 파일을 상대경로로 참조합니다.
[레이어 목록과 원본 정리 내역](layer-inventory.md)을 참고하세요.

외부 파일 경로, 온라인 타일, QGIS Python 매크로와 인증정보 연결은 없습니다.
새 데이터의 이용 권한을 추가로 부여하는 패키지는 아니며 기존 원천 데이터의
이용 조건은 그대로 적용됩니다.

## 재생성

먼저 저장소 루트에서 [전처리 절차](../qgis-workflow.md)에 따라
`/tmp/coolingpath-run/shadows.gpkg`를 생성합니다. 이후 **PyQGIS가 제공되는 Python**으로
다음 명령을 실행합니다. 일반 앱용 `.venv`의 Python과 다를 수 있습니다.

```bash
# Debian/Ubuntu에서 QGIS의 Python 바인딩을 설치한 경우
QT_QPA_PLATFORM=offscreen /usr/bin/python3 scripts/qgis/build_portfolio.py \
  --shadows /tmp/coolingpath-run/shadows.gpkg

QT_QPA_PLATFORM=offscreen /usr/bin/python3 scripts/qgis/build_portfolio.py \
  --check docs/qgis/CoolingPath_QGIS.qgz
```

빌더는 현재 표본(건물 1,392개·도로 971개)의 포트폴리오 산출물 전용입니다.
실수로 기존 결과물을 덮어쓰지 않도록 QGZ 또는 GeoPackage가 이미 있으면 중단합니다.
재생성이 필요하면 해당 두 파일과 렌더링 이미지를 별도 디렉터리로 보관한 뒤
실행하고 결과 차이를 검토하세요. 입력 그림자의 기준 날짜는 위 전처리 절차의
2025-07-08을 사용해야 합니다.

CI는 QGIS 없이 프로젝트의 상대경로, 로컬 데이터 제공자, CRS, GeoPackage 무결성,
피처 수, CSV와의 통계 일치를 검사합니다. 실제 QGIS 개방과 이미지 렌더링은 별도로
검증했으며, 저장소를 다른 위치로 옮긴 복사본에서도 네 레이어가 정상 로드됐습니다.
