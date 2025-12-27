# Phoenix Architecture

Phoenix is a **Digital Twin Humanitarian Platform** designed for real-time disaster visualization and collaborative recovery planning. This document provides a technical overview of the system architecture, data flow, and key design decisions.

## 1. Overview

Phoenix visualizes global disaster events (earthquakes, floods, wildfires, etc.) on a 3D digital twin of the Earth. It integrates data from multiple humanitarian sources and provides a high-fidelity visualization environment.

### High-Level Architecture

```ascii
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Next.js 15 (App Router)                          │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐ │   │
│  │  │   Pages     │  │  Components │  │     CesiumJS / MapLibre     │ │   │
│  │  │  - Globe    │  │  - Sidebar    │  │     3D Globe Viewer         │ │   │
│  │  │  - Events   │  │  - UI Kits    │  │     - Terrain / 3D Tiles    │ │   │
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
│  │   Events    │  │   GeoData   │  │   Sync      │  │   Scheduler     │    │
│  │   Service   │  │   Service   │  │   Service   │  │   (APScheduler) │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            DATA LAYER                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐ │
│  │     PostgreSQL      │  │     TimescaleDB     │  │       Redis         │ │
│  │     + PostGIS       │  │   (Time-series)     │  │       (Cache)       │ │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       EXTERNAL DATA SOURCES                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│      GDACS (RSS/API)  │  Copernicus EMS  │  UNOSAT  │  HDX (CKAN)            │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2. System Components

### Frontend (`apps/web`)

A Next.js 15 application utilizing the App Router. It handles user interactions, event filtering, and dual-engine map visualization.

- **Framework**: React 19, TypeScript
- **Styling**: Tailwind CSS
- **State Management**: Zustand

### Backend (`apps/api`)

A FastAPI-based REST API providing disaster data, geographic layers, and synchronization management.

- **Logic**: Service-oriented architecture
- **Task Scheduling**: APScheduler for background data synchronization

### Shared Packages (`packages/`)

- **`shared`**: Common TypeScript types, interfaces, and constants (e.g., `DisasterEvent`, `EventType`).
- **`typescript-config` / `eslint-config`**: Standardized configurations across the monorepo.

### Infrastructure

- **Docker**: Containerized services for development and production.
- **PostgreSQL**: Core relational database with **PostGIS** for spatial queries.
- **TimescaleDB**: Extension for high-performance time-series event metrics.
- **Redis**: Caching and potential event streaming.

## 3. Data Flow

1.  **Ingestion**: The `GDACSService` in the backend runs every 5 minutes (via APScheduler), fetching RSS feeds and REST API data from GDACS.
2.  **Normalization**: External data is mapped to the internal `Event` schema (mapped in `src/services/gdacs_service.py`).
3.  **Persistence**: Data is stored in PostgreSQL. Spatial coordinates are handled via GeoAlchemy2/PostGIS.
4.  **Serving**: The `Events API` provides endpoints to filter and retrieve disaster events.
5.  **State Sync**: The Frontend's `eventStore` (Zustand) fetches data on mount or filter change.
6.  **Visualization**: `MapEngineWrapper` receives the event list and renders it using either MapLibre GL JS or CesiumJS.

## 4. Key Design Decisions

- **Monorepo with Turborepo**: Enables shared types between frontend and backend and provides a unified build system.
- **Dual Map Engine Strategy**:
  - **MapLibre GL JS**: Used for high-performance 2D/3D globe visualization and fast interactive layers.
  - **CesiumJS (via Resium)**: Used for high-fidelity 3D analysis, including global terrain (DEM) and 3D Tiles (OSM Buildings).
- **Zustand State Management**: Chosen for its simplicity and excellent TypeScript support, managing both event data and map viewport state.
- **GeoJSON for Performance**: Vector data is served as GeoJSON or Vector Tiles to allow client-side styling and clustering.
- **Server/Client Component Split**: Leverages Next.js 15 features to minimize client-side bundle size by using Server Components for page layouts and Client Components for interactive map elements.

## 5. Directory Structure

```text
phoenix/
├── apps/
│   ├── api/                # FastAPI Backend
│   │   ├── src/api/        # Route handlers (v1)
│   │   ├── src/models/     # SQLAlchemy/GeoAlchemy2 models
│   │   ├── src/services/   # Business logic & external sync
│   │   └── src/main.py     # Entry point
│   └── web/                # Next.js Frontend
│       ├── src/app/        # App Router (pages & layouts)
│       ├── src/components/ # React components (layout, map, ui)
│       ├── src/store/      # Zustand stores (event, map)
│       └── src/lib/        # API client & utilities
├── packages/
│   ├── shared/             # Common types & constants
│   └── typescript-config/  # Shared TS configs
├── infrastructure/
│   └── docker/             # Docker Compose & Init scripts
└── docs/                   # Documentation (SPEC, ARCHITECTURE, API)
```

## 6. API Architecture

The API follows a RESTful pattern with the following core responsibilities:

- **Events API**: `/api/v1/events` for listing and retrieving disaster details.
- **GeoData API**: `/api/v1/geodata/tiles` for serving vector tiles (MVT).
- **Sync API**: `/api/v1/sync` (Internal) for triggering data updates from external sources.
- **Pydantic Validation**: All requests and responses are validated against Pydantic schemas to ensure data integrity.

## 7. Frontend Architecture

### Component Hierarchy

- **Root Layout**: Contains `Header`, `Sidebar`, and the main content area.
- **MapPageClient**: Orchestrates the map and sidebar interactions.
- **MapEngineWrapper**: The primary strategy component that switches between `GlobeViewer` and `CesiumViewer`.

### State Management

- **EventStore**: Manages `events`, `selectedEvent`, `filters` (type, severity), and `pagination`.
- **MapStore**: Manages `engine` (maplibre/cesium), `basemap`, and viewport state (`center`, `zoom`).

### Map Engine Switching

Engines are dynamically loaded using `next/dynamic` with `ssr: false`. Switching engines preserves the logical state (center, zoom, selected event) while swapping the underlying rendering library.

## 8. Database Schema

### Main Tables

- **`events`**: Stores core disaster information (type, title, severity, start_date). Uses `latitude` and `longitude` for location.
- **`geo_layers`**: Stores complex GeoJSON geometries (e.g., shake maps, flood perimeters) linked to events.
- **`data_sources`**: Registry of external data providers (GDACS, etc.).
- **`event_metrics`**: A TimescaleDB hypertable for tracking time-varying data like affected population or intensity over time.

### Spatial Features

- **PostGIS**: Enables efficient spatial queries (e.g., find events within a bounding box).
- **GIST Indexes**: Applied to geometry columns for high-performance spatial lookups.

## 9. Deployment

The project is containerized using Docker:

- **`docker-compose.yml`**: Orchestrates the API, Web, PostgreSQL/PostGIS, and Redis.
- **Ports**:
  - Web: `23000` (mapped to `3000` internally)
  - API: `28000` (mapped to `8000` internally)
  - Database: `5434` (PostgreSQL)
  - Redis: `6381`

## 10. Performance Optimizations

- **Lazy Loading**: Map engines and heavy components are only loaded when required using Next.js Dynamic Imports.
- **GeoJSON Clustering**: MapLibre is configured to cluster event markers at high zoom levels to maintain 60 FPS performance even with thousands of points.
- **Deferred Map Initialization**: Uses `requestIdleCallback` (via React effects) to ensure the UI thread is free before initializing heavy WebGL contexts.
- **Memoized API Responses**: Redis is used to cache frequent event queries and external data responses.
- **Shared Types**: Zero-cost abstraction for data consistency between Python and TypeScript via the `shared` package.
