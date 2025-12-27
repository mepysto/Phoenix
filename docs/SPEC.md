# Phoenix - Phase 1 MVP Technical Specification

> **Version**: 1.0.0  
> **Last Updated**: 2025-12-24  
> **Status**: In Development

---

## 1. Overview

### 1.1 Project Summary
Phoenix는 전 세계의 재난, 전쟁, 환경오염 현황을 실시간 3D 디지털트윈으로 시각화하고, 누구나 복구 설계에 참여할 수 있는 글로벌 오픈 휴머니타리안 플랫폼입니다.

### 1.2 Phase 1 MVP Scope
- **글로벌 재난 이벤트 맵**: GDACS, Copernicus EMS 등 실시간 재난 데이터 통합
- **3D 디지털트윈 뷰어**: CesiumJS 기반 글로벌 3D 지구본 + 피해 시각화

### 1.3 Out of Scope (Phase 1)
- 3D 복구 설계 툴 (Phase 2)
- 난민/이재민 지원 매칭 (Phase 2)
- AI 기반 피해 분석 (Phase 2)
- 블록체인 기부 추적 (Phase 3)

---

## 2. Technical Architecture

### 2.1 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Next.js 15 (App Router)                          │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐ │   │
│  │  │   Pages     │  │  Components │  │     CesiumJS/Resium         │ │   │
│  │  │  - /        │  │  - Globe    │  │     3D Globe Viewer         │ │   │
│  │  │  - /events  │  │  - EventMap │  │     - Terrain               │ │   │
│  │  │  - /event/  │  │  - Timeline │  │     - 3D Tiles              │ │   │
│  │  │    [id]     │  │  - Layers   │  │     - Vector Layers         │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API GATEWAY                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                         FastAPI (Python 3.12+)                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐    │
│  │   Events    │  │   GeoData   │  │   Tiles     │  │   WebSocket     │    │
│  │   Service   │  │   Service   │  │   Proxy     │  │   (Real-time)   │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            DATA LAYER                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐ │
│  │     PostgreSQL      │  │     TimescaleDB     │  │   Object Storage    │ │
│  │     + PostGIS       │  │   (Time-series)     │  │   (S3 Compatible)   │ │
│  │                     │  │                     │  │                     │ │
│  │  - Events          │  │  - Sensor data      │  │  - 3D Tiles         │ │
│  │  - Geometries      │  │  - Event history    │  │  - Satellite imgs   │ │
│  │  - Users           │  │  - Metrics          │  │  - Terrain data     │ │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       EXTERNAL DATA SOURCES                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐    │
│  │   GDACS     │  │  Copernicus │  │   UNOSAT    │  │      HDX        │    │
│  │   API       │  │    EMS      │  │             │  │                 │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Technology Stack

| Layer | Technology | Version | Justification |
|-------|------------|---------|---------------|
| **Frontend** | Next.js | 15.x | App Router, RSC, Server Actions, 우수한 SSR/SSG |
| **UI Framework** | React | 19.x | Next.js 15 기본 탑재 |
| **Styling** | Tailwind CSS | 4.x | Utility-first, 빠른 개발 |
| **3D Viewer (Primary)** | deck.gl + MapLibre GL JS | 9.x / 5.x | 경량 재난 맵, GlobeView, 벡터 타일 |
| **3D Viewer (Advanced)** | CesiumJS + Resium | 1.x | 3D 지형/건물, OGC 표준 지원 |
| **State Management** | Zustand | 5.x | 경량, TypeScript 친화적 |
| **Backend** | FastAPI | 0.115+ | 비동기, OpenAPI 자동 생성, AI/ML 친화적 |
| **Database** | PostgreSQL + PostGIS | 16+ | 공간 쿼리, 산업 표준 |
| **Time-series** | TimescaleDB | 2.x | PostgreSQL 확장, 시계열 최적화 |
| **Cache** | Redis | 7.x | 세션, 캐싱, Pub/Sub |
| **Message Queue** | Redis Streams | 7.x | 이벤트 스트리밍 (향후 Kafka 전환 가능) |
| **Container** | Docker | 24+ | 컨테이너화 |
| **Orchestration** | Docker Compose | 2.x | 개발 환경 (Production: K8s) |

