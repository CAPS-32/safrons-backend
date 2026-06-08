-- 006_seed_users.sql
-- Seed initial users for development: admin, expert, and normal user.
-- Idempotent: safe to run repeatedly (uses INSERT ... ON CONFLICT).

INSERT INTO users (id, email, full_name, hashed_password, role, is_active, created_at)
VALUES 
(
    1, 
    'admin@safrons.com', 
    'SAFRONS Administrator', 
    'pbkdf2_sha256$210000$WRsOR-Y92qiwT92HPROHng$nncmgmR_5_KFsko4UXTxwThsvLPA9Ba9EMlDkZFWFG0', 
    'admin', 
    TRUE, 
    NOW()
),
(
    2, 
    'expert@safrons.com', 
    'SAFRONS Expert', 
    'pbkdf2_sha256$210000$aBu9ZZLX1WIM0JXnMjSaAg$iG-Jbio2gEdfDy-K5QPVhyLy2T_JPOqVvN3vyRBCsUs', 
    'expert', 
    TRUE, 
    NOW()
),
(
    3, 
    'user@safrons.com', 
    'SAFRONS User (Petani)', 
    'pbkdf2_sha256$210000$puE3P_ZTHTeEjOTxpwog_w$rkV4bICUyliQVZOyQXjDNq1oO_JSM6GPcVwHvXkqWpg', 
    'user', 
    TRUE, 
    NOW()
)
ON CONFLICT (email) DO NOTHING;

-- Adjust standard PostgreSQL sequence after manual ID insertion
SELECT setval(pg_get_serial_sequence('users', 'id'), COALESCE(MAX(id), 1)) FROM users;
