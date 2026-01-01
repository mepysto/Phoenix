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

## 2. 현재 코드베이스 상태 (Phase 2 완료 후)

### 2.1 서비스 구조 (✅ 업데이트됨)

- `apps/api/src/services/gdacs_service.py` - fetch & parse (DB 저장은 IngestionService로 위임)
- `apps/api/src/services/copernicus_service.py` - fetch & parse (DB 저장은 IngestionService로 위임)
- `apps/api/src/services/ingestion_service.py` - ✅ **NEW** DB 저장 오케스트레이션
- `apps/api/src/services/event_service.py` - ✅ **DB 기반** (mock 제거됨)

### 2.2 Repository 계층 (✅ NEW)

- `apps/api/src/repositories/event_repository.py` - Event CRUD + 필터링
- `apps/api/src/repositories/event_source_repository.py` - upsert (source_id + external_id)
- `apps/api/src/repositories/data_source_repository.py` - DataSource 관리 + sync status

### 2.3 DB 모델 (multi-source 지원)

- `event_sources` 테이블: `(source_id, external_id)` 유니크 인덱스로 중복 방지
- `raw_data(JSONB)` 보존으로 원본 데이터 추적 가능
- `events.source_id/source_url`은 legacy 호환용으로 유지

---

## 3. 이번 세션에서 생긴 변경사항

~~현재 워킹트리에 미완성 변경이 존재함~~ → **Phase 1 완료됨** → **Phase 2 완료됨** → **Phase 3 완료됨** → **Phase 4 완료됨**

Phase 4에서는 Cross-source 중복 제거(Dedup) 및 이벤트 병합(Merge) 로직이 구현되었습니다. 같은 재난이 여러 소스(GDACS, USGS, EONET 등)에서 수집될 때 하나의 Event로 병합됩니다.

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

### Phase 2 (저장 레이어) ✅ COMPLETED (2025-12-31)

1. **Repository 패턴 도입** ✅
   - `src/repositories/base.py`: BaseRepository (AsyncSession 주입)
   - `src/repositories/data_source_repository.py`: get_by_name, get_or_create, update_sync_status
   - `src/repositories/event_repository.py`: create, update_if_better, list_events, get_by_id
   - `src/repositories/event_source_repository.py`: upsert (on_conflict_do_update), find_event_id_by_source_external

2. **Upsert 전략 구현** ✅
   - `(source_id, external_id)` 유니크 인덱스로 event_sources upsert
   - 기존 이벤트면 EventSource만 업데이트 + Event는 geo_precision 개선 시에만 업데이트
   - PostgreSQL `on_conflict_do_update` 사용

3. **IngestionService 구현** ✅
   - `src/services/ingestion_service.py`: GDACS/Copernicus 이벤트 DB 저장
   - atomic/non-atomic 모드 지원 (배치 롤백 vs 개별 실패 허용)
   - 타입 매핑: GDACS/Copernicus → EventType, SeverityLevel enum

4. **EventService DB 기반 교체** ✅
   - mock 데이터 제거, EventRepository 사용
   - sources relationship eager loading (N+1 방지)
   - FastAPI Depends(get_db) 패턴으로 세션 주입

5. **Scheduler DB 연동** ✅
   - sync_gdacs/sync_copernicus가 IngestionService 사용
   - data_sources 테이블에 last_sync, last_sync_status 저장
   - get_status_with_db() 메서드로 DB 상태 조회 가능

6. **geo 유틸리티** ✅
   - `src/utils/geo.py`: make_point_expr, validate_lat_lng, point_within_bbox

### Phase 3 (정규화 레이어) ✅ COMPLETED (2025-12-31)

1. **Connector/Normalizer 베이스 구조** ✅
   - `src/services/connectors/base.py`: RawEvent dataclass, Connector Protocol
   - `src/services/normalization/base.py`: EventUpsertPayload, Normalizer Protocol
   - `src/services/normalization/severity.py`: SeverityStrategy 구현 (USGS, EONET, GDACS, Default)
   - `src/services/normalization/admin_area.py`: AdminAreaResolver