### 2.3 Monorepo Structure

```
phoenix/
├── apps/
│   ├── web/                    # Next.js 15 Frontend
│   │   ├── src/
│   │   │   ├── app/           # App Router pages
│   │   │   ├── components/    # React components
│   │   │   ├── hooks/         # Custom hooks
│   │   │   ├── lib/           # Utilities
│   │   │   ├── services/      # API clients
│   │   │   └── store/         # Zustand stores
│   │   ├── public/
│   │   ├── next.config.ts
│   │   ├── tailwind.config.ts
│   │   └── package.json
│   │
│   └── api/                    # FastAPI Backend
│       ├── src/
│       │   ├── main.py        # FastAPI app entry
│       │   ├── api/           # Route handlers
│       │   │   ├── v1/
│       │   │   │   ├── events.py
│       │   │   │   ├── geodata.py
│       │   │   │   └── tiles.py
│       │   ├── core/          # Core configs
│       │   ├── models/        # SQLAlchemy models
│       │   ├── schemas/       # Pydantic schemas
│       │   ├── services/      # Business logic
│       │   │   ├── gdacs.py
│       │   │   ├── copernicus.py
│       │   │   └── geocoding.py
│       │   └── db/            # Database setup
│       ├── tests/
│       ├── pyproject.toml
│       └── Dockerfile
│
├── packages/
│   └── shared/                 # Shared types & utilities
│       ├── src/
│       │   ├── types/         # TypeScript types
│       │   └── constants/     # Shared constants
│       └── package.json
│
├── infrastructure/
│   ├── docker/
│   │   ├── docker-compose.yml
│   │   ├── docker-compose.dev.yml
│   │   └── docker-compose.prod.yml
│   └── k8s/                   # Kubernetes manifests (future)
│
├── docs/
│   ├── SPEC.md               # This file
│   ├── PROGRESS.md           # Development checklist
│   ├── API.md                # API documentation
│   └── ARCHITECTURE.md       # Architecture details
│
├── scripts/
│   ├── setup.sh
│   └── seed-data.sh
│
├── package.json              # Root package.json
├── pnpm-workspace.yaml
├── turbo.json
├── .env.example
└── README.md
```

---

## 3. Feature Specifications

### 3.1 FR-1: Global Disaster Event Map

#### 3.1.1 Live Event Map (FR-1.1)

**Description**: 전 세계 재난/전쟁/오염 이벤트를 실시간 3D 지구본에 표시

**Data Sources**:
| Source | Type | Update Frequency | API |
|--------|------|------------------|-----|
| GDACS | 지진, 홍수, 태풍, 화산 | 실시간 | RSS/GeoRSS |
| Copernicus EMS | 위성 기반 피해 분석 | 일별 | REST API |
| UNOSAT | 분쟁/재난 피해 지도 | 주별 | WMS/WFS |
| HDX | 인도주의 데이터셋 | 다양함 | CKAN API |

**UI Components**:
```typescript
// Event marker on globe
interface DisasterEvent {
  id: string;
  type: 'earthquake' | 'flood' | 'wildfire' | 'hurricane' | 'war' | 'pollution';
  title: string;
  description: string;
  location: {
    lat: number;
    lng: number;
    country: string;
    region?: string;
  };
  severity: 'low' | 'medium' | 'high' | 'critical';
  affectedPopulation?: number;
  startDate: Date;
  endDate?: Date;
  sources: DataSource[];
  geometry?: GeoJSON.Geometry;
}
```

**Acceptance Criteria**:
- [ ] 3D 지구본에 이벤트 마커 표시
- [ ] 마커 클릭 시 이벤트 요약 팝업
- [ ] 이벤트 유형별 필터링 (지진, 홍수, 전쟁 등)
- [ ] 시간 범위 필터링 (최근 24시간, 7일, 30일)
- [ ] 5초 내 초기 로딩

#### 3.1.2 Event Detail View (FR-1.2)

**Description**: 개별 이벤트의 상세 정보 페이지

