# Phoenix 차세대 업그레이드 마스터플랜 (v1.0)

> **작성일**: 2026-07-13
> **대상 독자**: 프로젝트 오너, 구현을 담당할 AI 에이전트/개발자
> **짝 문서**: [AI_AGENT_DEV_GUIDE.md](./AI_AGENT_DEV_GUIDE.md) — 본 플랜의 구현 지침(SOP·템플릿·티켓 규격)
> **선행 문서**: [PRD.md](../PRD.md), [PHASE2_NEEDS_OFFERS_CONNECT_DISCLOSURES_PLAN.md](./PHASE2_NEEDS_OFFERS_CONNECT_DISCLOSURES_PLAN.md), [HANDOFF_PIPELINE.md](./HANDOFF_PIPELINE.md)

---

## 0. 요약 (Executive Summary)

Phoenix는 Phase 1 MVP(글로벌 재난 이벤트 맵 + 멀티소스 인제션 + 중복제거)를 완료했다.
본 문서는 PRD의 비전("지구의 상처를 모두가 함께 고치는 디지털트윈")을 향해 **기능·성능·생태계를 동시에 끌어올리는 6개 트랙, 24개 기능 패키지**를 정의한다.

| 트랙 | 이름 | 핵심 산출물 | 우선순위 |
|------|------|------------|---------|
| A | 데이터 인텔리전스 완성 | 10개 소스 커넥터, 신뢰도 스코어, 이벤트 라이프사이클 | ★★★ |
| B | 성능·확장성 | 벡터타일 서버, 다층 캐시, 델타 스트리밍, p95 예산 달성 | ★★★ |
| C | 매칭 생태계 (Phase 2+) | Needs/Offers/Connect + AI 시맨틱 매칭 | ★★★ |
| D | AI 어시스턴트 | 이벤트 RAG Q&A, 자동 상황보고(SitRep), 연쇄 재난 예측(Cascade) | ★★ |
| E | 참여형 디지털트윈 | 타임라인 슬라이더, Before/After, 주석, 설계 시나리오 V1 | ★★ |
| F | 개방 생태계·신뢰 | 공개 API/웹훅, 임베드 위젯, 저대역폭 PWA, Phoenix Score | ★★ |
| 0 | 안정화 (선행) | 실사 결함 수정(P0 10건·P1·P2), 스키마 단일화, CI — [상세](./GODS_EYE_ADOPTION_PLAN.md) | ★★★ |
| G | God's Eye View 전면 채택 | 레이어 레지스트리, 통합 타임라인, 맵 에이전트, 감시·모니터링 계층(CCTV·항공·선박·위성), 운영센터 — [상세](./GODS_EYE_ADOPTION_PLAN.md) | ★★ |

**혁신 포인트 5가지** (기존 유사 플랫폼과의 차별화):

1. **Phoenix Score** — 이벤트별 "피해→대응→복구" 진행 상황을 0~100 지수로 정량화해 지도에 표시. 세계 최초의 "복구 진행률 지도".
2. **AI SitRep** — 멀티소스 데이터를 LLM이 종합해 UN 공용어 6개로 자동 상황보고서 발행. 인도주의 기관의 초기 3시간을 절약.
3. **시맨틱 매칭 엔진** — 니즈/오퍼를 임베딩 공간에서 매칭하고, 거리·물류·긴급도를 반영한 설명 가능한 점수 제공.
4. **Crisis Widget** — 언론사/NGO가 한 줄 스크립트로 자기 사이트에 심을 수 있는 실시간 재난 지도 위젯 → 유입 플라이휠.
5. **연쇄 재난 예측 엔진 (Cascade Risk Predictor)** — 1차 재난 정보와 지형/기상 데이터를 결합하여 산사태, 댐 붕괴 등 2차 연쇄 재난 위험도를 공간 AI로 예측.

---

## 1. 현황 진단 (2026-07 기준, 코드 기반 실사)

### 1.1 완료된 것 (강점)

