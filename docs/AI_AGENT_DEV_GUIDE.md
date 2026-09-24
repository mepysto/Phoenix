# Phoenix AI 에이전트 개발 지침 (v1.0)

> **작성일**: 2026-07-13
> **대상**: Phoenix 코드를 수정하는 모든 AI 에이전트(하위 성능 모델 포함) 및 신규 개발자
> **짝 문서**: [UPGRADE_MASTER_PLAN.md](./UPGRADE_MASTER_PLAN.md) — "무엇을" 만들지. 본 문서는 "어떻게" 만들지.
>
> **이 문서의 사용법**: 티켓 하나를 받으면 → §1 절대 규칙 확인 → 해당 SOP(§5~§10) 절차를 순서대로 실행 → §12 Definition of Done 체크 → 종료. **절차를 건너뛰거나 재해석하지 말 것.**

---

## 1. 절대 규칙 (위반 금지)

### 반드시 할 것 (MUST)

1. **파일을 수정하기 전에 반드시 그 파일 전체를 읽는다.**
2. **한 티켓에서는 티켓에 명시된 파일/기능만 수정한다.** 개선하고 싶은 다른 코드를 발견하면 수정하지 말고 보고만 한다.
3. 코드 변경 후 **반드시 검증 명령(§4.3)을 실행**하고, 실패하면 통과할 때까지 고친 뒤 종료한다.
4. 새 API 엔드포인트/스키마 변경 시 **OpenAPI 타입 재생성**(§4.4)을 수행한다.
5. UI에 새 문자열을 추가하면 **7개 언어 번역을 모두** `apps/web/src/lib/i18n/translations.ts`에 추가한다 (en, ko, es, fr, zh, ar, ru — 파일 내 실제 키 확인).
6. 모든 이벤트 목록 조회 쿼리에 `is_canonical == True` 필터를 포함한다 (중복 병합된 이벤트 노출 방지).
7. DB 스키마 변경은 **반드시 Alembic 마이그레이션으로만** 한다 (모델 파일만 고치고 끝내지 않는다).
8. 커밋 메시지는 Conventional Commits (`feat(api): ...`, `fix(web): ...`) 형식. 기존 `git log` 스타일을 따른다.

### 하지 말 것 (NEVER)

1. **NEVER** 저장소 루트에 파일 생성. 코드는 `apps/`·`packages/`, 문서는 `docs/`, 스크립트는 `scripts/`.
2. **NEVER** 시크릿/API 키를 코드나 커밋에 포함. 설정은 `apps/api/src/core/config.py`의 `Settings`에 필드 추가 + `.env.example`에 예시만 추가.
3. **NEVER** 요청받지 않은 문서 파일 생성.
4. **NEVER** 파일 하나를 500줄 초과로 작성. 초과하면 모듈 분리.
5. **NEVER** 외부 HTTP를 실제로 호출하는 테스트 작성. 반드시 mock (기존 `tests/services/test_gdacs_service.py` 패턴 참조).
6. **NEVER** `pip install` 직접 실행. 의존성은 `apps/api/pyproject.toml`에 추가 후 `uv sync`(또는 프로젝트 방식) / 프론트는 `pnpm add --filter web`.
7. **NEVER** 기존 공개 API의 응답 필드를 삭제·이름변경 (additive만 허용. breaking은 `/api/v2`).
8. **NEVER** 마이그레이션 파일을 수정하지 않는다 — 이미 커밋된 마이그레이션은 불변. 고칠 게 있으면 새 마이그레이션 추가.

---

## 2. 저장소 지도 — "이 작업은 어디를 고치는가"

