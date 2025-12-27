-- Phoenix Database Initialization
-- Note: PostGIS will be added when we move to a compatible image
-- For MVP, using simple lat/lon columns

CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TYPE event_type AS ENUM (
    'earthquake', 'flood', 'wildfire', 'hurricane',
    'tsunami', 'volcano', 'war', 'pollution', 'drought', 'other'
);

CREATE TYPE severity_level AS ENUM ('low', 'medium', 'high', 'critical');

CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type event_type NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    severity severity_level NOT NULL DEFAULT 'medium',
    -- Simple lat/lon for MVP (will migrate to PostGIS geometry later)
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    -- Affected area as GeoJSON text (will migrate to PostGIS geometry later)
    affected_area_geojson TEXT,
    country_code CHAR(2),
    region VARCHAR(255),
    affected_population INTEGER,
    start_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    source_id VARCHAR(255),
    source_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_lat_lon ON events (latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_events_type ON events (type);
CREATE INDEX IF NOT EXISTS idx_events_severity ON events (severity);
CREATE INDEX IF NOT EXISTS idx_events_start_date ON events (start_date DESC);
CREATE INDEX IF NOT EXISTS idx_events_is_active ON events (is_active);
CREATE INDEX IF NOT EXISTS idx_events_source_id ON events (source_id);

CREATE TABLE IF NOT EXISTS data_sources (
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

CREATE TABLE IF NOT EXISTS event_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID REFERENCES events(id) ON DELETE CASCADE,
    source_id UUID REFERENCES data_sources(id),
    external_id VARCHAR(255),
    raw_data JSONB,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(event_id, source_id, external_id)
);

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

-- TimescaleDB hypertable for time-series metrics
CREATE TABLE IF NOT EXISTS event_metrics (
    time TIMESTAMPTZ NOT NULL,
    event_id UUID NOT NULL,
    metric_type VARCHAR(100) NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
);

SELECT create_hypertable('event_metrics', 'time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_event_metrics_event_id ON event_metrics (event_id, time DESC);

-- Initial data sources
INSERT INTO data_sources (name, type, api_url, update_frequency, is_active) VALUES
    ('GDACS', 'disaster_alert', 'https://www.gdacs.org/gdacsapi/api', '5 minutes', true),
    ('Copernicus EMS', 'satellite_imagery', 'https://emergency.copernicus.eu', '1 day', true),
    ('HDX', 'humanitarian_data', 'https://data.humdata.org/api/3', '1 day', true),
    ('UNOSAT', 'satellite_analysis', 'https://unosat.org', '1 week', true)
ON CONFLICT (name) DO NOTHING;