2. **USGS Earthquake Connector** ✅
   - `src/services/connectors/usgs_connector.py`
   - GeoJSON feed 파싱 (4.5_week, all_day 등)
   - magnitude → severity 변환 (>=7.0 critical, >=6.0 high, >=4.5 medium)
   - 재시도 로직 (exponential backoff)

3. **NASA EONET Connector** ✅
   - `src/services/connectors/eonet_connector.py`
   - 13개 카테고리 → EventType 매핑
   - 다양한 geometry 타입 처리 (Point, MultiPoint, Polygon)
   - open/closed 상태 필터링

4. **IngestionService 확장** ✅
   - `ingest_raw_events()`: 범용 RawEvent 저장 메서드
   - `ingest_usgs_events()`, `ingest_eonet_events()`: 소스별 wrapper
   - SeverityStrategy 자동 선택
   - GeoPrecision/GeoMethod 자동 설정

5. **Sync Endpoints 추가** ✅
   - `POST /api/v1/sync/usgs`: USGS 지진 동기화 (feed 파라미터)
   - `POST /api/v1/sync/eonet`: EONET 이벤트 동기화 (status, days 파라미터)

6. **Scheduler 확장** ✅
   - USGS sync job (매 5분)
   - EONET sync job (매 10분)
   - 각 소스별 상태 추적 (last_sync, errors, counts)

**선택적 확장 (Phase 3.5)**

- ReliefWeb Connector (좌표 없는 소스) - 필요 시 추가
- 좌표 없는 소스의 admin_area 자동 연결 - AdminAreaResolver 준비됨

### Phase 4 (Dedup / Merge) ✅ COMPLETED (2026-01-01)

1. **Strong Key 매칭** ✅
   - `src/services/dedup/strong_keys.py`: StrongKeyExtractor
   - GLIDE number (`events.glide_number` 인덱스 활용)
   - USGS event id, Copernicus EMSR code, EONET id 패턴 추출
   - Confidence 기반 우선순위 (field > title > description)

2. **Fuzzy 시공간 매칭** ✅
   - `src/services/dedup/fuzzy.py`: FuzzyMatcher
   - `ST_DWithin(location::geography, ..., 50km)` + 48시간 윈도우
   - Haversine 거리 점수 + 시간 점수 가중 평균
   - 선택적 title similarity (Jaccard)

3. **품질 점수 시스템** ✅
   - `src/services/dedup/quality.py`: QualityScorer
   - 소스 신뢰도: GDACS(1.0) > USGS(0.95) > Copernicus(0.85) > EONET(0.8)
   - geo_precision, completeness, recency 가중 합산

4. **이벤트 병합 로직** ✅
   - `src/services/dedup/merge.py`: EventMerger
   - 품질 점수 기반 primary 선택
   - 필드별 best value 병합 (GLIDE/geo_precision 항상 best 유지)
   - Tie-break: 기존 이벤트 유지 (ID 안정성)

5. **IngestionService 연동** ✅
   - `DedupService` facade 통합
   - `_process_raw_event()` 내 cross-source 매칭 삽입
   - 매칭 시 EventSource만 기존 Event에 연결
   - 로깅: "Merged ... into existing event ... via {method}"

6. **PostGIS 헬퍼 확장** ✅
   - `src/utils/geo.py`: `point_within_distance()`, `distance_meters()`
   - `src/repositories/event_repository.py`: `find_candidates_by_spatiotemporal()`, `find_by_glide_number()`

### Phase 5 (API 고도화) ← **다음 단계**

- 응답에 `geo_precision`, `display_point` 포함
- 공간 쿼리 API (bbox, radius 검색)
- 실시간 WebSocket 업데이트

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

## 6. 다음 단계 추천 (Phase 4 착수)

**즉시 착수 가능**