**UI Components**:
- 이벤트 메타데이터 (위치, 발생 시각, 규모)
- 영향 추정 (인구, 면적)
- 관련 데이터셋 목록 및 링크
- 전/후 위성 이미지 비교 (가능한 경우)
- 관련 뉴스/보고서 링크

**Acceptance Criteria**:
- [ ] 이벤트 상세 정보 표시
- [ ] 관련 데이터셋 링크 제공
- [ ] 영향 지역 지도 표시
- [ ] 시간대별 변화 타임라인 (데이터 가용 시)

### 3.2 FR-3: Digital Twin Viewer

#### 3.2.1 2D/3D Integrated View (FR-3.1)

**Description**: WebGL 기반 2D/3D 통합 지구 뷰어

**Technical Implementation**:
```typescript
// Viewer configuration
interface ViewerConfig {
  mode: '2d' | '3d';
  baseLayer: 'osm' | 'satellite' | 'terrain';
  terrain: {
    enabled: boolean;
    provider: 'cesium-world-terrain' | 'custom';
  };
  buildings: {
    enabled: boolean;
    tileset: string; // 3D Tiles URL
  };
}
```

**Acceptance Criteria**:
- [ ] 3D 지구본 기본 렌더링
- [ ] 2D/3D 모드 전환
- [ ] 위성 영상 오버레이
- [ ] 3D 지형 (DEM) 렌더링
- [ ] 3D 건물 타일셋 로딩
- [ ] 부드러운 줌/팬/회전

#### 3.2.2 Timeline Control (FR-3.2)

**Description**: 재난 전/후 시간축 비교

**UI Components**:
```typescript
interface TimelineConfig {
  startDate: Date;
  endDate: Date;
  currentDate: Date;
  mode: 'single' | 'compare'; // compare = before/after split view
}
```

**Acceptance Criteria**:
- [ ] 타임라인 슬라이더 UI
- [ ] 날짜별 데이터 로딩
- [ ] Before/After 분할 뷰 (선택적)
- [ ] 애니메이션 재생 기능

#### 3.2.3 Layer Management (FR-3.3)

**Description**: 다양한 데이터 레이어 On/Off

**Layers**:
| Layer Type | Description | Data Format |
|------------|-------------|-------------|
| Damage Assessment | 건물 피해 등급 | GeoJSON |
| Flood Extent | 침수 영역 | GeoJSON/Raster |
| Fire Perimeter | 화재 경계 | GeoJSON |
| Infrastructure | 도로, 병원, 학교 등 | Vector Tiles |
| Population Density | 인구 밀도 | Raster |

**Acceptance Criteria**:
- [ ] 레이어 목록 UI
- [ ] 레이어 On/Off 토글
- [ ] 레이어 투명도 조절
- [ ] 레이어 순서 변경
- [ ] 범례 표시

---

## 4. Database Schema

### 4.1 Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│     events      │       │  event_sources  │       │  data_sources   │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │──┐    │ id (PK)         │    ┌──│ id (PK)         │
│ type            │  │    │ event_id (FK)   │────┘  │ name            │
│ title           │  └───▶│ source_id (FK)  │◀──────│ type            │
│ description     │       │ external_id     │       │ api_url         │
│ severity        │       │ raw_data        │       │ update_freq     │
│ location (geom) │       └─────────────────┘       └─────────────────┘
│ affected_area   │
│ start_date      │       ┌─────────────────┐       ┌─────────────────┐
│ end_date        │       │  geo_layers     │       │    datasets     │
│ created_at      │       ├─────────────────┤       ├─────────────────┤
│ updated_at      │       │ id (PK)         │       │ id (PK)         │
└─────────────────┘       │ event_id (FK)   │◀──┐   │ event_id (FK)   │
                          │ layer_type      │   │   │ name            │
                          │ geometry        │   │   │ type            │
                          │ properties      │   └───│ url             │
                          │ timestamp       │       │ license         │
                          └─────────────────┘       │ metadata        │
                                                    └─────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    TimescaleDB Hypertables                          │
├─────────────────────────────────────────────────────────────────────┤
│  event_metrics (time-series)                                        │
│  ├─ time (TIMESTAMPTZ) - partition key                             │
│  ├─ event_id (FK)                                                  │
│  ├─ metric_type (affected_population, area_km2, etc.)              │
│  └─ value (DOUBLE)                                                 │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 Core Tables (PostgreSQL + PostGIS)

