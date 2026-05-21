-- 005_expert_persona.sql
-- Adds role-based expert/admin access and public expert advisory data.
-- Idempotent: safe to run repeatedly.

ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(32) NOT NULL DEFAULT 'user';

CREATE INDEX IF NOT EXISTS ix_users_role ON users (role);

CREATE TABLE IF NOT EXISTS hara_advisories (
    id SERIAL PRIMARY KEY,
    hara_area_id INTEGER NOT NULL REFERENCES hara_bogor(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(64),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    updated_by_user_id INTEGER REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_hara_advisories_id ON hara_advisories (id);
CREATE INDEX IF NOT EXISTS ix_hara_advisories_hara_area_id ON hara_advisories (hara_area_id);
CREATE INDEX IF NOT EXISTS ix_hara_advisories_is_active ON hara_advisories (is_active);

CREATE TABLE IF NOT EXISTS hara_area_changes (
    id SERIAL PRIMARY KEY,
    hara_area_id INTEGER NOT NULL REFERENCES hara_bogor(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    action VARCHAR(32) NOT NULL,
    changed_fields JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_hara_area_changes_id ON hara_area_changes (id);
CREATE INDEX IF NOT EXISTS ix_hara_area_changes_hara_area_id ON hara_area_changes (hara_area_id);
CREATE INDEX IF NOT EXISTS ix_hara_area_changes_user_id ON hara_area_changes (user_id);

COMMENT ON COLUMN users.role IS 'Application role: user, expert, or admin.';
COMMENT ON TABLE hara_advisories IS 'Expert-authored public advisory content linked to hara areas.';
COMMENT ON TABLE hara_area_changes IS 'Audit log for expert-created and expert-updated hara area data.';