| 영역 | 구현 상태 | 근거 (코드) |
|------|----------|------------|
| 멀티소스 인제션 | GDACS, Copernicus EMS, USGS, EONET 4개 소스 + 5분 스케줄러 | `apps/api/src/services/connectors/`, `scheduler.py` |
| 중복제거/병합 | strong key(GLIDE 등)·fuzzy 매칭·품질 점수·canonical 병합·자식 relink | `apps/api/src/services/dedup/` (7개 모듈) |
| 지오 정규화 | PostGIS Point + `geo_precision`/`geo_method` + admin_area centroid 폴백 | `models/event.py`, `normalization/` |
| API | Events/GeoData(클러스터·GeoJSON·MVT)/Sync/Admin/WebSocket | `api/v1/` 5개 라우터 |
| 3D 뷰어 | MapLibre Globe(기본) + CesiumJS(고급) 듀얼 엔진 스위칭 | `components/map/MapEngineWrapper.tsx` |
| 타입 안전성 | OpenAPI → openapi-typescript → openapi-fetch 자동 생성 | `web/src/lib/api/schema.d.ts` |
| 테스트 | 백엔드 113개(85% 커버리지) + 프론트 29개 + E2E 9개 | `apps/api/tests/`, Vitest, Playwright |
| i18n | 7개 언어 UI 번역 | `web/src/lib/i18n/translations.ts` |

### 1.2 갭 분석 (PRD 대비 미구현)

| PRD 요구 | 현재 상태 | 갭 심각도 |
|----------|----------|----------|
| FR-2.1 데이터 소스 (10종) | 4종만 연동. IFRC GO, ReliefWeb, FIRMS, WHO, ACLED, EM-DAT 미연동 | 높음 |
| FR-7.x 니즈–지원 매칭 | 기획 문서만 존재 (PHASE2 plan). 코드 0% | 높음 |
| FR-5.x AI 분석/어시스턴트 | 전무 | 높음 |
| FR-3.2 타임라인 (전/후 비교) | 미구현 (PROGRESS.md에서 선택 항목으로 스킵됨) | 중간 |
| FR-4.x 3D 복구 설계 | 전무 (PRD상 Phase 3) | 중간 |
| FR-8.1 인증/RBAC | 전무. Admin API도 `api_sync_key` 단일 키 | 높음 |
| NFR 성능 (100k TPS, 5s 로딩) | 측정 인프라 없음. 캐시 레이어 미사용(Redis 설정만 존재) | 중간 |
| NFR 접근성 (저사양/저속) | 미고려. Cesium 번들 무거움 | 중간 |

### 1.3 기술 부채 (즉시 수정 대상 — Track B에 포함)

1. **Redis가 설정만 있고 아무 데도 안 쓰임** — 캐시 0%.
2. **`datetime.utcnow` 사용** — Python 3.12+에서 deprecated. `datetime.now(UTC)`로 점진 전환.
3. **`GeoLayer.geojson`이 Text 컬럼** — 대용량 레이어에서 직렬화 비용 큼. JSONB 또는 PostGIS geometry로 전환 필요.
4. **이벤트 목록 API가 offset 페이지네이션** — 대량 데이터에서 성능 저하. keyset(cursor) 전환.
5. **프론트 `GlobeViewer.tsx`에 MOCK_EVENTS 하드코딩 잔존** — API 실패 시 mock 폴백은 데모엔 좋지만 프로덕션 오해 위험. 명시적 "데모 모드" 플래그로 전환.
6. **스케줄러가 앱 프로세스 내장(APScheduler)** — 멀티 워커 배포 시 중복 실행. 분산 락(Redis) 또는 전용 워커 프로세스 분리 필요.

---

## 2. 전략 목표 & North Star Metrics

### 2.1 North Star

> **"재난 발생 후 30분 안에, 세계에서 가장 신뢰할 수 있는 통합 상황판이 된다."**

### 2.2 목표 지표 (12개월)

| 지표 | 현재 | 목표 | 측정 방법 |
|------|------|------|----------|
| 연동 데이터 소스 수 | 4 | 10 | `data_sources` 테이블 active 카운트 |
| 이벤트 최초 감지 → 표출 지연 | ~5분 | < 2분 (실시간 소스) | `event_sources.fetched_at - 소스 발행시각` |
| 중복 이벤트율 (동일 재난 다중 표출) | 측정 안 됨 | < 3% | 주간 오프라인 머지 리포트 |
| API p95 응답 (이벤트 목록) | ~2ms(로컬) | < 150ms (프로덕션, 캐시 히트 시 < 20ms) | 미들웨어 메트릭 + Grafana |
| 초기 지도 렌더 (3G Fast) | 미측정 | < 3.5s LCP | Lighthouse CI |
| 니즈→커넥트 성사 리드타임 | N/A | < 72시간 중앙값 | `connect_requests.approved_at - needs.created_at` |
| 외부 임베드 위젯 도메인 수 | 0 | 50+ | 위젯 로드 텔레메트리 |

