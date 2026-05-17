-- 002_post_import.sql
-- Dijalankan SETELAH import_hara.sh selesai mengimpor tabel `hara_bogor`.
-- Menambahkan primary key, index spasial, dan komentar kolom.
-- Idempotent: aman dijalankan berulang.

-- Index spasial GIST untuk mempercepat query ST_Contains / ST_Intersects dll.
CREATE INDEX IF NOT EXISTS idx_hara_bogor_geom
    ON hara_bogor USING GIST (geom);

-- Komentar tabel & kolom kunci (memudahkan dokumentasi & tooling).
COMMENT ON TABLE  hara_bogor             IS 'Data hara tanah area Bogor & sekitarnya, Jawa Barat. Geometri WGS 84 (SRID 4326).';
COMMENT ON COLUMN hara_bogor.geom        IS 'Poligon area, MultiPolygon SRID 4326 (geodetic WGS 84).';
COMMENT ON COLUMN hara_bogor.ph_rata2    IS 'pH tanah rata-rata.';
COMMENT ON COLUMN hara_bogor.n_rata2     IS 'Nitrogen (N) rata-rata.';
COMMENT ON COLUMN hara_bogor.p_rata2     IS 'Fosfor (P) rata-rata.';
COMMENT ON COLUMN hara_bogor.k_rata2     IS 'Kalium (K) rata-rata.';

-- Verifikasi: jumlah baris & SRID geometri harus 4326.
SELECT count(*) AS jumlah_fitur,
       ST_SRID(geom) AS srid
FROM hara_bogor
GROUP BY ST_SRID(geom);
