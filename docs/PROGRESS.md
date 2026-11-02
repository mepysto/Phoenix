# Phoenix - Development Progress

> **Last Updated**: 2026-11-02  
> **Status**: Phase 1, Track 0/G and Phase 2 (community, planning, alerts) shipped; production deploy tooling ready

---

## 2026-11 update — from "see" to "act"

Phase 1 and the God's Eye View track (M0–M7, PR #1–#38) are complete; see
[GODS_EYE_ADOPTION_PLAN.md](./GODS_EYE_ADOPTION_PLAN.md). This round added:

- [x] Event confidence score and lifecycle stage (Master plan A-2, A-3), derived on read
- [x] Situation report per event, 7 languages, no language model
- [x] Before/after satellite comparison (PRD FR-3.2)
- [x] New visual identity, 3D intro globe, accessibility fixes (WCAG AA contrast, focus handling)
- [x] Sign-in by emailed link; organisations with admin approval (PRD FR-8.1, basic)
- [x] Needs, offers, explainable matching, two-sided connections, disclosures (PRD FR-7.1–7.3, Phase 2 plan)
- [x] Relief site planner against Sphere minimum standards (PRD FR-4.1, FR-4.3 basic)
- [x] Area alerts, /lite text page, /embed widget (Master plan F, PRD NFR-6)

- [x] Copernicus EMS damage assessments per event (FR-5.1, expert grading; no Phoenix model)
- [x] Site plans saved with version history, forks, attached to needs (FR-4.2)
- [x] Closed-tab area alerts (Web Push, opt-in) and an installable app with offline /lite (NFR-6)

- [x] Verified-partner badges and personal contribution badges (FR-6.2)
- [x] Design challenges: entries, votes, host selection (PRD scenario 2, recovery design hackathon)

Then, to run it and to make it pleasant to use (PR #41–#42 and the follow-up on `main`):

- [x] One-command setup (`scripts/setup.sh`): development, or production with HTTPS (Caddy), backups and restore — see [DEPLOYMENT.md](./DEPLOYMENT.md)
- [x] UI/UX pass: filters on phones and tablets, map icon toolbar, working light theme with a light basemap,
      header language picker, readable badges, one date style, quick actions on event pages, RTL-safe map
      overlays, shared loading and empty states
- [x] Overview dashboard (`/dashboard`, `GET /api/v1/stats/overview`): people affected, active events,
      weekly onsets, severity split, types, most affected events, community activity — aggregated in SQL,
      public data only; every chart has a hover/focus readout and a table view; severity colours re-chosen
      to pass a colour-vision check (low is blue, not green)

Testing: 674 API tests (incl. PostGIS integration), 159 web unit tests, 11 Playwright end-to-end tests;
map rendering benchmark in `apps/web/scripts/perf-map.mjs` (see 6.3).

Still open: Phoenix's own AI damage model (FR-5.1 beyond Copernicus grading; plan and prerequisites in
[AI_DAMAGE_MODEL_PLAN.md](./AI_DAMAGE_MODEL_PLAN.md)), funding and
logistics tracking (FR-7.3, out of scope for now).

## Overview

이 문서는 Phoenix의 개발 진행 상황을 추적합니다. 아래 체크리스트는 Phase 1 MVP 기준이고, 이후 작업은 위 업데이트 절에 정리했습니다.  
각 기능과 작업 항목의 완료 상태를 체크하여 진척도를 파악할 수 있습니다.

### Progress Summary

| Category                 | Progress | Status    |
| ------------------------ | -------- | --------- |
| **Infrastructure Setup** | 10/10    | Completed |
| **Backend API**          | 14/14    | Completed |
| **Frontend Web**         | 16/16    | Completed |
| **3D Globe Viewer**      | 15/15    | Completed |
| **Data Integration**     | 10/10    | Completed |
| **Testing & QA**         | 6/6      | Completed |
| **Documentation**        | 5/5      | Completed |
| **Advanced Features**    | 10/10    | Completed |

**Overall Progress**: 92/92 tasks (100%)

---

## Phase 1: Infrastructure Setup

### 1.1 Monorepo Configuration

- [x] Root `package.json` 생성
- [x] `pnpm-workspace.yaml` 설정
- [x] `turbo.json` 파이프라인 설정
- [x] `.npmrc` pnpm 설정
- [x] `.gitignore` 설정
- [x] `.env.example` 환경변수 템플릿

### 1.2 Docker Environment

- [x] `docker-compose.yml` (개발 환경)
- [x] PostgreSQL + TimescaleDB 컨테이너 (Port 5434)
- [x] Redis 컨테이너 (Port 6381)
- [x] FastAPI Dockerfile
- [x] Next.js Dockerfile
- [x] 개발 환경 실행 테스트

