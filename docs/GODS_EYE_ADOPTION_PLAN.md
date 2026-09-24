# God's Eye View 반영 기획안 (Track 0 · Track G)

> **작성일**: 2026-09-23
> **짝 문서**: [UPGRADE_MASTER_PLAN.md](./UPGRADE_MASTER_PLAN.md)
> **참고**: [bilawalsidhu/gods-eye-view](https://github.com/bilawalsidhu/gods-eye-view) (MIT)


## Context

- **요청:** Phoenix 전체를 검토해 수정 사항을 제안하고, 2026-08 GitHub Trending 1위였던 오픈소스 **God's Eye View(GEV, bilawalsidhu/gods-eye-view, MIT)**의 좋은 요소를 Phoenix에 반영하는 기획안을 만든다.
- **현재 상태:**
  - Phoenix는 Phase 1 MVP를 마쳤다. 백엔드 소스는 4종, 중복제거, PostGIS가 들어가 있다.
  - 실제 코드를 점검한 결과, **데이터가 갱신되지 않는 치명적 버그**와 **인증 없는 Admin API**가 있다.
  - **프론트엔드는 "실시간" 플랫폼인데도 실시간 연결이 전혀 없다**(WS 미사용, 새로고침 없음, 50건 제한).
- **기존 문서와의 관계:** `docs/UPGRADE_MASTER_PLAN.md`(Track A–F)가 이미 있으므로 새로 쓰지 않는다. 본 기획은 다음 두 가지만 담는다.
  - **(1) Track 0 – 안정화:** 실사로 발견한 결함 수정. 마스터플랜 M1보다 먼저 진행한다.
  - **(2) Track G – GEV 전면 채택:** 신규 트랙. GEV의 **모든 기능**(CCTV, 항공기·선박·위성 추적, 센서 셰이더, 콕핏, 음성 에이전트 포함)을 재난·전쟁 복원을 위한 감시·모니터링 용도로 재정의해 이식한다. 기존 Track B/D/E/F와 겹치는 항목은 그 트랙에 합친다.
- **최종 산출물:** 승인 후 이 기획을 `docs/GODS_EYE_ADOPTION_PLAN.md`로 저장하고, 마스터플랜 §0 표에 Track 0/G 행을 추가한다.

---

## Part 1. 전체 검토 결과 (코드 실사)

테스트 현황은 다음과 같다.
- **API:** 443개 중 442개 통과. 실패 1건은 미커밋 `tests/test_models.py:14`로, `AdminArea(code=…)`에 없는 컬럼을 넘긴다.
- **Web:** `eventStore.test.ts:136-184`와 `Sidebar.test.tsx:9-19`가 `visibleTypes` 구조로 바뀐 스토어를 반영하지 못해 실패할 것으로 보인다. 직접 실행하지는 않았다.

### P0 – 데이터 정확성 & 보안 (즉시)

| # | 문제 | 위치 | 조치 |
|---|---|---|---|
| 1 | 기존 이벤트의 제목, 심각도, `end_date`, `is_active`가 영원히 갱신되지 않음. `geo_precision`이 개선될 때만 업데이트됨 | `repositories/event_repository.py:128-141` | precision 검사는 좌표 필드에만 적용하고, 나머지 필드는 항상 패치 |
| 2 | Admin API에 인증이 없음. 누구나 `merge/trigger?dry_run=false`를 호출할 수 있음 | `main.py:52`, `api/v1/admin.py` | `sync.py`의 `X-API-Key` 의존성을 공용 `core/security.py`로 옮기고 `hmac.compare_digest`로 비교. admin, sync, `/scheduler/status`에 적용 |
| 3 | GDACS `event_id`의 연산자 우선순위 버그. link가 없으면 `""`가 되어 unique가 충돌하고, 해저드 타입 간 ID도 충돌 | `services/gdacs_service.py:236` | 괄호로 묶고 `f"{eventtype}-{eventid}"`로 키 생성 |
| 4 | 위도·경도 0.0이 누락으로 처리됨(`or`) | `event_repository.py:40,78,146` | `is not None`으로 비교 |
| 5 | 배치 중 한 건이 실패하면 트랜잭션 전체가 중단됨 | `ingestion_service.py:173-190` 외 2곳 | 이벤트마다 `session.begin_nested()` savepoint 사용 |
| 6 | 같은 소스의 서로 다른 이벤트(예: USGS 여진)가 fuzzy로 병합됨. canonical 필터와 GLIDE `scalar_one_or_none`에서 크래시 | `event_repository.py:369-398`, `dedup_service.py:117` | 같은 source는 제외하고 `is_canonical` 필터와 `.first()` 사용 |
| 7 | 목록과 GeoJSON이 병합된 중복 이벤트까지 노출 | `event_repository.py:170-259` | 기본값을 `is_canonical=true`로 |
| 8 | 프로덕션에서 MOCK_EVENTS(가짜 "Ukraine" 포함)가 폴백으로 표출됨 | `MapPageClient.tsx:38`, `GlobeViewer.tsx:27-113`, `CesiumViewer.tsx:35-121` | mock을 제거하고 빈 상태/오류 상태 UI 추가. 데모 모드는 `NEXT_PUBLIC_DEMO=1`일 때만 |
| 9 | Cesium popup에 외부 피드의 HTML을 정제 없이 삽입(XSS) | `CesiumViewer.tsx:224-237` | 텍스트 escape 처리 |
| 10 | 기본 비밀값과 debug 기본값: `dev-sync-key`, `api_debug=True`이며 SQL echo가 파라미터까지 로깅 | `core/config.py:14-16`, `db/database.py:18` | production 환경에서 기본값이면 기동 실패. debug 기본값은 False |

### P1 – 기능 결함

**GDACS·Copernicus 경로**
- GDACS와 Copernicus는 중복제거와 브로드캐스트를 우회하고 `is_active=True`를 하드코딩한다(`ingestion_service.py:586-828`).
- 조치: USGS·EONET처럼 `RawEvent` + `Connector` 경로로 이관한다. 이렇게 하면 872줄 파일도 분할된다.

**오프라인 병합**
- `_event_to_dict`가 `latitude`로 보내는데 merger는 `lat`을 읽는다(`offline_merge_service.py:465` ↔ `merge.py:315`).

**잘못된 입력이 500을 반환하는 경우**
- enum 파싱 실패, 날짜 문자열을 asyncpg에 그대로 전달, `limit` 음수 허용.
- 조치: 스키마에서 `datetime`과 `Literal`로 검증하고, `ge=1`을 추가하고, `ExternalAPIError` 핸들러를 추가한다.

**브로드캐스트와 GDACS 파싱**
- 브로드캐스트가 commit보다 먼저 나간다. 조치: after-commit 큐를 쓴다.
- GDACS georss 폴백이 동작하지 않는다(`gdacs_service.py:213-227`).
- `defusedxml`을 적용한다.

**스키마 이원화**
- 모델, `init-db.sql`, Alembic이 서로 다르다.
  - enum 이름이 `eventtype`과 `event_type`으로 다르다.
  - `data_sources`의 7개 컬럼이 빠져 있다.
  - `idx_event_sources_source_external`이 없어서 ON CONFLICT가 실패한다.
- 조치: Alembic을 단일 원천으로 삼는 교정 마이그레이션을 만들고, `init-db.sql`은 extension 설치만 하도록 축소한다.
- 미커밋 JSONB 마이그레이션에는 잘못된 JSON 행을 사전에 정리하는 단계를 추가한다. validator는 dict이면서 `type` 키가 있는지 확인하고, 이를 위해 `utils/geojson.validate_geojson`을 재사용한다.

**프론트엔드**
- 2D/3D를 토글하면 지도가 재생성된다. `is3D`가 init effect의 deps에 들어 있기 때문이다(`GlobeViewer.tsx:442`).
- `requestIdleCallback`이 해제되지 않는다.
- 50건만 로드되고 `loadMore`는 호출되지 않는다.
- 필터 요청이 경쟁한다. 조치: `AbortController`를 쓴다.
- `events/page.tsx:136`이 `filter.types`를 참조하는데, 스토어에서는 이미 제거된 필드다.
- Header 검색의 `?q=`와 "View on Globe"의 `/?event=`를 아무 곳에서도 처리하지 않는다.
- 범례는 severity 색상인데 마커는 type 색상이다.
- Cesium 엔진은 UI에서 도달할 수 없고, 에셋과 `CESIUM_BASE_URL`도 없다.

### P2 – 성능, 인프라, 품질

**DB 쿼리**
- `ST_DWithin(cast(location, Geography))`는 GiST 인덱스를 쓰지 못한다.
- 조치: geography 함수형 인덱스를 만들거나, bbox 필터를 `location && ST_MakeEnvelope`로 바꾼다.
- 누락 인덱스: `event_sources.event_id`, `datasets.event_id`, `events.created_at`, `(type, start_date)`.

**프로세스 구조**
- 기동할 때마다 GDACS를 동기 fetch한다(최대 약 47초). 테스트도 이 때문에 느리다.
- 워커마다 스케줄러가 중복 실행된다.
- 조치: 마스터플랜 B-5의 `SCHEDULER_ENABLED`와 Redis 락을 앞당겨 적용한다.

**WebSocket**
- 브로드캐스트가 락을 잡은 채 순차적으로 send한다. Origin 검사와 연결 제한이 없다.

**프론트 성능**
- snake→camel 미들웨어가 JSON을 세 번 처리한다.
- zustand 스토어를 selector 없이 전체 구독한다.

**인프라**
- web 컨테이너가 `next dev`로 뜨고, api 컨테이너는 `--reload`와 소스 마운트를 쓴다.
- `.dockerignore`가 없다. Postgres와 Redis 포트가 외부에 노출되고, Redis에는 비밀번호가 없다.
- 포트 설정이 세 곳에서 서로 다르다.

**CI·린트**
- `.github/`가 없다. ESLint 9와 flat config가 맞지 않는다. ruff 경고가 435건이다.

**타입**
- `@phoenix/shared` 수기 타입과 OpenAPI 생성 타입이 공존한다. `as unknown as` 캐스팅이 많다.

**접근성**
- 아이콘 버튼에 label이 없다. 토글에 `role="switch"`가 없다. 마커를 키보드로 조작할 수 없다. `lang`과 `dir="rtl"`이 없다.

**데드코드 정리**
- `utils/geojson.py` 대부분, `geocoder_service`, normalization resolver, Copernicus damage 함수 등.
- `geocoder`는 `country_code`와 `admin_area_id`를 채우는 데 재사용할 가치가 있다. 삭제 대신 연결을 권장한다.

---

## Part 2. God's Eye View 분석 → Phoenix 적용

GEV는 CesiumJS, Google Photorealistic 3D Tiles, 19개 공개 데이터 레이어, OpenAI Realtime 음성 에이전트(29개 tool), GLSL 센서 모드, Scene Director, Node 프록시로 구성된 **로컬 우선 공간 인텔리전스 콘솔**이다.

### 가져올 것 (Phoenix 미션: 재난 대응·복구에 맞게 변형)

| GEV 요소 | Phoenix 적용안 | 합칠 트랙 |
|---|---|---|
| **키 없이 쓰는 레이어 + "POWER UP" 키 업그레이드**: 키는 게이트가 아니라 업그레이드 | 레이어 레지스트리에 `auth: keyless / free_key / metered`를 표기. 키가 없어도 USGS, GDACS, EONET, NHC 사이클론, 바람 레이어는 동작. FIRMS·ACLED 키는 서버 env에서만 받고 UI에는 "키 추가 시 활성" 배지만 표시 | G-1 |
| **재난 관련 신규 레이어** | NASA FIRMS 화점(A-1과 합침), **NHC/JTWC 태풍 진로·예보 콘**, **NOAA GFS 바람 파티클**, GOES 적외 구름, RainViewer 강수 레이더, USGS ShakeMap 폴리곤, 기반시설 번들(댐, 해저케이블, 발전소, 병원: OSM 및 Global Energy Monitor). 댐 레이어는 D-4 연쇄 재난 예측의 입력이 됨 | A-1, G-2 |
| **통합 타임라인 스크러버**: 모든 시계열 레이어를 한 타임라인에서 0.25–4× 재생 | 이벤트 발생·전이, 화점 누적, 태풍 진로, 기상 레이어를 하나의 `TimelineStore`로 스크럽. 백엔드는 A-4 `event_metrics`(TimescaleDB)와 `?at=` 스냅샷 쿼리 | E-1 (강화) |
| **Scene Director(시네마틱 카메라 투어), 재생, 공유 파일** | **"Disaster Brief" 스토리 모드**: 재난 하나의 발생 → 확산 → 대응을 카메라 경로 + 타임라인 + 주석으로 저장하고, 언론·NGO가 공유하거나 위젯(F-3)으로 임베드 | G-3 |
| **URL 상태 직렬화**: 카메라, 레이어, 스타일, 추적 대상 | `?lng&lat&z&pitch&bearing&layers&t&event=` 딥링크. 현재 동작하지 않는 `/?event=`와 검색 `?q=` 버그도 함께 해결 | G-4 (P1 버그와 합침) |
| **AI 에이전트 tool-calling + 장면 컨텍스트 grounding + 지출 상한** | D-1 RAG Q&A를 **"지도를 조작하는 에이전트"**로 확장. tool 예: `fly_to`, `toggle_layer`, `filter_events`, `count_in_view`, `summarize_view`, `measure`, `draw_area`. 현재 뷰포트, 활성 레이어, 선택 이벤트를 컨텍스트로 전달. 성공한 tool만 확인하고 추측성 응답은 금지. 세션별 비용 미터와 하드캡. 텍스트 우선, 음성은 선택(Claude API tool use 기반, 서버 프록시) | D-1 (확장) |
| **Intelligence HUD / AI 장면 요약** | "현재 화면" 브리핑 스트립: 화면 안 활성 재난 수, 영향 인구 합계, 최고 심각도, 데이터 신선도. 백엔드는 `GET /geodata/summary?bbox=` | G-5 |
| **데이터 신선도·stale feed 감지** | `data_sources.last_sync_status`와 `consecutive_failures`는 이미 모델에 있으므로 이를 **소스 상태 패널**로 노출. 레이어마다 "N분 전 갱신" 표시와 stale 경고. 실패 시 `status=failed`를 기록하는 버그도 수정 | G-1, B-6 |
| **보간 & 화면 공간 최적화**: dead reckoning, 지평선 밖 컬링, 지연 로딩 | 태풍 진로 보간 애니메이션, deck.gl 없이 MapLibre 벡터타일(B-2) 도입, Cesium 번들 lazy load(B 예산) | B-2 |
| **3D 모드 (Photorealistic 3D Tiles)** | 도시 규모 재난(지진, 폭발)의 **피해 현장 3D 컨텍스트**용으로 Cesium 경로를 되살림: 에셋 복사, ion 토큰, 엔진 토글 UI. Google 3D Tiles는 metered이므로 선택 사항으로 둠(키가 있을 때만) | E / G-6 |
| **서버 프록시 + 키 브로커 + SSRF 방어 + IP별 레이트리밋** | 외부 키가 필요한 모든 호출(FIRMS, ACLED, LLM)은 FastAPI 경유만 허용. `slowapi` 레이트리밋, 응답 크기 상한, 오류 메시지 정제 | P0-2와 F-1 |
| **`npm run doctor`**: 설치 상태 점검, 키 설정 여부만 출력 | `pnpm doctor` 스크립트: Node/Python/Docker, DB extension, 마이그레이션 헤드, 각 소스의 연결성, 키 설정 여부(값은 출력하지 않음) | G-7 |
| **윤리 선언**: "People are not a query type" | `docs/RESPONSIBLE_USE.md`와 CONTRIBUTING에 명시: 개인 추적, 얼굴 인식, 난민 개인 위치 노출 금지. 분쟁(ACLED) 데이터는 격자 단위로 집계해 표출(마스터플랜 §7 민감도 정책과 합침). "운영·안전 결정에 단독 사용 금지" 고지 | G-8 |
| **DATA_SOURCES.md**: 소스별 라이선스와 약관 | 소스별 라이선스, 출처 표기, 갱신 주기, 키 필요 여부 표. UI 하단에 attribution 표시 | G-8 |
| **키보드 단축키 & 첫 실행 미션 선택** | `1–4` 베이스맵, `L` 레이어, `T` 타임라인, `/` 검색, `Esc`. 첫 방문 온보딩: "지금 진행 중인 재난 / 내 지역 / 타임라인 탐색" | G-9 |
| **Contacts roster**: 주변 목록 | "주변 이벤트" 패널: 현재 뷰 또는 반경 N km의 이벤트를 거리순으로 표시. 기존 radius search를 재사용하고, 키보드 접근성 대안도 겸함 | G-5 |

### 감시·모니터링 계층: GEV 나머지 기능 전부 채택 (Track G-10 ~ G-20)

사용자 결정(2026-09-23)에 따라 **GEV의 모든 기능을 채택**한다. 재난·전쟁으로부터 복원하려면 상황 감시와 모니터링이 필수라는 판단이다. 각 기능은 "복원 운영"에 맞게 용도를 재정의한다. 모든 레이어는 G-1 레이어 레지스트리에 플러그인으로 등록하고, 켜고 끄기, 키 등급, 신선도 표시를 공통으로 적용한다.

| ID | GEV 기능 | Phoenix 적용 (재난·전쟁 복원 용도) | 데이터 소스 |
|---|---|---|---|
| G-10 | **공공 CCTV 메시 + 3D 투영 + 뷰셰드** | 재난 현장의 공개 교통·기상 카메라를 3D로 투영해 침수 수위, 도로 붕괴, 산불 연기를 육안으로 확인. 뷰셰드(카메라 감시 범위 볼륨)로 **감시 사각지대**를 파악해 드론·현장 조사 우선순위를 정함. 이벤트 상세에서 "반경 N km 카메라" 자동 연결. HLS는 서버 프록시로 중계하며 세션 수, 세그먼트 수, 메모리 상한은 GEV와 같은 수준 | 도시·주정부 공개 교통 카메라 API, Windy Webcams, OSM `surveillance` 태그 |
| G-11 | **항공기 추적 (민간 + 군용 ADS-B)** | 재난 지역의 구호 수송기, 소방 항공기, 의료 헬기, 공역 폐쇄 현황을 파악. 전쟁 지역에서는 공역 활동을 모니터링. 항공기 클래스별 필터(구호·소방·군용)와 24시간 궤적 백필. 보간(dead reckoning)으로 15–30초 간격 데이터를 부드럽게 표시 | OpenSky, adsb.lol (키 불필요), FAA TFR·NOTAM (공역 제한) |
| G-12 | **선박 추적 (AIS)** | 구호물자 선박, 항만 봉쇄·혼잡, 해상 대피 모니터링. 흑해 곡물 회랑 같은 **인도적 해상 회랑** 감시. 이벤트 반경 안의 선박 목록 제공 | AISStream (무료 키) |
| G-13 | **위성 + 통과 예측** | CelesTrak TLE와 SGP4로 **지구관측 위성(Sentinel, Landsat, WorldView, ICEYE SAR)이 다음에 재난 지역을 지나는 시각**을 예측. Copernicus EMS 촬영 요청 타이밍 판단에 활용. GMST 보정 궤도 링 | CelesTrak (키 불필요) |
| G-14 | **센서 시각 모드 (GLSL): FLIR, NVG, CRT, Noir, Snow** | 모든 모드를 채택. FLIR·Ironbow는 FIRMS 화점, 열섬, 화재 현장 강조. NVG는 야간 운영과 VIIRS 야간 조명(정전 피해 지표)을 함께 표시. 그 밖에 접근성용 고대비 모드를 추가. 데이터를 다시 불러오지 않고 셰이더만 전환 | 클라이언트 셰이더 |
| G-15 | **탐지 오버레이 + 전술 HUD** | 화면 안 엔티티에 바운딩 박스와 ID 라벨을 표시하고 밀도를 조절. 운영센터 스타일 텔레메트리 카드(선택 엔티티의 속도, 고도, 목적지, 신선도) | 전체 레이어 공통 |
| G-16 | **콕핏 / 추적 카메라 모드 + 3D Hangar** | 구호 항공기나 선박을 따라가는 1인칭 시점. **드론·항공 정찰 계획 시뮬레이션**(정찰 경로를 미리 비행)으로 확장. 가까이 다가가면 클래스별 3D 모델(glTF)로 전환 | Cesium 엔진 (G-6) |
| G-17 | **ALPR·감시 인프라 지도** | OSM에 태깅된 감시 인프라의 **위치만** 표시(번호판 데이터 없음). 전쟁 이후 **파괴·복구 대상 도시 인프라 목록**과 치안 복구 계획에 활용 | OSM Overpass |
| G-18 | **라이브 라디오** | 재난 지역의 현지 방송국을 지도에서 바로 청취. 비상 방송, 현지어 상황 파악, 통신 두절 여부 확인(방송국 오프라인이면 정전·통신 두절 신호) | Radio Browser API |
| G-19 | **교통, 대중교통, 공유자전거, 경로 안내** | TomTom 교통 흐름으로 대피 정체 파악. GTFS-RT와 GBFS로 대중교통 운행 중단 여부 확인. OSRM 경로 안내를 **위험 폴리곤을 회피하는 대피·구호 배송 경로**로 확장 | TomTom, GTFS-RT, GBFS, OSRM |
| G-20 | **나머지 레이어 전부** | 낙뢰 밀도, 우주 발사(Launch Library 2, 위성 보충 추적), 데이터센터·해저케이블(통신 복구 우선순위), 군사 시설(OSM, 분쟁 맥락), 장소 검색 | 각 공개 소스 |

부가 채택:
- **운영센터(Ops Console) 모드:** 위 감시 레이어, HUD, 탐지 오버레이, 콘택트 목록, 브리핑 스트립을 하나의 전체 화면 레이아웃으로 묶은 "상황실" 뷰. 기관 사용자(Phase 2 인증)의 기본 화면 후보.
- **음성 에이전트:** D-1 텍스트 에이전트에 음성 입출력을 추가하고, GEV의 29개 tool 전체를 Phoenix tool 세트로 이식(카메라, 주석, 레이어, 분석, 장면). 세션 비용 미터, 경고 임계값, 하드캡 포함.
- **음성·수동 화이트보드 주석:** 경계 폴리곤(OSM), 선, 면, 거리 측정. E-3 주석 기능과 합침.

**거버넌스 (GEV 자체 원칙을 그대로 계승):**
- GEV가 명시한 선을 유지한다. 특정 인물 검색, 얼굴 인식, 개인 추적 기능은 만들지 않는다("People are not a query type"). 이 선을 넘는 PR은 병합하지 않는다.
- 공개 데이터만 사용하고 소스별 약관을 따른다(DATA_SOURCES.md).
- 분쟁 지역 옵션: 교전 중인 지역의 군용기·선박 위치는 설정에 따라 **지연 표시 또는 격자 집계**를 할 수 있게 한다. 기본값은 GEV와 같이 실시간이며, 기관 배포 시 정책으로 켜고 끈다. 마스터플랜 §7 민감도 정책과 합친다.

### 기술 스택상 채택하지 않는 것

- **Vanilla JS 전환:** Next.js와 OpenAPI 타입 체계를 유지하고, GEV 모듈은 React 컴포넌트와 레이어 플러그인으로 이식한다.
- **로컬 전용 바인딩:** Phoenix는 공개 호스팅이 목표다. 대신 GEV의 원격 클라이언트 키 설정 비활성화, IP별 레이트리밋, 프록시 방어 원칙을 채택한다.

### 아키텍처 전제 (감시 계층 채택으로 필요해진 것)

- **엔진:** 감시 레이어 대부분(3D 투영, 뷰셰드, 콕핏, 셰이더)은 CesiumJS가 필요하다. **MapLibre(가벼운 기본, `/lite`)와 Cesium(운영센터·3D)을 공존**시키고, 레이어 플러그인은 엔진별 렌더러를 구현한다. 현재 도달할 수 없는 Cesium 경로를 되살리는 작업(G-6)이 M5의 선행 조건이다.
- **고빈도 스트림:** 항공기 11k+와 선박 수천 척은 DB에 이벤트로 저장하지 않는다. `apps/api/src/services/streams/` 에서 폴링하고, Redis에 최신 스냅샷(TTL)을 둔 뒤, WS 채널(`/ws/tracks?bbox=`)로 뷰포트만 구독하게 한다. 이력 백필은 TimescaleDB `track_points` 하이퍼테이블(7일 보관)을 쓴다.
- **렌더링:** 수만 개 엔티티는 React 컴포넌트가 아니라 Cesium `PointPrimitiveCollection`/`BillboardCollection`과 Web Worker 보간으로 그린다(현재 CesiumViewer의 이벤트당 Entity 방식은 폐기).
- **프록시:** `apps/api/src/api/v1/proxy.py`에 HLS, 카메라 스냅샷, 키가 필요한 API를 둔다. 허용 도메인 목록(SSRF 방어), 응답 크기·시간 상한, 동시 세션 제한을 적용한다.

---

## 실행 로드맵

| 단계 | 내용 | 기간(예상) |
|---|---|---|
| **M0 – 안정화 (Track 0)** | P0 10건 → P1(스키마 단일화, GDACS·Copernicus 커넥터 이관, 프론트 버그) → CI(GitHub Actions: ruff, pytest, vitest, tsc, build) → 프로덕션 Dockerfile | 2–3주 |
| **M1 – 실시간 기반** | WS 클라이언트 연결 + 델타(B-3), 스케줄러 분리(B-5), 벡터타일(B-2), URL 딥링크(G-4), 소스 상태 패널(G-1) | 3주 |
| **M2 – 레이어 확장** | 레이어 레지스트리(G-1), FIRMS, NHC, 바람, 레이더, 기반시설(G-2), DATA_SOURCES / RESPONSIBLE_USE(G-8), doctor(G-7) | 3–4주 |
| **M3 – 시간축** | 통합 타임라인(E-1 강화), Disaster Brief 스토리 모드(G-3), 화면 요약 HUD와 주변 패널(G-5) | 3주 |
| **M4 – AI 에이전트** | map tool-calling 에이전트(D-1 확장), SitRep 연계, 비용 상한 | 3주 |
| **M5 – 감시 기반** | Cesium 경로 복구(G-6), 고빈도 트랙 스트림 인프라, 프록시(`proxy.py`), 항공기(G-11), 선박(G-12), 위성·통과 예측(G-13) | 4주 |
| **M6 – 감시 확장** | CCTV 메시와 뷰셰드(G-10), 센서 셰이더(G-14), 탐지 오버레이와 HUD(G-15), 라디오(G-18), 교통·대중교통·경로(G-19), 기타 레이어(G-17, G-20) | 4–5주 |
| **M7 – 운영센터** | Ops Console 모드, 콕핏·정찰 시뮬레이션과 3D Hangar(G-16), 음성 에이전트(29 tool 이식), 분쟁 지역 정책 토글 | 3–4주 |
| 이후 | 마스터플랜 C(매칭), F(위젯/PWA) | — |

**재사용할 기존 자산**
- 백엔드:
  - `services/connectors/` 의 `RawEvent`/`Connector` 프로토콜: 신규 레이어와 커넥터에 사용
  - `services/broadcaster.py`: WS 델타 전송
  - `services/clustering_service.py`: 요약 HUD의 집계
  - `EventRepository`의 radius search: 주변 패널
  - `utils/geojson.validate_geojson`: JSONB validator
  - `sync.py`의 API 키 의존성
- 프론트:
  - `settingsStore`의 `autoRefresh`, `refreshInterval` 설정(현재 미사용 → 연결)
  - `mapStore.layers`: 레이어 레지스트리의 UI 측

## Verification

- **M0**
  - `cd apps/api && pytest` 전체 통과. 추가 테스트:
    - `update_if_better` 필드 갱신
    - 위도·경도 0 처리
    - GDACS ID 생성
    - savepoint 격리
    - admin 401
    - 동일 소스 비병합
  - `pnpm --filter web test && pnpm build` 통과.
  - `alembic upgrade head`를 빈 PostGIS DB에 적용한 뒤 `alembic check`로 모델과 차이가 없는지 확인.
  - Docker 전체 스택을 기동해 `/health`, 이벤트 수 50건 초과 표출, mock 미표출을 확인.
- **M1 이후**
  - Playwright E2E로 확인: 딥링크 복원, WS 수신 시 마커 갱신, 타임라인 스크럽, 에이전트 tool 호출이 실제 지도 상태를 변경하는지.
  - Lighthouse CI로 LCP 3.5초 미만, 초기 JS 350KB 미만(gzip) 예산을 검증.
- **M5–M7**
  - 부하 테스트: 항공기 11k와 선박 5k 엔티티에서 운영센터 뷰가 60fps(데스크톱 기준)를 유지하고, 뷰포트 구독 WS 대역폭이 상한 안에 있는지 확인.
  - 프록시 보안 테스트: 허용 목록 밖 URL 거부, 크기·시간 상한, 동시 HLS 세션 제한.
  - 위성 통과 예측을 CelesTrak과 외부 도구(예: Heavens-Above)의 결과와 대조.
- 브라우저 확인은 `run` 스킬 또는 chrome-devtools로 지도 렌더와 콘솔 오류를 점검.


---

## 진행 현황 (2026-09-24)

M0–M7 로드맵을 PR #1–#31로 구현했다. 모든 PR은 CI(API·Web·타입 계약)를 통과했고 브라우저에서 실제 데이터로 확인한 뒤 병합했다.

### 완료

| 항목 | 내용 | PR |
|---|---|---|
| M0 | P0·P1 결함 수정, CI, 공간 쿼리 성능, 스케줄러 락 | #1, #2 |
| M1 | WebSocket 실시간 갱신, 소스 상태 패널(G-1), 딥링크(G-4) | #3, #4 |
| M2 | 레이어 레지스트리(G-1), 레이더·적외 구름·야간광, 사이클론·ShakeMap, 발전소·댐·병원(G-2), FIRMS 화재, DATA_SOURCES / RESPONSIBLE_USE / doctor(G-7·G-8) | #5–#9 |
| M3 | 타임라인 스크러버(E-1), 화면 요약 HUD와 주변 이벤트(G-5), Disaster Brief(G-3) | #10–#12 |
| M4 | 지도 조작 AI 에이전트(도구 호출, 토큰 하드캡), 채팅 패널 | #13, #14 |
| M5 | 지구관측 위성과 통과 예측(G-13), 항공기 ADS-B(G-11, PIA/LADD 제외), 선박 AIS(G-12, 키 필요) | #15–#17 |
| M6 | 공개 CCTV와 SSRF 방어 프록시(G-10), 텔레메트리 카드(G-15), 센서 보기 모드(G-14), 현지 라디오(G-18), 위험 인지 경로(G-19), 해저 케이블·우주 발사(G-20) | #18–#25 |
| M7 | 분쟁 지역 정책(§7), 운영 콘솔·단축키·추적 모드(G-9·G-16), Cesium 3D 부활(G-6), 3D 실고도 트랙(G-16), 카메라 커버리지(G-10), 음성·모니터링 도구 에이전트 | #26–#31 |

### 남은 작업과 선행 조건

| 항목 | 상태 | 필요한 것 |
|---|---|---|
| AI 에이전트 실모델 검증 | 스크립트 모델과 SDK 와이어 테스트로만 검증 | `ANTHROPIC_API_KEY` |
| 선박 실데이터 | 프로토콜만 검증(잘못된 키로 핸드셰이크) | `AISSTREAM_API_KEY`(무료) |
| 위험 구역 회피 경로 | 공개 Valhalla가 회피 면적을 둘레 10 km로 제한하여 경고만 제공 | 자체 호스팅 Valhalla(`VALHALLA_URL`), 공개 배포 전 Valhalla Discussions 공지 |
| 감시 인프라 지도(G-17), 군사 시설(G-20) | 미구현 | 자체 호스팅 Overpass(공개 Overpass는 웹사이트 백엔드 사용 금지) |
| 데이터센터, 낙뢰(G-20) | 채택 안 함 | PeeringDB AUP와 Blitzortung 약관이 재배포 금지. 다른 소스 필요 |
| CCTV 실시간 영상(HLS) | 스냅샷만 제공 | 스트림 가용성 확인(샘플 재생목록이 404), 세션 상한이 있는 HLS 프록시 |
| 3D 지형·건물, 3D Hangar(glTF), CCTV 3D 투영 | 키 없는 3D 지구본만 제공 | Cesium ion 토큰(`NEXT_PUBLIC_CESIUM_ION_TOKEN`), glTF 모델 라이선스 확인 |
| 지연 표시(분쟁 정책의 delay 모드) | grid·hide만 구현 | 위치 이력 저장(`track_points` 하이퍼테이블) |

### 결정이 필요한 사항

1. 공개 배포 시 키 발급: Anthropic, AISStream, 필요 시 Cesium ion.
2. 자체 호스팅 여부: Valhalla(경로 회피), Overpass(G-17 등).
3. 라이선스가 확인되지 않은 소스의 상업 배포 여부: CelesTrak, AISStream, Launch Library 2. 현재는 비상업으로 표시되어 있다.
