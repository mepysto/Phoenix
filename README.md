# Phoenix

> **Digital twin platform where everyone can heal the wounds of the earth together**

Phoenix는 전 세계의 재난, 전쟁, 환경오염 현황을 실시간 3D 디지털트윈으로 시각화하고, 누구나 복구 설계에 참여할 수 있는 글로벌 오픈 휴머니타리안 플랫폼입니다.

## What it does

**See** — a live picture of disasters
- Global event map (MapLibre globe, optional Cesium 3D) fed by GDACS, USGS, NASA EONET and Copernicus EMS, deduplicated and pushed live over WebSocket
- Every event carries a **confidence score** (independent sources, freshness) and a **lifecycle stage**: detected → verified → response → recovery → closed
- Hazard, weather, infrastructure and monitoring layers; timeline playback; Disaster Brief story mode; map assistant
- **Situation report** per event in the reader's language, every line traced to a data field
- **Before/after** satellite comparison (NASA GIBS daily VIIRS imagery)

**Act** — connect needs with help (Phase 2)
- Sign in with an emailed link, no passwords
- Organisations apply and are approved by platform admins; their members post **needs** (site, categories, priority, quantity)
- Anyone signed in posts **offers**; explainable **matching** ranks offers for each need
- **Two-sided connections**: contact details are shared only after both sides approve
- Organisations publish **progress updates** on each event

**Plan** — check a relief site against standards
- Lay out tents, water taps, toilets and health posts on the map; live checks against the **Sphere** minimum standards; auto-layout; shareable links

**Reach** — beyond the main app
- **Area alerts** with browser notifications · **/lite** text-only page for slow connections · **/embed** live map for other sites
- Seven UI languages (the six UN languages plus Korean), RTL for Arabic

## Tech Stack

| Layer    | Technology                                     |
| -------- | ---------------------------------------------- |
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS, Zustand |
| Maps     | MapLibre GL JS (globe), CesiumJS (3D engine)    |
| Backend  | FastAPI, SQLAlchemy 2 (async), Python 3.12+    |
| Database | PostgreSQL 16 + PostGIS (+ TimescaleDB in Docker) |
| Infra    | Docker, Turborepo, GitHub Actions              |

## Quick Start

### Prerequisites

- Node.js 20+
- pnpm 9+
- Python 3.11+
- Docker & Docker Compose

### Development Setup

```bash
# Clone and install dependencies
git clone https://github.com/your-org/phoenix.git
cd phoenix
pnpm install

# Copy environment variables
cp .env.example .env.local

# Check toolchain, database, migrations and upstream feeds
pnpm doctor

# Start database and services
pnpm docker:up

# Run development servers
pnpm dev
```

To try sign-in without a mail server, set `AUTH_DEV_RETURN_LINK=true` (development only) and add your address to `PLATFORM_ADMIN_EMAILS` to approve organisations.

- Frontend: http://localhost:23000
- API: http://localhost:28000
- API Docs: http://localhost:28000/docs

### Docker Only (Full Stack)

```bash
docker compose -f infrastructure/docker/docker-compose.yml up -d
```

## Project Structure

```
phoenix/
├── apps/
│   ├── web/          # Next.js 15 Frontend
│   └── api/          # FastAPI Backend
├── packages/
│   ├── shared/       # Shared types & constants
│   ├── eslint-config/
│   └── typescript-config/
├── infrastructure/
│   └── docker/       # Docker Compose configs
└── docs/
    ├── SPEC.md       # Technical Specification
    └── PROGRESS.md   # Development Progress
```

## Documentation

- [PRD.md](./PRD.md) - Product Requirements Document
- [docs/SPEC.md](./docs/SPEC.md) - Technical Specification
- [docs/PROGRESS.md](./docs/PROGRESS.md) - Development Progress Checklist
- [docs/DATA_SOURCES.md](./docs/DATA_SOURCES.md) - Every data source with licence, attribution and commercial-use status
- [docs/RESPONSIBLE_USE.md](./docs/RESPONSIBLE_USE.md) - Limits on use: not for safety-critical decisions alone, no tracking of individuals

## Data Sources

Live event feeds: **GDACS**, **USGS**, **NASA EONET** and **Copernicus EMS**. Map layers: OpenFreeMap, EOxCloudless (Sentinel-2), NASA GIBS and RainViewer.
Phoenix is operated non-commercially. See [docs/DATA_SOURCES.md](./docs/DATA_SOURCES.md) for licences, and set `NEXT_PUBLIC_COMMERCIAL_DEPLOYMENT=1` for commercial deployments.

## License

MIT License - See [LICENSE](./LICENSE) for details.