---

## 3. Track A — 데이터 인텔리전스 완성

### A-1. 커넥터 6종 추가 (IFRC GO, ReliefWeb, FIRMS, WHO, ACLED, EM-DAT)

기존 `BaseConnector` 패턴(`services/connectors/base.py`)을 그대로 따른다. 각 커넥터는 독립 티켓으로 분리 가능(하위 모델 구현에 최적).

| 소스 | 데이터 | 좌표 | 주기 | 특이사항 |
|------|--------|------|------|---------|
| IFRC GO | 적십자 재난 대응/어필 | 국가 수준 | 30분 | `geo_precision=country`, admin_centroid 폴백 |
| ReliefWeb | 재난 보고서/뉴스 | 국가 수준 | 30분 | 이벤트가 아닌 **문서** → 기존 이벤트에 `Dataset`으로 연결 우선 |
| NASA FIRMS | 위성 화재 감지 포인트 | 정밀 좌표 | 15분 | 포인트가 대량(수천/일) → 개별 Event가 아니라 wildfire 이벤트의 **GeoLayer**로 집계 저장 |
| WHO | 질병 발생(Disease Outbreak News) | 국가 수준 | 6시간 | `EventType.epidemic` |
| ACLED | 분쟁 이벤트 | 정밀 좌표 | 24시간 | API 키 필요. `EventType.war`. 민감도 정책(§7) 적용 |
| EM-DAT | 재난 통계(과거) | 국가 수준 | 주 1회 | 백필용. 실시간 아님 |

**수용 기준(각 커넥터 공통)**:
- [ ] `fetch_events()` 가 정규화된 `NormalizedEvent` 리스트 반환
- [ ] 외부 HTTP는 목킹된 단위 테스트 ≥ 5개 (정상/빈응답/필드누락/타임아웃/스키마변형)
- [ ] `data_sources` 시드 등록 + 스케줄러 잡 등록
- [ ] 기존 dedup 파이프라인 통과 (GLIDE/strong key 우선)

### A-2. 소스 신뢰도 & 크로스 검증 스코어 (혁신)

동일 이벤트를 여러 소스가 보고할수록 신뢰도가 올라가는 **confidence score**를 도입한다.

```
confidence = base(source_tier) + 0.15 × (독립 소스 수 - 1) + freshness_decay
  - source_tier: GDACS/USGS=0.6, Copernicus=0.6, EONET=0.5, ReliefWeb=0.4 ...
  - 상한 1.0, 하한 0.1
  - freshness_decay: 마지막 확인 후 24h마다 -0.05 (활성 이벤트만)
```

- DB: `events.confidence_score FLOAT`, `events.source_count INT` (dedup 병합 시 갱신)
- API: 이벤트 응답에 `confidence_score`, `sources[]` 노출
- UI: 마커 투명도/뱃지("3개 소스 확인됨")로 표현

### A-3. 이벤트 라이프사이클 상태 머신

현재 `is_active` bool 하나로는 "대응 중/복구 중/종료"를 표현 못 한다.

```
detected → verified → responding → recovering → closed
                    ↘ false_alarm(종료)
```

- DB: `events.lifecycle_status ENUM`, `event_status_history` 테이블(전이 이력, TimescaleDB 하이퍼테이블 후보)
- 전이 규칙: 소스 데이터 기반 자동(예: GDACS 알림 해제 → recovering) + Admin API 수동 전이
- `is_active`는 하위호환용 파생값으로 유지(`lifecycle_status NOT IN (closed, false_alarm)`)

### A-4. 이벤트 타임라인 API (TimescaleDB 활용 개시)

`event_metrics` 하이퍼테이블은 있으나 실사용 0. 여기에 시계열을 적재해 타임라인 UI(Track E)의 데이터 소스로 쓴다.

- 적재 항목: 심각도 변화, 영향 인구 추정 변화, 소스 수, FIRMS 화점 수, Copernicus AOI 면적
- API: `GET /api/v1/events/{id}/timeline?metric=...&from=...&to=...` (time_bucket 집계)

---

## 4. Track B — 성능·확장성

### 4.1 성능 예산표 (Performance Budget)