### 1.3 Database Setup

- [x] PostGIS 확장 활성화 (init-db.sql)
- [x] TimescaleDB 확장 활성화 (init-db.sql)
- [x] 초기 스키마 마이그레이션 (init-db.sql)
- [x] Seed 데이터 스크립트 (scripts/seed_data.py - 12개 이벤트, 17개 레이어, 6개 데이터셋)

---

## Phase 2: Backend API (FastAPI)

### 2.1 Project Structure

- [x] FastAPI 앱 초기화 (`main.py`)
- [x] 디렉토리 구조 생성 (api/, models/, schemas/, services/)
- [x] 설정 관리 (Pydantic Settings)
- [x] 데이터베이스 연결 설정 (SQLAlchemy + GeoAlchemy2)

### 2.2 Database Models

- [x] `Event` 모델 (재난 이벤트)
- [x] `DataSource` 모델 (데이터 소스)
- [x] `GeoLayer` 모델 (지리 레이어)
- [x] `Dataset` 모델 (데이터셋)
- [x] `EventMetrics` 모델 (시계열 - TimescaleDB)
- [x] Alembic 마이그레이션 설정

### 2.3 API Endpoints

- [x] `GET /api/v1/events` - 이벤트 목록 조회
- [x] `GET /api/v1/events/{id}` - 이벤트 상세 조회
- [x] `GET /api/v1/events/{id}/layers` - 이벤트 레이어 조회
- [x] `GET /api/v1/geodata/tiles/{z}/{x}/{y}` - 벡터 타일
- [x] `POST /api/v1/sync/gdacs` - GDACS 동기화 트리거
- [x] `POST /api/v1/sync/copernicus` - Copernicus 동기화 트리거
- [x] OpenAPI 스펙 자동 생성 확인

### 2.4 External Data Services

- [x] GDACS 데이터 수집 서비스 (RSS 파싱 구현)
- [x] Copernicus EMS 데이터 수집 서비스
- [x] 데이터 동기화 스케줄러 (APScheduler - 5분 간격)
- [x] 에러 처리 및 재시도 로직 (지수 백오프, 최대 3회)

---

## Phase 3: Frontend Web (Next.js)

### 3.1 Project Structure

- [x] Next.js 15 앱 초기화 (App Router)
- [x] Tailwind CSS 설정
- [x] TypeScript 설정
- [x] ESLint/Prettier 설정
- [x] Zustand 상태 관리 설정

### 3.2 Shared Types & API Client

- [x] `@phoenix/shared` 패키지 생성
- [x] OpenAPI → TypeScript 타입 생성 설정 (openapi-typescript + openapi-fetch)
- [x] API 클라이언트 설정 (type-safe openapi-fetch)

### 3.3 Layout & Navigation

- [x] Root Layout 컴포넌트
- [x] Header 컴포넌트 (로고, 네비게이션)
- [x] Sidebar 컴포넌트 (레이어 패널, 필터)
- [x] Footer 컴포넌트
- [x] 반응형 디자인

### 3.4 Pages

- [x] `/` - 메인 페이지 (3D 지구본)
- [x] `/events` - 이벤트 목록 페이지
- [x] `/events/[id]` - 이벤트 상세 페이지
- [x] `/about` - About 페이지
- [x] `/settings` - 설정 페이지 (언어, 테마, 맵 설정)
- [x] `loading.tsx` 스켈레톤 UI
- [x] `error.tsx` 에러 페이지

### 3.5 Interactive Features

- [x] 모바일 햄버거 메뉴
- [x] 이벤트 검색 기능
- [x] Settings Store (Zustand + persist)

---

## Phase 4: 3D Globe Viewer

### 4.1 Core Viewer Setup

- [x] MapLibre GL JS 설정
- [x] Globe 프로젝션 초기화
- [x] 기본 지구본 렌더링
- [x] 카메라 컨트롤 (줌, 팬, 회전)

### 4.2 Base Layers

- [x] Dark 베이스맵 (Esri World Dark Gray, 키 불필요 — CARTO는 키 요구로 교체됨)
- [x] 위성 영상 베이스맵 (Esri World Imagery)
- [x] 2D/3D 모드 전환

### 4.3 CesiumJS Integration (Advanced 3D)

- [x] Resium 설정 (React 바인딩)
- [x] Cesium World Terrain 연동
- [x] 3D 건물 타일셋 로딩 (OSM Buildings)
- [x] CesiumJS ↔ MapLibre 엔진 스위칭 (MapEngineWrapper)

### 4.4 Event Visualization

