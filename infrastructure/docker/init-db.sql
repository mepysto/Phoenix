-- Phoenix Database Initialization
-- PostgreSQL 16 + TimescaleDB + PostGIS
--
-- This script initializes the database schema for Phoenix.
-- It's executed on first container startup via docker-entrypoint-initdb.d/

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================================================
-- ENUM TYPES
-- ============================================================================

-- Event type enum (disaster categories)
CREATE TYPE event_type AS ENUM (
    'earthquake', 'flood', 'wildfire', 'hurricane',
    'tsunami', 'volcano', 'war', 'pollution', 'drought', 'other',
    'landslide', 'industrial', 'epidemic', 'storm',
    'coldwave', 'heatwave', 'complex_emergency'
);

-- Severity level enum
CREATE TYPE severity_level AS ENUM ('low', 'medium', 'high', 'critical');

-- Geographic precision enum (how accurate is the location)
CREATE TYPE geo_precision AS ENUM (
    'exact',        -- GPS coordinates from source
    'approximate',  -- Approximate location
    'admin1',       -- State/province level
    'country',      -- Country centroid
    'unknown'       -- Precision not determined
);

-- Geographic method enum (how was the location determined)
CREATE TYPE geo_method AS ENUM (
    'source_provided',  -- Coordinates from original source
    'geocoded',         -- Geocoded from address/place name
    'admin_centroid',   -- Centroid of administrative area
    'manual'            -- Manually assigned
);

-- ============================================================================
-- TABLES
-- ============================================================================

-- Admin Areas (countries, states, provinces, etc.)
CREATE TABLE IF NOT EXISTS admin_areas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    iso_a2 VARCHAR(2),                          -- ISO 3166-1 alpha-2 (KR, US)
    iso_a3 VARCHAR(3),                          -- ISO 3166-1 alpha-3 (KOR, USA)
    name VARCHAR(255) NOT NULL,                 -- English name
    name_local VARCHAR(255),                    -- Local language name
    admin_level INTEGER NOT NULL DEFAULT 0,     -- 0=country, 1=state, etc.
    parent_id UUID REFERENCES admin_areas(id),  -- Hierarchy reference
    geometry GEOMETRY(MULTIPOLYGON, 4326),      -- Boundary polygon
    centroid GEOMETRY(POINT, 4326),             -- Center point
    bbox JSONB,                                 -- Bounding box {minx,miny,maxx,maxy}
    population INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Admin Areas indexes
CREATE UNIQUE INDEX IF NOT EXISTS idx_admin_areas_iso_a2
    ON admin_areas (iso_a2) WHERE admin_level = 0 AND iso_a2 IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_admin_areas_iso_a3
    ON admin_areas (iso_a3) WHERE admin_level = 0 AND iso_a3 IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_admin_areas_geometry
    ON admin_areas USING GIST (geometry);
CREATE INDEX IF NOT EXISTS idx_admin_areas_parent
    ON admin_areas (parent_id);
CREATE INDEX IF NOT EXISTS idx_admin_areas_level
    ON admin_areas (admin_level);

-- Events (disaster/crisis events)
CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type event_type NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    severity severity_level NOT NULL DEFAULT 'medium',

    -- Legacy lat/lon columns (kept for backward compatibility)
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,

    -- PostGIS geometry column (primary spatial field)
    location GEOMETRY(POINT, 4326),

    -- Geolocation metadata
    geo_precision geo_precision DEFAULT 'unknown',
    geo_method geo_method,
    admin_area_id UUID REFERENCES admin_areas(id),
    glide_number VARCHAR(50),                   -- GLIDE disaster ID

    -- Additional location info
    affected_area_geojson TEXT,
    country_code VARCHAR(3),
    region VARCHAR(255),
    affected_population INTEGER,

    -- Temporal data
    start_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,

    -- Source tracking
    source_id VARCHAR(255),
    source_url TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Events indexes