| 구간 | 예산 (p95) | 측정 도구 |
|------|-----------|----------|
| `GET /api/v1/events` (필터 포함) | 150ms / 캐시 히트 20ms | 자체 타이밍 미들웨어 |
| `GET /geodata/events/clusters` | 200ms | 〃 |
| 벡터타일 1장 (z0–z8) | 80ms (사전 생성 시 10ms) | 〃 |
| WebSocket 이벤트 브로드캐스트 지연 | 500ms | 브로드캐스터 테스트 |
| 웹 첫 렌더 LCP (Fast 3G) | 3.5s | Lighthouse CI (GitHub Actions) |
| 웹 JS 초기 번들 (Cesium 제외) | < 350KB gzip | `next build` 리포트 |
| Cesium 엔진 | 사용자가 3D 고급 모드 선택 시에만 lazy load | dynamic import 확인 |

### B-1. 다층 캐시 도입 (Redis 실사용 개시)

```
클라이언트 ─ ETag/Cache-Control ─→ CDN/브라우저
API      ─ Redis (키: 쿼리 정규화 해시, TTL 60s) ─→ PostgreSQL
무효화    ─ 인제션 파이프라인이 이벤트 upsert 시 관련 키 태그 삭제
```

- 대상: 이벤트 목록, 클러스터, GeoJSON export, 타일
- 구현: FastAPI 의존성 `cache(ttl, tags)` 데코레이터 1개로 통일 (SOP-7 참조)
- ETag: 응답 본문 해시 → `304 Not Modified` 지원

### B-2. 벡터타일 고도화 (PostGIS `ST_AsMVT`)

현재 타일 엔드포인트를 `ST_AsMVT` 기반으로 재구현하고, 저줌(z0–z6)은 이벤트 수가 적으므로 **인제션 후 사전 생성(Redis 저장)**, 고줌은 온디맨드+캐시.

- 레이어: `events`(포인트) + `event_areas`(Copernicus AOI 폴리곤)
- 프론트: MapLibre 소스를 GeoJSON 전체 로드 → 벡터타일로 교체 (이벤트 1만 개 이상 규모 대비)

### B-3. WebSocket 델타 스트리밍

현재 브로드캐스터를 확장: 전체 목록 push가 아니라 `{op: "upsert"|"remove", event: {...}}` 델타만 전송. 클라이언트 zustand 스토어가 델타 적용. 재접속 시 `since` 파라미터로 놓친 델타 재전송(Redis Stream 24h 보관).

### B-4. 쿼리·스키마 최적화

- keyset pagination (`?after=<cursor>` = start_date+id 복합 커서)
- 복합 인덱스: `(is_canonical, is_active, type, severity, start_date DESC)` — 목록 쿼리 커버링
- `GeoLayer.geojson` Text → JSONB 마이그레이션 + 크기 상한(5MB) 검증
- 모든 목록 API에 `is_canonical = true` 필터 기본 적용 (누락 시 중복 노출 버그)

### B-5. 스케줄러 분리 & 분산 락

- `SCHEDULER_ENABLED` env 플래그 → API 워커와 스케줄러 워커 분리 실행 가능
- Redis `SET NX EX` 분산 락으로 잡 중복 실행 방지 (멀티 레플리카 안전)

### B-6. 관측성 (Observability)

- `/metrics` Prometheus 엔드포인트 (요청 수/지연/캐시 히트율/싱크 성공률)
- 구조화 로깅(JSON) + request_id 전파
- Grafana 대시보드 JSON을 `infrastructure/grafana/`에 커밋

---

## 5. Track C — 매칭 생태계 (Phase 2 계획 + AI 확장)

기반은 기존 [PHASE2 계획](./PHASE2_NEEDS_OFFERS_CONNECT_DISCLOSURES_PLAN.md)을 **그대로 승계**한다(매직링크 인증, Org 승인, Needs/Offers/Connect/Disclosure). 본 플랜은 그 위에 3가지를 추가한다.

### C-1. 시맨틱 매칭 엔진 (혁신)

키워드/태그 매칭의 한계("겨울 텐트" vs "방한 쉘터")를 임베딩으로 해결한다.

**아키텍처** (외부 의존 최소화, 하위 모델도 구현 가능하게 단순화):

