-- Phoenix Database Initialization
-- PostgreSQL 16 + TimescaleDB + PostGIS
--
-- Executed once on first container startup via docker-entrypoint-initdb.d/.
-- Only installs extensions. The schema is owned exclusively by Alembic
-- (apps/api/alembic), applied by `python -m scripts.migrate` when the API
-- container starts. Do not add tables here — they would drift from the models.

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS timescaledb;