```
phoenix/
├── apps/api/                        # FastAPI 백엔드 (Python 3.12, uvicorn 포트 28000)
│   ├── alembic/versions/            # DB 마이그레이션 (파일명: YYYY_MM_DD_HHMM-<rev>_<슬러그>.py)
│   ├── scripts/                     # 운영 CLI (seed_data.py, offline_merge.py 등)
│   ├── src/
│   │   ├── main.py                  # 앱 조립: 라우터 등록, lifespan(스케줄러 시작)
│   │   ├── core/config.py           # Settings (env 기반 설정) — 새 설정은 여기에만
│   │   ├── core/exceptions.py       # 커스텀 예외
│   │   ├── db/database.py           # SQLAlchemy 세션/Base
│   │   ├── models/                  # SQLAlchemy 모델 (event.py, admin_area.py)
│   │   ├── schemas/                 # Pydantic 응답/요청 스키마
│   │   ├── repositories/            # DB 접근 계층 (쿼리는 여기에만 작성)
│   │   ├── services/                # 비즈니스 로직
│   │   │   ├── connectors/          # 외부 데이터 소스 커넥터 (base.py 상속)
│   │   │   ├── dedup/               # 중복제거/병합 파이프라인
│   │   │   ├── normalization/       # 심각도/행정구역 정규화
│   │   │   ├── ingestion_service.py # 커넥터 → DB 저장 오케스트레이션
│   │   │   └── scheduler.py         # APScheduler 잡 등록 (sync_gdacs 등)
│   │   ├── api/v1/                  # FastAPI 라우터 (events, geodata, sync, admin, websocket)
│   │   └── utils/                   # geojson.py, geo.py
│   └── tests/                       # pytest (api/ 라우터 테스트, services/ 단위 테스트)
├── apps/web/                        # Next.js 15 App Router (포트 23000)
│   └── src/
│       ├── app/                     # 페이지 (page.tsx, layout.tsx, loading.tsx, error.tsx)
│       ├── components/layout/       # Header, Sidebar, Footer
│       ├── components/map/          # GlobeViewer(MapLibre), CesiumViewer, MapEngineWrapper
│       ├── lib/api/client.ts        # openapi-fetch 클라이언트 (schema.d.ts는 자동생성 — 손대지 말 것)
│       ├── lib/i18n/translations.ts # 7개 언어 UI 문자열
│       └── store/                   # zustand (eventStore, mapStore, settingsStore)
├── packages/shared/src/             # 프론트-공용 타입/상수 (EVENT_TYPE_COLORS 등)
├── infrastructure/docker/           # docker-compose (Postgres 5434, Redis 6381)
└── docs/                            # 모든 문서
```

### 계층 규칙 (백엔드)

```
api/v1(라우터) → services(로직) → repositories(쿼리) → models(테이블)
                 schemas(입출력 검증)는 라우터와 서비스에서 사용
```

- 라우터에 SQL/비즈니스 로직 작성 금지. 라우터는 파라미터 검증 + 서비스 호출 + 응답 변환만.
- 서비스에서 직접 SQLAlchemy 쿼리 작성 금지. repository 메서드를 호출.

---

## 3. 환경 정보 (정확한 값)

| 항목 | 값 |
|------|-----|
| 웹 개발 서버 | `http://localhost:23000` (`pnpm dev:web`) |
| API 서버 | `http://localhost:28000` (`pnpm dev:api`), 문서 `/docs` |
| PostgreSQL (docker) | 호스트 포트 **5434** (PostGIS + TimescaleDB) |
| Redis (docker) | 호스트 포트 **6381** |
| 인프라 기동 | `pnpm docker:up` / 종료 `pnpm docker:down` |
| DB 마이그레이션 | `pnpm db:migrate` (= `cd apps/api && alembic upgrade head`) |
| 시드 데이터 | `pnpm db:seed` |
| Python 가상환경 | `apps/api/.venv` (활성화: `source apps/api/.venv/bin/activate`) |
| 환경변수 | 루트 `.env.local` (커밋 금지), 예시는 `.env.example` |

---

## 4. 표준 명령어

### 4.1 개발 실행

```bash
pnpm docker:up          # DB/Redis 먼저
pnpm dev                # web + api 동시 (turbo)
```

### 4.2 백엔드 단독

```bash
cd apps/api
source .venv/bin/activate
uvicorn src.main:app --reload --port 28000
```

### 4.3 검증 명령 (티켓 종료 전 필수 — 전부 통과해야 함)

```bash
# 백엔드를 수정했다면:
cd apps/api && source .venv/bin/activate
ruff check src tests && ruff format --check src tests
mypy src
pytest                                  # 전체 통과 확인

# 프론트를 수정했다면:
cd apps/web
pnpm lint && pnpm typecheck
pnpm test:run

# 어느 쪽이든 마지막에 루트에서:
pnpm build
```