```
Need/Offer 저장 시 → 임베딩 생성(title+description+tags)
                   → pgvector 컬럼에 저장 (needs.embedding vector(1024))
매칭 조회 시       → 코사인 유사도 상위 50 → 재랭킹(규칙 기반) → 상위 10 반환
```

**재랭킹 점수(설명 가능해야 함 — UI에 근거 표시)**:

```
score = 0.45 × semantic_similarity
      + 0.20 × geo_proximity      (동일 이벤트 > 동일 국가 > 인접국 > 기타)
      + 0.15 × urgency_match      (need.priority vs offer 가용 시점)
      + 0.10 × quantity_fit       (min(offer.qty/need.qty, 1))
      + 0.10 × org_trust          (승인 Org·과거 완료 이력)
```

- 임베딩 프로바이더는 인터페이스로 추상화 (`EmbeddingProvider`): 기본 구현은 API 호출(Voyage/OpenAI 호환), 오프라인 폴백은 fastembed(ONNX 로컬). env로 선택.
- DB: `CREATE EXTENSION vector;` + HNSW 인덱스
- API: `GET /api/v1/needs/{id}/matches` → `[{offer, score, score_breakdown}]`

### C-2. 니즈 자동 초안 (AI-assisted intake)

승인 기관 담당자가 자유 텍스트/보고서 URL을 붙여넣으면 LLM이 구조화된 Need 초안(수량·단위·우선순위·태그)을 생성 → 사람이 확인 후 저장. **자동 등록은 절대 하지 않음**(human-in-the-loop 원칙).

### C-3. 매칭 알림 & 다이제스트

- Connect 상태 변화 시 이메일 알림 (매직링크 인프라 재사용)
- Org 대상 주간 다이제스트: "귀 기관 니즈에 신규 매칭 후보 N건"

---

## 6. Track D — AI 어시스턴트 & 자동 상황보고

### D-1. 이벤트 RAG Q&A ("Phoenix Copilot")

이벤트 상세 페이지에 채팅 패널. 컨텍스트는 **해당 이벤트의 DB 데이터만** 사용(환각 억제):

```
컨텍스트 조립: event + sources[].raw_data 요약 + geo_layers 메타 + datasets + timeline
시스템 프롬프트: "제공된 데이터에 없는 내용은 '데이터 없음'이라고 답하라. 모든 답변에 출처 소스명 표기."
```

- 백엔드: `POST /api/v1/events/{id}/ask` (SSE 스트리밍)
- LLM 프로바이더 추상화(`LLMProvider`) — Claude API 기본, env로 교체 가능
- 모든 응답 하단에 "AI 생성 — 출처: GDACS, Copernicus" 고지 (윤리 요건 §7)

### D-2. AI SitRep — 자동 상황보고서 (혁신, 플래그십 기능)

심각도 high/critical 이벤트에 대해 발생 직후 + 매 12시간 자동 발행:

- 구성: 개요 / 피해 현황(소스별) / 대응 현황 / 등록된 니즈 요약 / 데이터 출처와 신뢰도
- 다국어: UN 공용어 6개 (영어 원문 생성 → 번역 체인)
- 저장: `sitreps` 테이블 (event_id, version, lang, content_md, generated_at, model)
- 노출: 이벤트 상세 탭 + `GET /events/{id}/sitreps` + RSS 피드
- **검증 루프**: 발행 전 self-check 프롬프트(수치가 컨텍스트에 실존하는지 검증) → 실패 시 발행 보류 + Admin 큐

### D-3. 피해 분석 (BDA) 로드맵 — 이번 사이클엔 "연결"만

위성 영상 딥러닝 BDA(xView2 계열)는 인프라 비용이 크므로, 이번 사이클에서는:
1. Copernicus EMS의 **기존 피해 평가 산출물**(이미 수집 중)을 이벤트 상세에 구조화 표출
2. `damage_assessments` 테이블 스키마만 선제 설계 (Phase 4에서 자체 모델 주입 가능하게)

### D-4. 연쇄 재난 예측 엔진 (Cascade Risk Predictor, 초혁신)

지진, 홍수 등 대규모 1차 재난이 발생했을 때 시공간 데이터와 지형정보(PostGIS DEM/slope), 기상 데이터(실시간 강수량)를 LLM 및 공간 AI와 결합하여 산사태, 추가 홍수, 댐 붕괴 등 2차 연쇄 재난(Cascade Effect)의 위험도를 시뮬레이션 및 예측합니다.

