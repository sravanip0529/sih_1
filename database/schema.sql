CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS tile (
    tile_id UUID PRIMARY KEY,
    geometry geometry(POLYGON, 4326) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    sensor TEXT NOT NULL,
    acquisition_datetime TIMESTAMPTZ NOT NULL,
    cloud_cover REAL,
    source TEXT,
    filepath TEXT NOT NULL,
    embedding_id_semantic TEXT,
    embedding_id_spectral TEXT,
    quality_score REAL,
    processing_version TEXT NOT NULL,
    location_key TEXT NOT NULL,
    scene_id TEXT,
    source_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS tile_geometry_gist ON tile USING GIST (geometry);
CREATE INDEX IF NOT EXISTS tile_location_date_idx ON tile (location_key, acquisition_datetime);

CREATE TABLE IF NOT EXISTS change_result (
    change_id UUID PRIMARY KEY,
    location_key TEXT NOT NULL,
    before_tile_id UUID NOT NULL REFERENCES tile(tile_id),
    after_tile_id UUID NOT NULL REFERENCES tile(tile_id),
    earliest_change_date DATE,
    change_type TEXT NOT NULL CHECK (change_type IN ('construction', 'water_extent', 'road', 'clearance', 'no_change')),
    change_score REAL,
    confidence REAL,
    evidence_paths JSONB NOT NULL DEFAULT '[]'::jsonb,
    registration_shift_px REAL,
    cloud_mask_quality REAL,
    model_version TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS change_result_location_idx ON change_result (location_key);

CREATE TABLE IF NOT EXISTS review_log (
    review_id UUID PRIMARY KEY,
    change_id UUID NOT NULL REFERENCES change_result(change_id),
    decision TEXT NOT NULL CHECK (decision IN ('confirmed', 'rejected')),
    analyst_note TEXT,
    reviewed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
