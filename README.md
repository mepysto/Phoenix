# Phoenix

> **Digital twin platform where everyone can heal the wounds of the earth together**

Phoenix는 전 세계의 재난, 전쟁, 환경오염 현황을 실시간 3D 디지털트윈으로 시각화하고, 누구나 복구 설계에 참여할 수 있는 글로벌 오픈 휴머니타리안 플랫폼입니다.

## Features (Phase 1 MVP)

- **Global Disaster Event Map**: GDACS, Copernicus EMS 등 실시간 재난 데이터 통합
- **3D Digital Twin Viewer**: MapLibre GL JS 기반 글로벌 3D 지구본
- **Event Filtering**: 재난 유형, 심각도별 필터링
- **Real-time Updates**: 5분 간격 재난 데이터 자동 동기화

## Tech Stack

| Layer    | Technology                                     |
| -------- | ---------------------------------------------- |
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS |
| 3D Map   | MapLibre GL JS (Globe), deck.gl (layers)       |
| Backend  | FastAPI, Python 3.12+                          |
| Database | PostgreSQL 16 + PostGIS + TimescaleDB          |
| Cache    | Redis 7                                        |
| Infra    | Docker, Turborepo                              |

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

# Start database and services
pnpm docker:up

# Run development servers
pnpm dev
```

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

## Data Sources

- **GDACS** - Global Disaster Alert and Coordination System
- **Copernicus EMS** - Emergency Management Service
- **HDX** - Humanitarian Data Exchange
- **UNOSAT** - UN Satellite Centre

## License

MIT License - See [LICENSE](./LICENSE) for details.