- **구현 방식**:
  - **데이터 파이프라인**: USGS(지진), Copernicus(지질), EONET/기상청(강수량) 및 PostGIS DEM(디지털 고도 모델) 데이터를 공간 레이어로 오버레이합니다.
  - **공간 분석 계층**: PostGIS의 공간 연산(버퍼, 경사도 분석 등)을 이용해 1차 재난 영향 영역 내 경사도가 급하고 강수량이 누적된 취약 구역을 필터링합니다.
  - **AI 추론 모듈**: `LLMProvider` 및 공간 추론 프롬프트를 연동하여 위험 등급(Green/Yellow/Red)과 위험도 점수(0~100)를 산정하고 텍스트 기반의 위험인자 분석을 생성합니다.
  - **API**: `GET /api/v1/events/{id}/cascade-risks` -> `{status, risks: [{type: "landslide", risk_level: "high", score: 85, geometry: "MULTIPOLYGON...", reason: "..."}]}`
  - **UI 시각화**: MapLibre에 예측된 위험 영역(Polygon/Heatmap Layer)을 visual overlay로 렌더링하고, 사이드바 패널을 통해 발생 가능성이 높은 연쇄 재난 목록과 인자 분석 리포트를 제공합니다.

---

## 7. Track E — 참여형 디지털트윈

### E-1. 타임라인 슬라이더 (PROGRESS.md 미완 항목 해소)

- 지도 하단 시간 슬라이더: 기간 내 이벤트를 시점별 필터 + 재생(애니메이션)
- 데이터: 기존 `start_date`/`end_date` + Track A-4 타임라인 API
- MapLibre 필터 표현식으로 클라이언트 필터링(추가 API 불필요, 성능 안전)

### E-2. Before/After 비교 뷰

- Copernicus AOI 폴리곤이 있는 이벤트에서 위성 타일 2장을 스와이프 비교 (maplibre-compare 패턴)
- 소스: Sentinel-2 공개 타일(재난 전) vs Copernicus 산출물(재난 후)

### E-3. 커뮤니티 주석 (Annotations) V1

- 로그인 사용자가 지도에 포인트/폴리곤 + 텍스트 주석 (예: "이 다리 통행 불가 확인")
- 신뢰 모델: 일반 사용자 주석은 `unverified`, 승인 Org 멤버 확인 시 `verified` 뱃지
- DB: `annotations` (event_id, geom, body, status, created_by, verified_by)
- 남용 방지: rate limit(사용자당 10/일) + Admin 숨김 처리 + 신고

### E-4. 복구 설계 시나리오 V1 (PRD FR-4의 최소 단면)

풀 3D 모델링 툴 대신, **실행 가능한 최소 단면**부터:
- 이벤트에 "시나리오" 생성 → 지도 위에 오브젝트 팔레트(쉼터/급수/의료/도로차단 해제 등 10종 아이콘) 배치
- 자동 KPI 계산: 배치된 쉼터 수용 인원 합계, 최근접 급수시설 평균 거리(PostGIS)
- 시나리오 포크/댓글/투표 (Phase 2 인증 재사용)
- 3D 오브젝트 배치(Cesium glTF)는 V2로 연기 — 데이터 모델은 3D 좌표 확장 가능하게 설계(`position: {lng, lat, alt?}`)

---

## 8. Track F — 개방 생태계 & 신뢰

### F-1. 공개 API 프로그램

- API 키 발급(셀프서브, 이메일 인증) + rate limit (익명 60rpm / 키 600rpm, Redis 카운터)
- `GET /api/v1/...` 읽기 전용 공개, 문서 포털(`/docs` 확장 + 예제 갤러리)
- OpenAPI 스펙 버저닝 정책: additive만 허용, breaking은 `/api/v2`

### F-2. 웹훅 & 알림 구독

- 구독 조건: 지역(bbox/국가) × 유형 × 최소 심각도
- 채널: 웹훅(HMAC 서명), 이메일
- DB: `subscriptions`, `deliveries`(재시도 3회 지수 백오프)

### F-3. Crisis Widget (임베드 위젯, 혁신)

```html
<script src="https://phoenix.example/widget.js"
        data-region="global" data-types="earthquake,flood" data-lang="ko"></script>
```

- iframe 기반, 30KB 미만 로더 + 경량 2D 지도(Cesium 미포함)
- 위젯 하단 "Powered by Phoenix" → 본 서비스 유입 플라이휠
- 언론사·NGO·학교가 1차 타깃