1. Cross-source 이벤트 매칭: GLIDE number, 시공간 proximity
2. 품질 점수 시스템: source 신뢰도, geo_precision, 업데이트 신선도
3. 이벤트 병합 로직: 같은 재난 → 하나의 Event + 여러 EventSource

**현재 데이터 소스**

| 소스       | Endpoint           | 특징                             |
| ---------- | ------------------ | -------------------------------- |
| GDACS      | `/sync/gdacs`      | 재난 경보 (지진, 홍수, 태풍 등)  |
| Copernicus | `/sync/copernicus` | 유럽 EMS 활성화                  |
| USGS       | `/sync/usgs`       | 실시간 지진 데이터               |
| EONET      | `/sync/eonet`      | NASA 자연 이벤트 (산불, 화산 등) |

**테스트 명령**

```bash
# API 서버 시작
cd apps/api && uvicorn src.main:app --reload

# 각 소스 동기화 테스트
curl -X POST http://localhost:28000/api/v1/sync/gdacs
curl -X POST http://localhost:28000/api/v1/sync/usgs
curl -X POST http://localhost:28000/api/v1/sync/eonet
```

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

---

## 8. Phase 2 완료 변경사항 요약 (2025-12-31)

**생성된 파일**
| 파일 | 설명 |
|------|------|
| `src/repositories/__init__.py` | Repository exports |
| `src/repositories/base.py` | BaseRepository (AsyncSession 주입) |
| `src/repositories/data_source_repository.py` | DataSource CRUD + sync status |
| `src/repositories/event_repository.py` | Event CRUD + list/filter + update_if_better |
| `src/repositories/event_source_repository.py` | EventSource upsert (on_conflict_do_update) |
| `src/services/ingestion_service.py` | GDACS/Copernicus 이벤트 DB 저장 오케스트레이션 |
| `tests/services/test_ingestion_service.py` | IngestionService 단위 테스트 (22개) |

**수정된 파일**
| 파일 | 변경 내용 |
|------|-----------|
| `src/services/event_service.py` | mock 제거 → EventRepository 사용 |
| `src/services/scheduler.py` | IngestionService 연동, DB sync status 저장 |
| `src/api/v1/events.py` | Depends(get_db) 패턴으로 세션 주입 |
| `src/api/v1/sync.py` | IngestionService 사용하여 실제 DB 저장 |
| `src/utils/geo.py` | make_point_expr, validate_lat_lng, bbox 유틸 추가 |
| `src/services/__init__.py` | IngestionService export |
| `tests/api/test_events.py` | DB 기반 응답에 맞게 테스트 수정 |
| `tests/api/test_sync.py` | IngestionService mock으로 테스트 수정 |

**테스트 현황**

- 전체 149개 테스트 통과
- 신규 테스트: IngestionService 22개, Repository 관련 테스트 포함

---

## 9. Phase 3 완료 변경사항 요약 (2025-12-31)

**생성된 파일**
| 파일 | 설명 |
|------|------|
| `src/services/connectors/__init__.py` | Connector exports |
| `src/services/connectors/base.py` | RawEvent dataclass, Connector Protocol |
| `src/services/connectors/usgs_connector.py` | USGS Earthquake API Connector |
| `src/services/connectors/eonet_connector.py` | NASA EONET API Connector |
| `src/services/normalization/__init__.py` | Normalization exports |
| `src/services/normalization/base.py` | EventUpsertPayload, Normalizer Protocol |
| `src/services/normalization/severity.py` | SeverityStrategy 구현들 (USGS, EONET, GDACS, Default) |
| `src/services/normalization/admin_area.py` | AdminAreaResolver |
| `tests/services/test_usgs_connector.py` | USGS Connector 테스트 (34개) |
| `tests/services/test_eonet_connector.py` | EONET Connector 테스트 (49개) |