- [x] 이벤트 마커 표시
- [x] 마커 스타일링 (유형별 색상)
- [x] 마커 클릭 이벤트 → 팝업
- [x] 클러스터링 (대량 이벤트)

### 4.5 UI Controls

- [x] 레이어 패널 UI
- [x] 레이어 On/Off 토글
- [x] 레이어 투명도 조절 (0~100% 슬라이더, i18n 지원)
- [x] 범례 컴포넌트
- [x] 타임라인 슬라이더 (재생, 속도, 히스토그램; `components/map/Timeline.tsx`)

### 4.6 MiniMap Component

- [x] MiniMap 컴포넌트 (이벤트 상세 페이지용)

---

## Phase 5: Data Integration

### 5.1 GDACS Integration

- [x] RSS/GeoRSS 파싱
- [x] REST API 연동
- [x] 이벤트 데이터 변환 (GDACS → Phoenix 스키마)
- [x] 자동 동기화 (5분 간격)

### 5.2 Copernicus EMS Integration

- [x] API 연동 방식 조사
- [x] 활성화 맵 데이터 수집
- [x] 피해 평가 데이터 수집 (DamageAssessment, AOIs, Products)

### 5.3 Data Processing

- [x] GeoJSON 변환 유틸리티
- [x] 좌표계 변환 (EPSG:4326)
- [x] 데이터 유효성 검증

---

## Phase 6: Testing & QA

### 6.1 Backend Tests

- [x] API 엔드포인트 테스트 (pytest) - 113개 테스트, 85% 커버리지
- [x] 데이터베이스 테스트 (PostGIS 쿼리) — `tests/integration/test_spatial_queries.py`: bbox(날짜변경선 포함),
      반경 검색과 geography 인덱스 사용, 중복 후보 검색(유형·거리·시간), 지오해시 클러스터링;
      경로·타임라인·뷰 요약 등 다른 통합 테스트도 실제 PostGIS에서 실행
- [x] 외부 API 모킹 테스트 (GDACS RSS/API 모킹)

### 6.2 Frontend Tests

- [x] 컴포넌트 테스트 (Vitest) - Header, Sidebar 29개 테스트
- [x] Zustand Store 테스트 (eventStore)
- [x] E2E 테스트 (Playwright) - 9개 테스트

### 6.3 Performance

- [x] 초기 로딩 시간 측정 및 최적화 (< 5s 달성)
- [x] API 응답 시간 측정 (< 500ms 달성 - 2ms)
- [x] 3D 렌더링 성능 프로파일링 — `pnpm --filter web perf:map [-- --headed --cesium --url …]`:
      지도를 드래그하는 동안의 프레임 간격(중앙 fps, p95, 50 ms 초과 프레임, long task)과 JS 힙을 측정

  기준값 (2026-11-02, 헤드리스 Chromium, 소프트웨어 WebGL, 타일 서버 차단 환경 — 같은 기계에서의 비교용 하한선):

  | 보기 | 중앙 fps | p95 프레임 | 50 ms 초과 | long task |
  | --- | --- | --- | --- | --- |
  | MapLibre 지구본 (3D) | 20 | 66.6 ms | 18 | 31 |
  | MapLibre 평면 (2D) | 30 | 50 ms | 1 | 0 |
  | Cesium | 2.2 | 483 ms | 21 | 68 |

  지도 준비 5.6 s, JS 힙 44 MB. GPU가 있는 실제 기기에서 `--headed`로 다시 재야 의미 있는 수치가 나옵니다.
  소프트웨어 렌더링에서도 Cesium이 크게 느리므로 기본 엔진은 MapLibre를 유지합니다.

---

## Phase 7: Advanced Features

### 7.1 Offline Merge Job

- [x] DB 마이그레이션 (merged_into_id, is_canonical)
- [x] OfflineMergeService 구현
- [x] CLI 스크립트 (scripts/offline_merge.py)
- [x] Admin API endpoint

### 7.2 GeoJSON Export

- [x] GeoJSON FeatureCollection 스키마
- [x] GET /geodata/events/geojson 엔드포인트
- [x] 필터링 및 limit 지원

### 7.3 Event Clustering

- [x] ClusteringService (PostGIS ST_GeoHash)
- [x] GET /geodata/events/clusters 엔드포인트
- [x] Zoom level별 클러스터 크기 조정

---

## Phase 8: Documentation

### 7.1 Technical Documentation

- [x] PRD.md - 제품 요구사항 문서
- [x] SPEC.md - 기술 스펙 문서
- [x] README.md - 프로젝트 설명
- [x] API.md - API 문서 (OpenAPI 기반)
- [x] ARCHITECTURE.md - 아키텍처 상세

---

## Milestone Checklist