### 4.4 OpenAPI 타입 재생성 (API 스키마 변경 시 필수)

```bash
# API 서버가 28000에서 실행 중이어야 함
pnpm generate:types     # → apps/web/src/lib/api/schema.d.ts 갱신
```

`schema.d.ts`는 **자동 생성 파일이므로 절대 수동 편집 금지.**

---

## 5. SOP-1: 새 DB 모델 + 마이그레이션 추가

1. `apps/api/src/models/`에 모델 작성 (새 도메인이면 새 파일, 기존 도메인이면 해당 파일에 추가).
   - PK는 `UUID` + `uuid4` 기본값, 타임스탬프는 기존 Event 모델 패턴 복사.
   - **Enum은 반드시 `Enum(PyEnum, name="<snake_name>", create_type=False)`** — 이 프로젝트는 PG enum 타입을 마이그레이션에서 수동 생성한다.
2. `apps/api/src/models/__init__.py`에 export 추가 (alembic autogenerate가 인식하도록).
3. 마이그레이션 생성:
   ```bash
   cd apps/api && source .venv/bin/activate
   alembic revision --autogenerate -m "add_<대상>_table"
   ```
4. **생성된 마이그레이션 파일을 열어 검수** (autogenerate는 불완전):
   - PG enum 타입: `upgrade()` 첫 부분에 `sa.Enum(..., name="...").create(op.get_bind(), checkfirst=True)` 추가, `downgrade()` 마지막에 `.drop(...)` 추가.
   - Geometry 컬럼: `geoalchemy2` import 확인, 불필요한 자동 인덱스 중복 제거.
   - 파일명이 기존 규칙(`YYYY_MM_DD_HHMM-...`)과 일치하는지 확인.
5. 적용 및 왕복 테스트:
   ```bash
   alembic upgrade head
   alembic downgrade -1 && alembic upgrade head   # downgrade도 동작해야 함
   ```
6. 스키마 문서 갱신이 티켓에 명시된 경우에만 `docs/ARCHITECTURE.md` §8 갱신.

---

## 6. SOP-2: 새 API 엔드포인트 추가

1. **스키마 먼저**: `apps/api/src/schemas/`에 Pydantic 요청/응답 모델 정의.
   - 응답 모델에는 `model_config = ConfigDict(from_attributes=True)` (기존 `schemas/event.py` 패턴).
2. **Repository**: 필요한 쿼리 메서드를 `repositories/`에 추가. 이벤트 조회라면 `is_canonical == True` 필터 필수.
3. **Service**: `services/`에 비즈니스 로직. 외부 I/O는 여기서만.
4. **Router**: `api/v1/`의 해당 라우터에 엔드포인트 추가. 새 리소스면 새 라우터 파일 생성 후 `src/main.py`에 `include_router` 등록 (prefix는 `/api/v1/<리소스복수형>`).
   ```python
   @router.get("/{event_id}/timeline", response_model=TimelineResponse)
   async def get_event_timeline(
       event_id: UUID,
       db: AsyncSession = Depends(get_db),
   ) -> TimelineResponse:
       result = await timeline_service.get_timeline(db, event_id)
       if result is None:
           raise HTTPException(status_code=404, detail="Event not found")
       return result
   ```
5. **테스트**: `tests/api/test_<라우터>.py`에 최소 4개 — 정상(200), 없는 리소스(404), 잘못된 입력(422), 필터/경계값 1개. 기존 `tests/conftest.py`의 픽스처를 재사용.
6. §4.3 검증 → §4.4 타입 재생성 → 프론트에서 사용 시 `client.ts` 경유로만 호출.

---

## 7. SOP-3: 새 데이터 소스 커넥터 추가

> 마스터플랜 A-1 (IFRC GO, ReliefWeb, FIRMS, WHO, ACLED, EM-DAT)이 이 SOP를 사용한다.

