Phoenix Multi-Source Ingestion Pipeline — Handoff (2025-12-31)

## 0. 목적

Phoenix 재난 데이터 플랫폼의 **다중 소스 데이터 파이프라인 통합**을 구현한다.

- Sources: GDACS, Copernicus EMS (기존), + EONET, USGS, IFRC GO, ReliefWeb, FIRMS, WHO, ACLED, EM-DAT
- 요구: 수집 → 정규화 → 저장(upsert) → 중복 제거/교차 검증 → 스케줄링 → API 제공

---

## 1. 핵심 결정사항 (확정)

### 1.1 EventType 확장

- Copernicus에서 이미 등장하는 `landslide`, `industrial` 등을 포함해 EventType을 확장한다.
- 추가 후보(설계안): `epidemic`, `storm`, `coldwave`, `heatwave`, `complex_emergency`

### 1.2 PostGIS 도입 (이번 단계)

- `events.location`을 `geometry(Point, 4326)`로 추가한다.
- 기존 `latitude/longitude`는 (호환을 위해) 당분간 유지하되, 점진적으로 `location` 중심으로 이동한다.

### 1.3 좌표 없는 소스도 Event로 강제 통합

좌표가 없는 이벤트(예: IFRC GO, ReliefWeb, WHO)는 별도 테이블로 분리하지 않고 `Event`로 저장한다.

**표현 전략 (Oracle 권고 기반): Hybrid (NULL geometry + admin_area FK)**

- `events.location`은 NULL 허용 (좌표 없음은 "모름"으로 유지)
- `events.geo_precision` (enum): `exact | approximate | admin1 | country | unknown`
- `events.geo_method` (enum): `source_provided | geocoded | admin_centroid | manual`
- `events.admin_area_id` FK → `admin_areas(id)` (국가/행정구역 폴리곤 테이블)
- API에서 `display_point = COALESCE(events.location, admin_areas.centroid)` 형태로 제공 가능 (UI 표시용)

이 방식의 장점:

- "거짓 좌표(국가 중심점)"를 실제 좌표로 오해하지 않게 함
- 공간쿼리( bbox / intersects )에서 admin polygon과 조합 가능
- 추후 geocoding으로 실제 좌표가 생기면 `location`만 업데이트하면 됨

---

## 2. 현재 코드베이스 상태(관찰)

### 2.1 기존 서비스는 "크롤링/파싱만"

- `apps/api/src/services/gdacs_service.py`
- `apps/api/src/services/copernicus_service.py`
- 현재는 fetch & parse 후 "count 반환" 중심이고 DB 저장 로직이 거의 없다.

### 2.2 EventService는 DB가 아닌 mock

- `apps/api/src/services/event_service.py` 는 mock 이벤트를 반환 중 → 추후 DB 기반으로 전환 필요

### 2.3 DB 모델은 multi-source 잠재력은 있음

- `event_sources` 테이블이 있고 `raw_data(JSONB)` 보존 가능
- 하지만 `events.source_id/source_url` 같은 단일소스 흔적도 남아있음(추후 정리 가능)

---

## 3. 이번 세션에서 생긴 변경사항

~~현재 워킹트리에 미완성 변경이 존재함~~ → **Phase 1 완료됨**

---

## 4. 앞으로 구현해야 할 것 (Roadmap)

### Phase 1 (DB/지오 기반) ✅ COMPLETED (2025-12-31)

1. **의존성 확정** ✅
   - `geoalchemy2`는 필수 (pyproject.toml에 추가됨)
   - `geopandas/shapely/pyproj`는 `admin_areas` import 스크립트에 필요

2. **Alembic migration 추가** ✅
   - 파일: `alembic/versions/2025_12_31_0100-add_postgis_admin_areas.py`
   - PostGIS extension 활성화
   - eventtype enum에 새 값 추가 (landslide, industrial, epidemic, storm, coldwave, heatwave, complex_emergency)
   - geo_precision, geo_method enum 생성
   - admin_areas 테이블 생성 (PostGIS 지원)
   - events 테이블에 새 컬럼 추가 (location, geo_precision, geo_method, admin_area_id, glide_number)
   - 공간 인덱스 및 백필 쿼리 포함