### MVP Launch Criteria

- [x] 3D 지구본에 재난 이벤트 표시 (Mock 데이터)
- [x] GDACS 데이터 자동 동기화 (5분 간격)
- [x] 이벤트 유형별 필터링 기능
- [x] 이벤트 상세 정보 페이지
- [x] 레이어 On/Off 기능
- [x] 5초 내 초기 로딩 (4.98s 달성)
- [x] 모바일 반응형 지원

---

## Change Log

| Date       | Version | Changes                                                                |
| ---------- | ------- | ---------------------------------------------------------------------- |
| 2026-11-02 | —       | UI/UX pass, light basemap, PostGIS dedup/cluster tests, map benchmark  |
| 2026-11-02 | —       | Setup/deploy scripts, HTTPS production compose, backups (PR #41)       |
| 2026-11-01 | —       | Community, site plans, damage, push alerts, badges, challenges (#39–40)|
| 2026-01-05 | 0.18.0  | Phase 7: Offline Merge Job, GeoJSON Export, Clustering API             |
| 2025-12-29 | 0.16.0  | Copernicus EMS 피해 평가 데이터 수집 기능 추가 (DamageAssessment)      |
| 2025-12-29 | 0.15.0  | 레이어 투명도 조절 슬라이더 추가 (7개 언어 i18n 지원)                  |
| 2025-12-29 | 0.14.0  | OpenAPI TypeScript 타입 생성 및 type-safe API 클라이언트 설정          |
| 2025-12-29 | 0.13.0  | Seed 데이터 스크립트 추가 (12개 재난 이벤트)                           |
| 2025-12-28 | 0.12.0  | Copernicus EMS 연동, GeoJSON 유틸리티, 테스트 113개                    |
| 2025-12-27 | 0.11.0  | ARCHITECTURE.md 문서 완료                                              |
| 2025-12-27 | 0.10.0  | E2E 테스트 추가 (Playwright 9개 테스트)                                |
| 2025-12-27 | 0.9.0   | 이벤트 클러스터링, 위성 영상 베이스맵 추가                             |
| 2025-12-27 | 0.8.0   | 로딩 시간 최적화 (GeoJSON 레이어, Server/Client 분리, devtools 조건부) |
| 2025-12-27 | 0.7.0   | CesiumJS 통합 (Resium, Terrain, Buildings, MapEngineWrapper)           |
| 2025-12-26 | 0.6.0   | Alembic 설정, 에러 처리/재시도 로직, API 문서 완료                     |
| 2025-12-26 | 0.5.0   | 테스트 스위트 추가 (Backend 56개, Frontend 29개)                       |
| 2025-12-26 | 0.4.0   | 프론트엔드 완료 (loading.tsx, error.tsx, Footer, MiniMap)              |
| 2025-12-25 | 0.3.0   | 프론트엔드-백엔드 연동, GDACS 스케줄러 구현                            |
| 2025-12-25 | 0.2.0   | 백엔드 API, 프론트엔드 구조, 3D 뷰어 구현                              |
| 2025-12-24 | 0.1.0   | 초기 문서 작성, 프로젝트 구조 설계                                     |

---

## Notes

### Blockers

- (현재 없음)

### Decisions Made

1. **3D 뷰어**: MapLibre GL JS Globe (기본) + CesiumJS (고급 3D) 듀얼 엔진
2. **엔진 스위칭**: MapEngineWrapper 컴포넌트로 동적 엔진 전환 구현
3. **Monorepo**: Turborepo + pnpm workspaces
4. **타입 공유**: `@phoenix/shared` 패키지
5. **GDACS 연동**: RSS 피드 파싱 방식
6. **PostGIS**: MVP의 lat/lon 컬럼에서 PostGIS geometry + geography 인덱스로 전환 완료

### Next Actions

1. 실서버 첫 배포: `scripts/setup.sh --prod DOMAIN EMAIL` 후 DNS·`PLATFORM_ADMIN_EMAILS`·`SMTP_*` 확인
   (이 저장소의 개발 환경에는 Docker가 없어 컨테이너는 실제로 띄워 보지 않았습니다)
2. 외부 서비스가 막힌 개발 환경에서 검증하지 못한 부분 확인: 지도 타일(밝은 지도 포함), Copernicus 수집,
   웹 푸시 발송, 메일 발송
3. GPU가 있는 기기에서 `perf:map --headed --cesium`으로 렌더링 기준값 다시 측정
4. AI 피해 판독 모델: 자금·파트너, 첫 재난 유형, 검토 단체 결정 후 착수 ([AI_DAMAGE_MODEL_PLAN.md](./AI_DAMAGE_MODEL_PLAN.md))
