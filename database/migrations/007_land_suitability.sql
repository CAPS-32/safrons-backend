-- 007_land_suitability.sql
-- Fasilitas penentuan kesesuaian lahan (land suitability) berbasis "bucket model"
-- / hukum minimum Liebig (limiting factor) untuk 3 tanaman simulasi:
--   jagung, kacang tanah, kakao.
--
-- Metode (FAO matching, mengikuti Djaenudin et al. 2011 / Permentan 79/2013 yang
-- dipakai di reference/penelitian/): tiap parameter lahan dicocokkan ke kelas
-- S1 (sangat sesuai) / S2 (cukup sesuai) / S3 (sesuai marginal) / N (tidak sesuai),
-- lalu KELAS AKHIR lahan = kelas TERBURUK dari semua parameter (limiting factor).
--
-- Parameter yang dinilai hanya yang tersedia & numeric di tabel hara_bogor:
--   ph_rata2 (pH), n_rata2 (N), p_rata2 (P), k_rata2 (K).
-- Nilai sentinel -9999 pada dataset = no-data; diperlakukan sebagai "tidak dapat
-- dinilai" dan menyebabkan kelas N (data tidak memenuhi syarat S1..S3).
--
-- Idempotent: aman dijalankan berulang.

-- =====================================================================
-- 1. Tabel kriteria bucket per tanaman per parameter
-- =====================================================================
-- Tiap parameter punya 3 rentang [min, max) untuk S1, S2, S3. Nilai di luar
-- ketiga rentang => N. Batas atas/bawah memakai NULL untuk "tak terhingga".
-- Pencocokan: value >= min (atau min NULL) AND value < max (atau max NULL).

CREATE TABLE IF NOT EXISTS crop_suitability_criteria (
    crop      VARCHAR(32)  NOT NULL,   -- 'jagung' | 'kacang_tanah' | 'kakao'
    parameter VARCHAR(8)   NOT NULL,   -- 'ph' | 'n' | 'p' | 'k'
    s1_min    NUMERIC,
    s1_max    NUMERIC,
    s2_min    NUMERIC,
    s2_max    NUMERIC,
    s3_min    NUMERIC,
    s3_max    NUMERIC,
    PRIMARY KEY (crop, parameter)
);

COMMENT ON TABLE crop_suitability_criteria IS
    'Ambang bucket kesesuaian lahan (S1/S2/S3) per tanaman per parameter tanah. Di luar rentang => N.';

-- =====================================================================
-- 2. Seed kriteria 3 tanaman x 4 parameter (= 12 baris)
-- =====================================================================
-- Sumber ambang:
--   * pH kakao: Tabel 5 kakao.md (Djaenudin et al. 2011) -> S1 6.0-7.0,
--     S2 5.0-6.0, S3 4.0-5.0, N <4.0/>8.0. Disederhanakan ke sisi masam
--     (data Bogor pH 4.4-6.56, tak ada yang basa) memakai batas atas longgar.
--   * pH jagung/kacang tanah: kriteria lahan kering Djaenudin et al. (2011),
--     S1 5.5-7.0, S2 5.0-5.5, S3 4.5-5.0.
--   * N/P/K: kelas status hara tanah Balittanah (rendah/sedang/tinggi) dipetakan
--     S3=rendah, S2=sedang, S1=tinggi, disetel ke skala nilai dataset
--     (N 1.3-39, P 5.8-91, K 75-3139). Tanaman semusim (jagung, kacang tanah)
--     lebih responsif ke hara sehingga ambangnya sedikit lebih menuntut
--     daripada kakao (tahunan, perakaran dalam).
--
-- Catatan: nilai parameter yang lebih tinggi dari batas atas S1 tetap dianggap
-- S1 (s1_max = NULL) karena kelebihan hara bukan pembatas pada model basic ini.

INSERT INTO crop_suitability_criteria
    (crop, parameter, s1_min, s1_max, s2_min, s2_max, s3_min, s3_max)
VALUES
    -- ---- JAGUNG ----
    ('jagung',       'ph', 5.5, 7.0, 5.0, 5.5, 4.5, 5.0),
    ('jagung',       'n',  5.0, NULL, 3.0, 5.0, 2.0, 3.0),
    ('jagung',       'p',  16.0, NULL, 8.0, 16.0, 6.0, 8.0),
    ('jagung',       'k',  300.0, NULL, 150.0, 300.0, 80.0, 150.0),

    -- ---- KACANG TANAH ----
    ('kacang_tanah', 'ph', 5.5, 7.0, 5.0, 5.5, 4.5, 5.0),
    ('kacang_tanah', 'n',  4.0, NULL, 2.5, 4.0, 1.5, 2.5),
    ('kacang_tanah', 'p',  16.0, NULL, 8.0, 16.0, 6.0, 8.0),
    ('kacang_tanah', 'k',  250.0, NULL, 120.0, 250.0, 70.0, 120.0),

    -- ---- KAKAO ----
    ('kakao',        'ph', 6.0, 7.0, 5.0, 6.0, 4.0, 5.0),
    ('kakao',        'n',  3.0, NULL, 2.0, 3.0, 1.0, 2.0),
    ('kakao',        'p',  12.0, NULL, 7.0, 12.0, 5.0, 7.0),
    ('kakao',        'k',  200.0, NULL, 100.0, 200.0, 60.0, 100.0)