3. **`admin_areas` 테이블 + 모델 도입** ✅
   - 파일: `src/models/admin_area.py`
   - UUID PK, iso_a2/iso_a3, name, admin_level, parent_id (self-referential)
   - PostGIS geometry (MULTIPOLYGON), centroid (POINT), bbox (JSONB)
   - GIST 인덱스, 계층적 쿼리 지원

4. **Natural Earth 데이터 import 스크립트** ✅
   - 파일: `scripts/import_natural_earth.py`
   - CLI: `python -m scripts.import_natural_earth --resolution 110m`
   - 110m/50m/10m 해상도 지원
   - GeoPandas로 shapefile 로드 → PostGIS upsert

5. **CountryGeocoder 구현** ✅
   - 파일: `src/services/geocoder_service.py`
   - `lookup(identifier)`: ISO alpha-2/3 또는 국가명으로 조회
   - `batch_lookup(identifiers)`: 다중 국가 조회
   - `find_by_point(lat, lng)`: 좌표로 국가 조회 (ST_Contains)
   - 메모리 캐싱 지원

### Phase 2 (저장 레이어) ← **다음 단계**

- Repository 패턴 도입 (EventRepository, DataSourceRepository, EventSourceRepository)
- Upsert 전략:
  - "소스+external_id"로 `event_sources` upsert
  - 동일 사건이면 `events`를 merge(추후 Dedup 엔진 단계에서)

### Phase 3 (정규화 레이어)

- 각 소스 Connector + Normalizer
- EventType 매핑 테이블 확정
- Severity 계산 통합 (USGS magnitude, GDACS alert, IFRC severity 등)

### Phase 4 (Dedup / Merge)

- Strong key: GLIDE, USGS event id, Copernicus EMSR code, EONET id
- Fuzzy: 시공간(ST_DWithin + time window) + title similarity
- 품질 점수: source 신뢰도 + 좌표 정밀도 + 업데이트 신선도

### Phase 5 (API)

- EventService를 DB 기반으로 교체
- 응답에 `sources[]`, `geo_precision`, (선택) `display_point` 포함

---

## 5. 시작 체크리스트 (Phase 1 완료 후)

```bash
# 1. Docker 컨테이너 재시작 (스키마 변경 적용)
cd infrastructure/docker
docker compose down -v  # 볼륨 삭제하여 init-db.sql 재실행
docker compose up -d

# 2. Natural Earth 데이터 import
cd apps/api
python -m scripts.import_natural_earth --resolution 110m

# 3. API 서버 테스트
uvicorn src.main:app --reload
```

---

## 6. 다음 단계 추천 (Phase 2 착수)

**즉시 착수 가능**

1. Repository 패턴 도입: EventRepository, DataSourceRepository, EventSourceRepository
2. GDACS/Copernicus 서비스에 DB 저장 로직 추가 (현재 fetch/parse만 함)
3. EventService를 DB 기반으로 교체 (mock 데이터 → 실제 DB 조회)

---

## 7. Phase 1 완료 변경사항 요약 (2025-12-31)

**생성된 파일**
| 파일 | 설명 |
|------|------|
| `src/models/admin_area.py` | AdminArea 모델 (PostGIS 지원) |
| `alembic/versions/2025_12_31_0100-add_postgis_admin_areas.py` | DB 마이그레이션 |
| `scripts/import_natural_earth.py` | Natural Earth 데이터 import CLI |
| `src/services/geocoder_service.py` | CountryGeocoder 서비스 |

**수정된 파일**
| 파일 | 변경 내용 |
|------|-----------|
| `src/models/event.py` | GeoPrecision/GeoMethod enum, location 컬럼, TYPE_CHECKING 패턴 |
| `src/models/__init__.py` | AdminArea, GeoPrecision, GeoMethod export |
| `alembic/env.py` | AdminArea metadata 연결 |
| `pyproject.toml` | geoalchemy2, shapely, geopandas, pyproj 의존성 |
| `init-db.sql` | PostGIS, admin_areas 테이블, 새 enum/컬럼 |
| `Dockerfile.db` | timescaledb-ha:pg16 이미지 (PostGIS 포함) |