1. `apps/api/src/services/connectors/base.py`를 **먼저 읽고** 추상 인터페이스 확인.
2. `connectors/<source>_connector.py` 생성. 기존 `usgs_connector.py`를 템플릿으로 복사해 시작.
   - 책임은 "fetch + parse + 정규화"까지만. **DB 저장 금지** (IngestionService 담당).
   - 좌표 없는 소스: `latitude/longitude=None`, `geo_precision="country"`, country_code 세팅 (admin centroid 폴백은 정규화 계층이 처리).
   - EventType 매핑 딕셔너리를 모듈 상수로 명시 (`SOURCE_TYPE_MAP = {...}`), 미지 값은 `EventType.other`.
3. `connectors/__init__.py`에 export 추가.
4. **시드 등록**: `scripts/seed_data.py`의 data_sources에 신규 소스 추가 (name, api_url, sync_interval_minutes).
5. **스케줄러 등록**: `services/scheduler.py`에 `sync_<source>()` 메서드 추가 — 기존 `sync_usgs()`를 그대로 본떠 재시도/에러 격리 로직 유지.
6. **설정**: API 키가 필요하면 `core/config.py`에 `<source>_api_key: str = ""` 추가 + `.env.example` 갱신. 키가 비어 있으면 커넥터는 조용히 skip하고 warning 로그.
7. **테스트** (`tests/services/test_<source>_connector.py`, 외부 HTTP는 전부 mock):
   - 정상 응답 파싱 / 빈 응답 / 필수 필드 누락 항목 skip / HTTP 오류 시 예외 처리 / EventType 매핑 경계값.
8. 수동 확인: `POST /api/v1/sync/<source>` (sync 라우터에 트리거 추가) 후 `GET /api/v1/events?source=<source>` 로 표출 확인.

---

## 8. SOP-4: 프론트 페이지/컴포넌트 추가

1. 페이지: `apps/web/src/app/<경로>/page.tsx`. 데이터 fetch가 있으면 Server Component 우선, 상호작용 부분만 `"use client"` 하위 컴포넌트로 분리 (기존 `page.tsx` + `MapPageClient.tsx` 패턴).
2. 같은 폴더에 `loading.tsx` 스켈레톤 추가 (기존 스타일 복사).
3. API 호출은 **반드시** `lib/api/client.ts`의 타입 클라이언트 경유. `fetch()` 직접 호출 금지.
4. 상태: 페이지-로컬은 `useState`, 크로스-컴포넌트는 기존 zustand 스토어 확장 (새 스토어 남발 금지 — 3개 스토어에 우선 편입 검토).
5. 새 UI 문자열 → `lib/i18n/translations.ts`에 7개 언어 키 추가 + `useTranslation()` 사용. 하드코딩 문자열 금지.
6. 스타일: Tailwind 유틸리티만. 신규 CSS 파일 생성 금지. 색상 등 상수는 `@phoenix/shared/constants` 재사용.
7. 내비게이션 추가가 티켓에 포함된 경우에만 `components/layout/Header.tsx` 수정.
8. 테스트: 로직이 있는 컴포넌트는 Vitest 테스트 (`__tests__/` 또는 기존 위치 규칙 따름), 신규 사용자 흐름이면 Playwright E2E 1개.

---

## 9. SOP-5: 지도 레이어/시각화 추가

1. 대상 엔진 결정: 기본은 **MapLibre**(`GlobeViewer.tsx`). Cesium(`CesiumViewer.tsx`)은 3D 전용 기능일 때만.
2. GlobeViewer에 추가할 때:
   - 소스/레이어 id는 `phoenix-<기능>` 접두사.
   - 레이어 on/off는 `mapStore`에 상태 추가 → `Sidebar.tsx` 레이어 패널에 토글 연결.
   - 스타일 상수(색상)는 `packages/shared/src/constants/index.ts`에 추가 (프론트 파일에 하드코딩 금지).
3. 데이터가 큰 레이어(>1000 피처)는 GeoJSON 전체 로드 금지 → 클러스터 API 또는 벡터타일 엔드포인트 사용.
4. 지도 기능은 자동 테스트가 어려우므로: zustand 스토어 로직은 단위 테스트, 시각 확인은 티켓 보고에 스크린샷 필수.

---

## 10. SOP-6: 테스트 작성 규칙

### 백엔드 (pytest)