**수정된 파일**
| 파일 | 변경 내용 |
|------|-----------|
| `src/services/ingestion_service.py` | ingest_raw_events, ingest_usgs_events, ingest_eonet_events 추가 |
| `src/services/scheduler.py` | sync_usgs, sync_eonet job 추가 |
| `src/api/v1/sync.py` | /sync/usgs, /sync/eonet 엔드포인트 추가 |
| `tests/api/test_sync.py` | USGS/EONET sync 테스트 추가 |
| `tests/services/test_ingestion_service.py` | USGS/EONET ingestion 테스트 추가 |

**테스트 현황**

- 전체 255개 테스트 통과
- 신규 테스트: USGS Connector 34개, EONET Connector 49개, Ingestion 확장 22개

**데이터 소스 현황**
| 소스 | 타입 | 좌표 | 업데이트 주기 |
|------|------|------|--------------|
| GDACS | RSS/API | ✅ | 5분 |
| Copernicus | REST API | ✅ | 5분 |
| USGS | GeoJSON Feed | ✅ | 5분 |
| EONET | GeoJSON API | ✅ | 10분 |

---

## 10. Phase 4 완료 변경사항 요약 (2026-01-01)

**생성된 파일**
| 파일 | 설명 |
|------|------|
| `src/services/dedup/__init__.py` | Dedup 모듈 exports |
| `src/services/dedup/types.py` | 데이터 타입 (EventKeyCandidate, MatchCandidate, QualityScore, MergeResult) |
| `src/services/dedup/strong_keys.py` | StrongKeyExtractor (GLIDE/USGS/EMSR/EONET 패턴) |
| `src/services/dedup/quality.py` | QualityScorer (소스 신뢰도, geo_precision, completeness, recency) |
| `src/services/dedup/fuzzy.py` | FuzzyMatcher (시공간 매칭, Haversine 거리, title similarity) |
| `src/services/dedup/merge.py` | EventMerger (필드별 best value 병합) |
| `src/services/dedup/dedup_service.py` | DedupService facade (Strong key → Fuzzy → Merge 오케스트레이션) |
| `tests/services/test_dedup_strong_keys.py` | StrongKeyExtractor 테스트 (24개) |
| `tests/services/test_dedup_quality.py` | QualityScorer 테스트 (27개) |
| `tests/services/test_dedup_fuzzy.py` | FuzzyMatcher 테스트 (35개) |
| `tests/services/test_dedup_merge.py` | EventMerger 테스트 (24개) |

**수정된 파일**
| 파일 | 변경 내용 |
|------|-----------|
| `src/utils/geo.py` | `point_within_distance()`, `distance_meters()` 추가 (Geography cast) |
| `src/repositories/event_repository.py` | `find_candidates_by_spatiotemporal()`, `find_by_glide_number()`, `update()` 추가 |
| `src/services/ingestion_service.py` | `DedupService` 연동, `_merge_into_existing_event()` 메서드 추가 |
| `tests/services/test_ingestion_service.py` | dedup mock 추가로 기존 테스트 호환 |

**테스트 현황**

- 전체 329개 테스트 통과 (신규 dedup 테스트 110개 포함)

**Cross-source 병합 흐름**

```
Ingestion → Same-source check → Cross-source match (Strong key/Fuzzy)
         → Quality score comparison → Merge patch → EventSource 연결
```

**품질 점수 가중치 (기본값)**
| 요소 | 가중치 |
|------|--------|
| source_reliability | 40% |
| geo_precision | 30% |
| completeness | 20% |
| recency | 10% |

---

## 11. 다음 단계 추천 (Phase 5 착수)

**즉시 착수 가능**

1. API 응답에 `geo_precision`, `display_point` 필드 추가
2. 공간 쿼리 API: `GET /events?bbox=...`, `GET /events?radius=50km&lat=...&lng=...`
3. 실시간 WebSocket 업데이트 (이벤트 생성/수정 시 push)

**선택적 확장 (Phase 4.5 - Offline Merge)**

- 기존에 중복 생성된 Event 정리 (batch job)
- `events.merged_into_id`, `events.is_canonical` 컬럼 추가
- 관리용 엔드포인트: `/admin/dedup/run`
