-- 001_enable_postgis.sql
-- Aktifkan ekstensi PostGIS pada database. Dijalankan SETELAH database dibuat.
-- Idempotent: aman dijalankan berulang.

CREATE EXTENSION IF NOT EXISTS postgis;

-- Verifikasi versi PostGIS yang aktif.
SELECT postgis_full_version();