```sql
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Disaster event types enum
CREATE TYPE event_type AS ENUM (
    'earthquake', 'flood', 'wildfire', 'hurricane', 
    'tsunami', 'volcano', 'war', 'pollution', 'other'
);

CREATE TYPE severity_level AS ENUM ('low', 'medium', 'high', 'critical');

-- Main events table
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type event_type NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    severity severity_level NOT NULL DEFAULT 'medium',
    location GEOMETRY(Point, 4326) NOT NULL,
    affected_area GEOMETRY(MultiPolygon, 4326),
    country_code CHAR(2),
    region VARCHAR(255),
    affected_population INTEGER,
    start_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Spatial index
CREATE INDEX idx_events_location ON events USING GIST (location);
CREATE INDEX idx_events_affected_area ON events USING GIST (affected_area);
CREATE INDEX idx_events_type ON events (type);
CREATE INDEX idx_events_start_date ON events (start_date DESC);

-- Data sources registry
CREATE TABLE data_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    type VARCHAR(50) NOT NULL,
    api_url TEXT,
    api_key_required BOOLEAN DEFAULT false,
    update_frequency INTERVAL,
    last_sync TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    metadata JSONB
);

-- Event-Source relationship (many-to-many)
CREATE TABLE event_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID REFERENCES events(id) ON DELETE CASCADE,
    source_id UUID REFERENCES data_sources(id),
    external_id VARCHAR(255), -- ID from external source
    raw_data JSONB,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(event_id, source_id, external_id)
);

-- Geographic layers for events
CREATE TABLE geo_layers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID REFERENCES events(id) ON DELETE CASCADE,
    layer_type VARCHAR(100) NOT NULL, -- damage_assessment, flood_extent, etc.
    geometry GEOMETRY NOT NULL,
    properties JSONB,
    timestamp TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_geo_layers_geometry ON geo_layers USING GIST (geometry);

-- Datasets linked to events
CREATE TABLE datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID REFERENCES events(id) ON DELETE CASCADE,
    name VARCHAR(500) NOT NULL,
    type VARCHAR(100), -- satellite_image, vector, 3d_tiles, report
    url TEXT,
    license VARCHAR(255),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Time-series metrics (TimescaleDB)
CREATE TABLE event_metrics (
    time TIMESTAMPTZ NOT NULL,
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    metric_type VARCHAR(100) NOT NULL,
    value DOUBLE PRECISION NOT NULL
);

SELECT create_hypertable('event_metrics', 'time');
```

---

## 5. API Specification

### 5.1 Events API

#### GET /api/v1/events
```yaml
summary: List disaster events
parameters:
  - name: type
    in: query
    schema:
      type: array
      items:
        type: string
        enum: [earthquake, flood, wildfire, hurricane, war, pollution]
  - name: severity
    in: query
    schema:
      type: string
      enum: [low, medium, high, critical]
  - name: bbox
    in: query
    description: Bounding box [minLng, minLat, maxLng, maxLat]
    schema:
      type: array
      items:
        type: number
  - name: start_date
    in: query
    schema:
      type: string
      format: date-time
  - name: end_date
    in: query
    schema:
      type: string
      format: date-time
  - name: limit
    in: query
    schema:
      type: integer
      default: 100
  - name: offset
    in: query
    schema:
      type: integer
      default: 0
responses:
  200:
    content:
      application/json:
        schema:
          type: object
          properties:
            data:
              type: array
              items:
                $ref: '#/components/schemas/Event'
            pagination:
              $ref: '#/components/schemas/Pagination'
```

#### GET /api/v1/events/{id}
```yaml
summary: Get event details
parameters:
  - name: id
    in: path
    required: true
    schema:
      type: string
      format: uuid
responses:
  200:
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/EventDetail'
```

#### GET /api/v1/events/{id}/layers
```yaml
summary: Get geographic layers for an event
responses:
  200:
    content:
      application/json:
        schema:
          type: object
          properties:
            layers:
              type: array
              items:
                $ref: '#/components/schemas/GeoLayer'
```