- 위치: 라우터 테스트 `tests/api/`, 서비스/유틸 테스트 `tests/services/`.
- 픽스처: `tests/conftest.py` 재사용. DB 픽스처가 있으면 그대로 쓰고, 없으면 서비스는 repository를 mock.
- 외부 HTTP: `httpx` mock 또는 `respx`/`unittest.mock` — **기존 테스트가 쓰는 방식을 열어보고 동일하게** 사용.
- 스케줄러: `main.py` lifespan이 시작 시 sync를 실행하므로, 앱 픽스처는 반드시 스케줄러를 mock/비활성한 기존 conftest 패턴을 따를 것.
- 명명: `test_<대상>_<조건>_<기대>` 예: `test_list_events_excludes_non_canonical`.

### 프론트 (Vitest / Playwright)

- 컴포넌트: Testing Library로 렌더+상호작용 검증. 지도 엔진은 mock.
- 스토어: 액션 호출 → 상태 검증 (기존 `eventStore` 테스트 패턴).
- E2E: 핵심 사용자 흐름 1개당 1 spec. 셀렉터는 role/text 우선, `data-testid`는 최후 수단.

### 공통

- 버그 수정 티켓은 **재현 실패 테스트를 먼저 작성**하고(빨강), 수정 후 통과(초록)를 확인한다.
- 테스트를 통과시키기 위해 테스트를 약화(assertion 삭제, skip)하는 것 금지.

---

## 11. 티켓 규격 & 작업 절차

### 11.1 티켓 크기 원칙

- 1 티켓 = 1 SOP 이내로 완결 = 코드 변경 ≤ 400줄 = 검증 1회로 확인 가능.
- 마스터플랜의 기능 패키지(§13 매핑표)는 반드시 여러 티켓으로 분해한다. 분해 예:

```
[C1 시맨틱 매칭] →
  C1-1 pgvector 확장 + embedding 컬럼 마이그레이션        (SOP-1)
  C1-2 EmbeddingProvider 인터페이스 + API/로컬 구현 + 테스트 (SOP 없음: services/ 신규 모듈)
  C1-3 Need/Offer 저장 시 임베딩 생성 훅                   (SOP-2 일부)
  C1-4 GET /needs/{id}/matches 엔드포인트 + 재랭킹          (SOP-2)
  C1-5 프론트 매칭 후보 패널                               (SOP-4)
```

### 11.2 티켓 템플릿 (에이전트에게 줄 때 이 형식 사용)

```markdown
## 티켓: <ID> <제목>
### 목표 (한 문장)
### 관련 SOP: SOP-N
### 수정 대상 파일 (예상)
- apps/api/src/...
### 하지 말 것
- (이 티켓에서 건드리면 안 되는 인접 영역)
### 수용 기준 (체크리스트)
- [ ] ...
### 검증 명령
- (§4.3 중 해당 항목)
```

### 11.3 Definition of Done (모든 티켓 공통)

- [ ] 수용 기준 전부 충족
- [ ] §4.3 검증 명령 전부 통과 (실행 결과를 보고에 포함)
- [ ] API 스키마 변경 시 §4.4 타입 재생성 완료
- [ ] 새 UI 문자열의 7개 언어 번역 완료
- [ ] 마이그레이션 upgrade/downgrade 왕복 확인 (해당 시)
- [ ] 커밋 메시지 Conventional Commits 준수, 1티켓 = 1~3커밋
- [ ] 보고: 변경 파일 목록 + 검증 결과 + (UI 변경 시) 스크린샷

---

## 12. 함정 목록 (Gotchas) — 시행착오 방지