### F-4. 저대역폭 모드 & PWA (NFR 접근성 요건)

- `/lite` 라우트: 지도 없이 텍스트/표 중심 이벤트 목록 (총 전송 < 100KB)
- PWA: 서비스워커로 마지막 동기화 데이터 오프라인 열람
- 자동 감지: `navigator.connection.effectiveType`이 2g/3g면 lite 제안 배너

### F-5. Phoenix Score (혁신, 브랜드 자산)

이벤트별 복구 진행 지수(0~100). 초기 산식은 단순·투명하게:

```
PhoenixScore = 100 × w1·(라이프사이클 단계 진척)
             + w2·(니즈 충족률: 승인된 Connect 수량 / 등록 니즈 수량)
             + w3·(공시(Disclosure) 최신성)
w1=0.5, w2=0.35, w3=0.15  — 산식과 가중치를 공개 문서화 (신뢰 확보)
```

- UI: 이벤트 카드/상세에 불사조 게이지. 지도 모드 "복구 현황 보기" 추가
- 데이터가 없으면 "산정 불가" 표시 (가짜 정밀도 금지)

---

## 9. 아키텍처 진화 방향

```
                        ┌─────────────────────────────┐
                        │  Next.js Web (+ /lite, PWA) │
                        │  MapLibre ⇄ Cesium (lazy)   │
                        └──────┬───────────┬──────────┘
                          REST/SSE      WS 델타
                        ┌──────┴───────────┴──────────┐
                        │        FastAPI (API 워커)     │
                        │  캐시 미들웨어 · RateLimit ·   │
                        │  Auth(매직링크/API키) · /metrics│
                        └──┬────────┬─────────┬────────┘
                    ┌──────┴──┐ ┌───┴────┐ ┌──┴───────────┐
                    │PostgreSQL│ │ Redis  │ │ AI 서비스 계층 │
                    │ PostGIS  │ │ 캐시/락 │ │ LLMProvider   │
                    │ Timescale│ │ Stream │ │ Embedding     │
                    │ pgvector │ └────────┘ │ (외부 API 추상화)│
                    └──────────┘            └──────────────┘
                        ▲
                ┌───────┴─────────┐
                │ 스케줄러 워커(분리) │  ← 10개 커넥터, dedup, SitRep 생성, 타일 사전생성
                └─────────────────┘
```

원칙: **모놀리스 유지 + 프로세스 역할 분리**(API/스케줄러). 마이크로서비스 분해는 트래픽 근거가 생기기 전까지 하지 않는다. 새 인프라 의존은 pgvector 확장 1개뿐(별도 DB 추가 금지).

---

## 10. 로드맵 & 마일스톤

각 마일스톤은 독립 배포 가능해야 하며, 티켓 분해 규칙은 [AI_AGENT_DEV_GUIDE.md](./AI_AGENT_DEV_GUIDE.md) §11을 따른다.

### M1 — 기반 다지기 (기술부채 + 성능 코어) : 3~4주

> B-1 캐시, B-4 쿼리 최적화, B-5 스케줄러 분리, B-6 관측성, §1.3 부채 6건

### M2 — 데이터 인텔리전스 : 3~4주

> A-1 커넥터 6종(각각 독립 티켓), A-2 신뢰도 스코어, A-3 라이프사이클, A-4 타임라인 API

### M3 — 인증 & 매칭 코어 (기존 Phase 2 계획 실행) : 4~6주

> 매직링크 인증, Org/승인, Needs/Offers/Connect/Disclosure CRUD — PHASE2 문서 §2~4 그대로

### M4 — AI 레이어 : 3~4주

> C-1 시맨틱 매칭, C-2 니즈 초안, D-1 RAG Q&A, D-2 SitRep, D-4 연쇄 재난 예측

### M5 — 참여 & 시각화 : 3~4주

> E-1 타임라인 슬라이더, E-2 Before/After, E-3 주석, B-2 벡터타일, B-3 WS 델타

### M6 — 개방 생태계 : 3~4주

> F-1 API 키, F-2 웹훅, F-3 위젯, F-4 lite/PWA, F-5 Phoenix Score, E-4 시나리오 V1

### 우선순위 원칙 (충돌 시 판단 기준)

