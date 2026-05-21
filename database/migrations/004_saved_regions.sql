-- 004_saved_regions.sql
-- Auth users are normal users only. Saved regions store a user's selected map
-- point and the resolved existing hara_bogor polygon.
-- Idempotent: safe to run repeatedly.

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(255),
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_users_id ON users (id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);

ALTER TABLE users DROP COLUMN IF EXISTS is_admin;

CREATE TABLE IF NOT EXISTS saved_regions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    hara_area_id INTEGER NOT NULL REFERENCES hara_bogor(id) ON DELETE RESTRICT,
    selected_lon DOUBLE PRECISION NOT NULL,
    selected_lat DOUBLE PRECISION NOT NULL,
    label VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_saved_regions_user_area_point UNIQUE (
        user_id,
        hara_area_id,
        selected_lon,
        selected_lat
    )
);

CREATE INDEX IF NOT EXISTS ix_saved_regions_id ON saved_regions (id);
CREATE INDEX IF NOT EXISTS ix_saved_regions_user_id ON saved_regions (user_id);
CREATE INDEX IF NOT EXISTS ix_saved_regions_hara_area_id ON saved_regions (hara_area_id);

COMMENT ON TABLE saved_regions IS 'User-saved hara regions resolved from selected map points.';
COMMENT ON COLUMN saved_regions.selected_lon IS 'Longitude selected by the user, WGS 84.';
COMMENT ON COLUMN saved_regions.selected_lat IS 'Latitude selected by the user, WGS 84.';