CREATE INDEX IF NOT EXISTS idx_events_lat_lon ON events (latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_events_location ON events USING GIST (location);
CREATE INDEX IF NOT EXISTS idx_events_type ON events (type);
CREATE INDEX IF NOT EXISTS idx_events_severity ON events (severity);
CREATE INDEX IF NOT EXISTS idx_events_start_date ON events (start_date DESC);
CREATE INDEX IF NOT EXISTS idx_events_is_active ON events (is_active);
CREATE INDEX IF NOT EXISTS idx_events_source_id ON events (source_id);
CREATE INDEX IF NOT EXISTS idx_events_geo_precision ON events (geo_precision);
CREATE INDEX IF NOT EXISTS idx_events_admin_area ON events (admin_area_id);
CREATE INDEX IF NOT EXISTS idx_events_glide ON events (glide_number);

-- Data Sources (external data providers)
CREATE TABLE IF NOT EXISTS data_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    type VARCHAR(50) NOT NULL,
    api_url TEXT,
    api_key_required BOOLEAN DEFAULT false,
    auth_type VARCHAR(20),
    update_frequency VARCHAR(50),
    sync_interval_minutes INTEGER DEFAULT 5,
    rate_limit_rpm INTEGER,
    last_sync TIMESTAMPTZ,
    last_sync_status VARCHAR(20) DEFAULT 'never',
    last_sync_error TEXT,
    consecutive_failures INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    is_realtime BOOLEAN DEFAULT false,
    metadata JSONB
);

-- Event Sources (junction table: events <-> data_sources)
CREATE TABLE IF NOT EXISTS event_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID REFERENCES events(id) ON DELETE CASCADE,
    source_id UUID REFERENCES data_sources(id),
    external_id VARCHAR(255),
    raw_data JSONB,
    fetched_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_event_sources_source_external
    ON event_sources (source_id, external_id);

-- Geo Layers (GeoJSON layers associated with events)
CREATE TABLE IF NOT EXISTS geo_layers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID REFERENCES events(id) ON DELETE CASCADE,
    layer_type VARCHAR(100) NOT NULL,
    geojson TEXT NOT NULL,
    properties JSONB,
    timestamp TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_geo_layers_event_id ON geo_layers (event_id);

-- Datasets (external datasets linked to events)
CREATE TABLE IF NOT EXISTS datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID REFERENCES events(id) ON DELETE CASCADE,
    name VARCHAR(500) NOT NULL,
    type VARCHAR(100),
    url TEXT,
    license VARCHAR(255),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Event Metrics (TimescaleDB hypertable for time-series data)
CREATE TABLE IF NOT EXISTS event_metrics (
    time TIMESTAMPTZ NOT NULL,
    event_id UUID NOT NULL,
    metric_type VARCHAR(100) NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (time, event_id, metric_type),
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
);

-- Convert to TimescaleDB hypertable
SELECT create_hypertable('event_metrics', 'time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_event_metrics_event_id
    ON event_metrics (event_id, time DESC);

-- ============================================================================
-- INITIAL DATA
-- ============================================================================

-- Seed data sources
INSERT INTO data_sources (name, type, api_url, update_frequency, sync_interval_minutes, is_active)
VALUES
    ('GDACS', 'disaster_alert', 'https://www.gdacs.org/gdacsapi/api', '5 minutes', 5, true),
    ('Copernicus EMS', 'satellite_imagery', 'https://emergency.copernicus.eu', '1 day', 1440, true),
    ('HDX', 'humanitarian_data', 'https://data.humdata.org/api/3', '1 day', 1440, true),
    ('UNOSAT', 'satellite_analysis', 'https://unosat.org', '1 week', 10080, true)
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- BACKFILL FUNCTION
-- ============================================================================

-- Function to backfill location from lat/lon for existing records
-- Run this after migrating existing data:
--
-- UPDATE events
-- SET location = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
-- WHERE latitude IS NOT NULL
--   AND longitude IS NOT NULL
--   AND location IS NULL;
