# QGIS와 Python 전처리 작업 기록

## 근거와 범위

사용자가 제공한 `CoolingPath_shadow.ipynb`와 `(Sandy) QGIS_project.qgz`를
직접 읽어 확인했습니다. QGZ의 `0112_project.qgs`에는 24개 레이어가 있으며
프로젝트 CRS는 **EPSG:5186**입니다. 이는 분석에 사용한 주요 건물·도로·그림자
레이어의 **EPSG:5179**와 구분해야 합니다. 원천 자료에는 EPSG:4326·5186,
OSM 배경지도에는 EPSG:3857이 사용됩니다.

QGIS 프로젝트는 레이어 구성·스타일·참조 경로의 증거입니다. 정확한 Processing
명령 순서나 전체 그림자 Dissolve 수행 여부를 확정하는 실행 기록은 아닙니다.
Notebook에서 직접 확인되는 Python 작업은 다음과 같습니다.

1. 강남구 좌표(37.5026, 127.0427), 2025-07-08 08–19시 KST의 태양 위치 계산.
2. 건물을 EPSG:5179로 재투영하고 0.3m로 단순화.
3. `height / tan(태양 고도)` 길이만큼 태양 반대 방향으로 이동한 형상을
   7단계(원본을 포함한 8개 위치)로 합집합하는 건물별 Shadow Ghosting.
4. 시간대별 그림자와 도로 버퍼를 교차하고 링크별 교차 면적을 합산.
   도로 면적으로 나눈 값을 최대 1로 제한하여 CSV 저장.

도로 버퍼링·건물 높이 보정 등 QGIS 단계의 상세 알고리즘과 수동 편집 이력은
제공 자료만으로 완전히 복원할 수 없습니다. 저장소의 가공된 SHP를 파이프라인
입력으로 사용합니다. 전체 도시 원천자료부터의 재현을 주장하지 않습니다.

## 재현 가능한 실행 경로

저장소 루트에서 Python 3.11 이상으로 실행합니다. 앱 실행에는 Pysolar가 필요하지
않으므로 별도 extra에만 선언했습니다. 아래 명령은 외부 API를 호출하지 않습니다.
의존성 설치에는 패키지 레지스트리 접근이 필요합니다.

```bash
python -m pip install -e '.[dev,preprocessing]'
python -m scripts.preprocessing.generate_solar_scenarios \
  --date 2025-07-08 --output /tmp/coolingpath-run/solar.csv
python -m scripts.preprocessing.generate_shadows \
  --buildings data/processed/processed_buildings.shp \
  --solar /tmp/coolingpath-run/solar.csv \
  --output /tmp/coolingpath-run/shadows.gpkg
python -m scripts.preprocessing.aggregate_shadow_by_link \
  --roads data/processed/processed_roads.shp \
  --shadows /tmp/coolingpath-run/shadows.gpkg \
  --overlap-policy union --output /tmp/coolingpath-run/links.csv
python -m pytest -q
```

출력 파일이 이미 있으면 덮어쓰지 않고 실패합니다. 재실행에는 새로운 출력 경로를
지정하세요. 기존 가공 CSV·SHP는 자동으로 바꾸지 않습니다. 높이 필드는
`--height-column`, 잔상 단계는 `--steps`, 단순화 허용치는 `--simplify`로 지정합니다.
CRS가 없거나 형상이 유효하지 않으면 임의 추정·자동 보정하지 않고 오류를 냅니다.

집계 기본값 `union`은 도로별 교차 형상을 합집합하여 건물 간 그림자 중복 면적을
제거합니다. `--overlap-policy legacy-sum`은 Notebook의 면적 합산·상한 제한을
재현합니다. 이 차이는 의도된 수정이며, 기본값으로 생성한 CSV가 기존 통계와
같다고 주장하지 않습니다. Ghosting은 연속적인 투영이 아닌 이산 근사이므로
태양 고도가 낮거나 건물 폭에 비해 이동 간격이 크면 그림자에 틈이 생길 수 있습니다.
단계를 늘려 민감도를 확인해야 합니다. 현장 정확도 검증은 별도입니다.

`notebooks/shadow_generation.ipynb`는 제공된 Notebook의 첫 9개 전처리 셀만
발췌한 **역사적 실험 기록**입니다. 출력·Colab 메타데이터는 제거했고 원본 경로는
보존했습니다. 뒤의 경로 실험·자동 생성된 작업 지시·지도 HTML 출력은 포함하지
않았습니다. Notebook 전체를 실행하는 방식 대신 위 스크립트를 사용하세요.

## 원본 QGIS 프로젝트와 공개 정리본

- `../../../Documents/`, `../../../processing/`의 외부 참조가 남아 있습니다.
- `processed_buildings`와 `processed_buildings2`는 같은 SHP를 참조합니다.
- `Roads_Teheran_5179`의 원본 경로는 `Building_Teheran_5179.shp`여서 이름과
  파일 역할이 일치하지 않습니다.
- `processed_shadows.shp` 등 저장소에 없는 파일이 참조됩니다.
- `Roads_Buffered` CSV 레이어는 CRS 선언이 비어 있습니다.

원본 QGZ는 그대로 게시하지 않았습니다. 대신 저장소 입력을 기반으로 중복·외부
레이어를 제거한 [포트폴리오용 정리본](qgis/usage.md)을 추가했습니다. 네 레이어의
참조 경로를 상대경로로 만들고 프로젝트 CRS를 분석 레이어와 같은 EPSG:5179로
정리했습니다. 원본 프로젝트 전체의 복원본은 아닙니다. 실제 QGIS에서 재개방한
프로젝트, QGIS가 렌더링한 이미지와 [레이어별 처리 내역](qgis/layer-inventory.md)을
함께 제공합니다.

## 실행 검증

제공된 가공 데이터(건물 1,392개, 도로 971개)로 위 세 명령을 모두 실행했습니다.
12시간의 그림자 16,704개와 링크·시간대 통계 11,652개를 생성했습니다.
`legacy-sum` 결과와 저장소의 기존 통계는 최대 절대 오차 약 `1.12e-15`로
부동소수점 정밀도 내에서 일치했습니다. `union`은 2,626개 링크·시간대 행에서
중복 집계 면적을 줄였습니다(차이 `1e-6` 초과 기준). 이 검증은 현재 가공 데이터와
알고리즘 재현에 대한 것이며 실제 현장 그림자의 정확도 검증은 아닙니다.