ON CONFLICT (crop, parameter) DO NOTHING;

-- =====================================================================
-- 3. VIEW hasil kesesuaian per area x tanaman
-- =====================================================================
-- Selalu sinkron dengan data hara_bogor (tidak di-materialize).
-- Langkah:
--   a. crop_param : tiap area x (crop,parameter) dengan nilai aktual dari hara_bogor
--      (nilai -9999 dijadikan NULL agar jatuh ke kelas N).
--   b. graded     : hitung kelas tiap parameter (rank 1=S1 .. 4=N) via ambang.
--   c. final      : kelas akhir = rank terburuk (MAX), faktor pembatas = parameter
--      yang menghasilkan rank terburuk itu.

CREATE OR REPLACE VIEW hara_crop_suitability AS
WITH crop_param AS (
    SELECT
        h.id AS hara_area_id,
        c.crop,
        c.parameter,
        c.s1_min, c.s1_max, c.s2_min, c.s2_max, c.s3_min, c.s3_max,
        CASE
            WHEN v.val IS NULL OR v.val <= -9000 THEN NULL
            ELSE v.val
        END AS value
    FROM hara_bogor h
    CROSS JOIN crop_suitability_criteria c
    JOIN LATERAL (
        SELECT CASE c.parameter
            WHEN 'ph' THEN h.ph_rata2
            WHEN 'n'  THEN h.n_rata2
            WHEN 'p'  THEN h.p_rata2
            WHEN 'k'  THEN h.k_rata2
        END AS val
    ) v ON TRUE
),
graded AS (
    SELECT
        cp.hara_area_id,
        cp.crop,
        cp.parameter,
        cp.value,
        CASE
            WHEN cp.value IS NOT NULL
                 AND (cp.s1_min IS NULL OR cp.value >= cp.s1_min)
                 AND (cp.s1_max IS NULL OR cp.value <  cp.s1_max) THEN 1
            WHEN cp.value IS NOT NULL
                 AND (cp.s2_min IS NULL OR cp.value >= cp.s2_min)
                 AND (cp.s2_max IS NULL OR cp.value <  cp.s2_max) THEN 2
            WHEN cp.value IS NOT NULL
                 AND (cp.s3_min IS NULL OR cp.value >= cp.s3_min)
                 AND (cp.s3_max IS NULL OR cp.value <  cp.s3_max) THEN 3
            ELSE 4   -- di luar rentang atau no-data => N
        END AS rank
    FROM crop_param cp
),
agg AS (
    SELECT
        g.hara_area_id,
        g.crop,
        MAX(g.rank) AS worst_rank,   -- rank terburuk antar parameter (bucket)
        MAX(g.rank) FILTER (WHERE g.parameter = 'ph') AS ph_rank,
        MAX(g.rank) FILTER (WHERE g.parameter = 'n')  AS n_rank,
        MAX(g.rank) FILTER (WHERE g.parameter = 'p')  AS p_rank,
        MAX(g.rank) FILTER (WHERE g.parameter = 'k')  AS k_rank
    FROM graded g
    GROUP BY g.hara_area_id, g.crop
)
SELECT
    a.hara_area_id,
    a.crop,
    -- kelas akhir = kelas terburuk antar parameter (limiting factor / bucket)
    (ARRAY['S1','S2','S3','N'])[a.worst_rank] AS class,
    -- parameter pembatas: yang rank-nya = rank terburuk
    (
        SELECT ARRAY_AGG(g2.parameter ORDER BY g2.parameter)
        FROM graded g2
        WHERE g2.hara_area_id = a.hara_area_id
          AND g2.crop = a.crop
          AND g2.rank = a.worst_rank
    ) AS limiting_factors,
    -- kelas per-parameter untuk transparansi
    (ARRAY['S1','S2','S3','N'])[a.ph_rank] AS ph_class,
    (ARRAY['S1','S2','S3','N'])[a.n_rank]  AS n_class,
    (ARRAY['S1','S2','S3','N'])[a.p_rank]  AS p_class,
    (ARRAY['S1','S2','S3','N'])[a.k_rank]  AS k_class
FROM agg a;

COMMENT ON VIEW hara_crop_suitability IS
    'Kesesuaian lahan per area hara x tanaman (jagung/kacang_tanah/kakao). class = kelas terburuk antar parameter (bucket/limiting factor); limiting_factors = parameter penyebabnya.';