| # | 함정 | 올바른 처리 |
|---|------|------------|
| 1 | SQLAlchemy Enum이 `create_type=False` | 마이그레이션에서 PG enum을 수동 create/drop (SOP-1 4단계) |
| 2 | 이벤트가 병합되어 `is_canonical=False`일 수 있음 | 모든 목록/집계 쿼리에 canonical 필터. 상세 조회는 `merged_into_id` 따라 리다이렉트 고려 |
| 3 | 좌표가 NULL인 이벤트 존재 (국가 수준 소스) | 지도 표출은 `display_point`(location 또는 admin centroid) 사용, NULL이면 지도 스킵하되 목록엔 표시 |
| 4 | `schema.d.ts`는 자동 생성 | 손으로 고치면 다음 재생성 때 소실. API 쪽을 고칠 것 |
| 5 | 포트가 표준과 다름 (web 23000 / api 28000 / pg 5434 / redis 6381) | §3 표의 값만 사용. 5432/6379 가정 금지 |
| 6 | `GlobeViewer.tsx`에 MOCK_EVENTS 폴백 존재 | 지도에 데이터가 보인다고 API 연동 성공이라 판단하지 말 것. 네트워크 탭/API 직접 호출로 확인 |
| 7 | lifespan에서 시작 시 GDACS sync 실행 | 테스트/로컬에서 외부 호출 유발. 테스트는 conftest 패턴으로 차단, 새 startup 작업 추가 시 동일 고려 |
| 8 | `EventSource` upsert 유니크 키 = (source_id, external_id) | 커넥터가 external_id를 안정적으로(불변) 생성해야 중복 방지됨 |
| 9 | APScheduler는 프로세스 내장 | 잡 추가 시 멀티 워커 중복 실행 고려 (M1 이후 Redis 락 유틸 사용) |
| 10 | `datetime.utcnow` 사용 중 (deprecated) | 기존 파일은 그대로 두되, **새 코드는 `datetime.now(UTC)`** 사용 |
| 11 | Cesium은 번들이 매우 큼 | Cesium 관련 import는 반드시 dynamic import 유지. 공통 코드에 정적 import 추가 금지 |
| 12 | 모노레포 의존성 | 프론트 패키지 추가는 `pnpm add <pkg> --filter web`. 루트에 추가 금지 |
| 13 | i18n 키 누락 시 영어 폴백으로 조용히 넘어감 | 번역 추가 후 설정 페이지에서 언어 전환해 육안 확인 |
| 14 | `GeoLayer.geojson`은 문자열(Text) | `json.loads` 필요. B4 티켓 전까지 JSONB 가정 금지 |
| 15 | war/분쟁(ACLED) 데이터 | 정밀 좌표를 그대로 노출 금지 — `geo_precision`을 admin1로 강등하는 정책 적용 (마스터플랜 §11) |

---

## 13. 코딩 컨벤션 요약

### Python (`apps/api`)

- 포매터/린터: ruff (설정은 `pyproject.toml`). 타입힌트 100% — mypy 통과 필수.
- async 우선: 라우터/서비스/레포지토리는 `async def`, DB는 AsyncSession.
- 로깅: `logger = logging.getLogger(__name__)`, f-string 대신 lazy `%` 포맷 권장.
- 예외: 도메인 예외는 `core/exceptions.py`에 정의, 라우터에서 HTTPException으로 변환.
- docstring: 공개 서비스/커넥터 클래스와 복잡한 함수에만 한 줄 요약. 자명한 코드에 주석 금지.

### TypeScript (`apps/web`, `packages/`)

- strict 모드. `any` 금지 (불가피하면 `unknown` + narrowing).
- 컴포넌트는 함수형 + 명시적 Props 인터페이스. default export는 페이지 파일만.
- 서버/클라이언트 경계 명확히: `"use client"`는 필요한 최소 단위 컴포넌트에만.
- import 순서: react/next → 외부 라이브러리 → `@phoenix/*` → 상대경로.

### 공통

- 코드·식별자·주석은 영어, 사용자 대면 문자열은 i18n, 문서는 한국어(기존 관례).
- 매직 넘버 금지 — `packages/shared/src/constants` 또는 모듈 상수로.

---

## 14. 보고 형식 (티켓 완료 시)

```markdown
## 완료 보고: <티켓 ID>
- 결과: 성공 / 부분 성공(사유) / 차단(사유)
- 변경 파일: (목록)
- 검증: ruff ✅ / mypy ✅ / pytest 137 passed ✅ / pnpm build ✅   ← 실제 실행 결과만 기재
- 스키마 변경: 있음(마이그레이션 rev) / 없음
- 발견한 문제(이번 티켓 범위 밖): (있으면 목록 — 수정하지 않았음을 명시)
```

**허위 보고 금지**: 실행하지 않은 검증을 통과했다고 쓰지 않는다. 실패한 테스트가 있으면 실패 로그를 그대로 첨부한다.