### 5.2 GeoData API

#### GET /api/v1/geodata/tiles/{z}/{x}/{y}
```yaml
summary: Get vector tiles
parameters:
  - name: z
    in: path
    schema:
      type: integer
  - name: x
    in: path
    schema:
      type: integer
  - name: y
    in: path
    schema:
      type: integer
  - name: layers
    in: query
    schema:
      type: array
      items:
        type: string
responses:
  200:
    content:
      application/x-protobuf:
        schema:
          type: string
          format: binary
```

### 5.3 Sync API (Internal)

#### POST /api/v1/sync/gdacs
```yaml
summary: Trigger GDACS data sync
security:
  - ApiKeyAuth: []
responses:
  202:
    description: Sync job started
```

---

## 6. External Data Integration

### 6.1 GDACS Integration

**REST API**: `https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH`
**RSS Feed**: `https://www.gdacs.org/xml/rss.xml` (GeoRSS)
**Swagger Docs**: https://www.gdacs.org/gdacsapi/swagger/index.html

**Data Mapping**:
```python
GDACS_EVENT_TYPE_MAP = {
    'EQ': 'earthquake',
    'FL': 'flood',
    'TC': 'hurricane',
    'VO': 'volcano',
    'DR': 'drought',
    'WF': 'wildfire',
}

GDACS_SEVERITY_MAP = {
    'Green': 'low',
    'Orange': 'medium', 
    'Red': 'high',
}
```

**Sync Frequency**: Every 5 minutes

### 6.2 Copernicus EMS Integration

**API**: https://emergency.copernicus.eu/mapping/

**Data Types**:
- Activation maps (vector)
- Delineation products
- Grading products (damage assessment)

**Sync Frequency**: Daily

### 6.3 HDX Integration

**API**: https://data.humdata.org/api/3/

**Data Types**:
- Population statistics
- Displacement data
- Infrastructure datasets

---

## 7. Performance Requirements

### 7.1 Response Time Targets

| Operation | Target | P95 |
|-----------|--------|-----|
| Initial page load | < 3s | < 5s |
| Event list fetch | < 500ms | < 1s |
| 3D globe render | < 2s | < 3s |
| Layer toggle | < 200ms | < 500ms |
| Search | < 300ms | < 500ms |

### 7.2 Scalability Targets

| Metric | Phase 1 | Phase 2 |
|--------|---------|---------|
| Concurrent users | 1,000 | 10,000 |
| Events in DB | 10,000 | 100,000 |
| API RPS | 100 | 1,000 |
| 3D Tiles size | 10 GB | 100 GB |

---

## 8. Security Requirements

### 8.1 Authentication (Phase 1 - Basic)
- Public read access for disaster data
- API key for sync endpoints
- Rate limiting: 100 req/min per IP

### 8.2 Future (Phase 2+)
- OAuth2 / OpenID Connect
- Role-based access control (RBAC)
- Audit logging

---

## 9. Deployment

### 9.1 Development Environment
```yaml
# docker-compose.dev.yml
services:
  web:
    build: ./apps/web
    ports: ["3000:3000"]
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
      
  api:
    build: ./apps/api
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql://...
      
  db:
    image: postgis/postgis:16-3.4
    ports: ["5432:5432"]
    
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
```

### 9.2 Production (Future)
- Kubernetes deployment
- CDN for static assets and 3D tiles
- Managed PostgreSQL (AWS RDS / GCP Cloud SQL)
- Redis Cluster

---

## 10. Appendix

### 10.1 Glossary

| Term | Definition |
|------|------------|
| Digital Twin | 실제 세계의 디지털 복제본 |
| 3D Tiles | OGC 표준 3D 공간 데이터 포맷 |
| PostGIS | PostgreSQL 공간 데이터 확장 |
| GDACS | Global Disaster Alert and Coordination System |
| EMS | Emergency Management Service |

### 10.2 References

- [CesiumJS Documentation](https://cesium.com/docs/)
- [PostGIS Documentation](https://postgis.net/docs/)
- [GDACS API](https://www.gdacs.org/resources.aspx)
- [OGC 3D Tiles](https://www.ogc.org/standards/3DTiles)