1. 신뢰(데이터 정확성·중복 제거·출처 표기) > 기능 수
2. 이미 계획된 것(Phase 2) > 새 아이디어
3. 측정 가능한 것부터 (관측성 없이 최적화 금지)
4. AI 기능은 반드시 human-in-the-loop + 출처 표기

---

## 11. 리스크 & 대응

| 리스크 | 확률 | 영향 | 대응 |
|--------|------|------|------|
| 외부 API 정책 변경/차단 (ACLED 등 키 필요 소스) | 중 | 중 | 커넥터별 독립 실패 격리(이미 구현된 consecutive_failures 활용), 소스별 활성 플래그 |
| LLM 비용 폭증 | 중 | 중 | SitRep은 high/critical만, Q&A rate limit, 응답 캐시, 저비용 모델 라우팅 |
| AI 환각으로 잘못된 재난 정보 유포 | 저 | **치명** | 컨텍스트 한정 RAG, self-check 게이트, 출처 표기 강제, 수치는 원본 데이터만 인용 |
| 분쟁 지역 데이터 민감성 (ACLED/war) | 중 | 높음 | war 유형은 좌표를 admin1 수준으로 강제 강등(`geo_precision` 정책), 정밀 좌표 비공개 |
| 니즈/오퍼 스팸·사기 | 중 | 높음 | Org 승인제(기존 계획) + 신고 + Admin 큐, 이메일은 Connect 승인 후만 교환 |
| pgvector/임베딩 운영 미경험 | 중 | 저 | EmbeddingProvider 추상화로 교체 가능, 실패 시 태그 매칭 폴백 |
| 단일 DB 병목 | 저 | 중 | M1 관측성으로 조기 감지, 읽기 레플리카는 근거 확보 후 |

---

## 12. 비범위 (Non-Goals, 이번 사이클)

- 블록체인 기부 추적 (PRD V3 항목 유지 — 공시(Disclosure)로 투명성 우선 확보)
- 자체 위성영상 딥러닝 BDA 학습 (D-3에서 스키마만 준비)
- Unreal Engine 시뮬레이션
- 결제/펀딩 처리 (매칭은 "연결"까지만 — Phase 2 정책 유지)
- 네이티브 모바일 앱 (PWA로 대체)

---

## 13. 부록: 기능 패키지 → 티켓 매핑 인덱스

구현 착수 시 아래 ID로 티켓을 생성한다. 티켓 규격·SOP는 [AI_AGENT_DEV_GUIDE.md](./AI_AGENT_DEV_GUIDE.md) 참조.

| 패키지 ID | 이름 | 예상 티켓 수 | 의존성 |
|-----------|------|------------|--------|
| B1 | Redis 캐시 계층 | 4 | 없음 |
| B4 | 쿼리/스키마 최적화 | 5 | 없음 |
| B5 | 스케줄러 분리 | 2 | B1 |
| B6 | 관측성 | 3 | 없음 |
| A1-a~f | 커넥터 6종 | 6×2 | 없음 (병렬 가능) |
| A2 | 신뢰도 스코어 | 3 | A1 일부 |
| A3 | 라이프사이클 | 4 | 없음 |
| A4 | 타임라인 API | 3 | A3 |
| AUTH | 매직링크+Org (Phase 2 §2.1~2.2) | 8 | 없음 |
| C0 | Needs/Offers/Connect/Disclosure (Phase 2 §2.4) | 12 | AUTH |
| C1 | 시맨틱 매칭 | 5 | C0 |
| C2 | 니즈 AI 초안 | 3 | C0, D공통 |
| D0 | LLM/Embedding Provider 공통 계층 | 3 | 없음 |
| D1 | RAG Q&A | 4 | D0 |
| D2 | SitRep | 5 | D0, A3 |
| D4 | 연쇄 재난 예측 (Cascade) | 5 | D0, A4 |
| E1 | 타임라인 슬라이더 | 3 | A4 |
| E2 | Before/After | 3 | 없음 |
| E3 | 주석 | 5 | AUTH |
| E4 | 시나리오 V1 | 6 | AUTH |
| B2 | 벡터타일 | 4 | B1 |
| B3 | WS 델타 | 3 | B1 |
| F1 | API 키 | 4 | B1 |
| F2 | 웹훅 | 4 | F1 |
| F3 | 위젯 | 4 | B2 |
| F4 | lite/PWA | 4 | 없음 |
| F5 | Phoenix Score | 3 | A3, C0 |
