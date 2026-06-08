# Database — Safrons Backend

Inisialisasi database PostgreSQL + PostGIS untuk menyimpan data hara tanah
(area Bogor & sekitarnya, Jawa Barat) yang sumbernya berupa file Shapefile
di folder `reference/data-hara-bogor/`.

## Kenapa database, bukan file?

Folder `reference/data-hara-bogor/` berisi satu dataset GIS dalam dua format:

- **Shapefile** (`Hara_pHNPK_Bogorsekitarnya.*`) — 191 poligon, CRS **WGS 84
  (EPSG:4326)**, satuan derajat lintang/bujur. Ini sumber yang dipakai.
- **`hara-bogor.geojson`** — export dari dataset yang sama, tapi CRS-nya
  EPSG:32348 (UTM zone 48S, satuan meter). **Tidak dipakai** supaya tidak
  perlu reproject.
- `*.qmd` — metadata QGIS (bukan data).

Disimpan di PostgreSQL + PostGIS agar bisa di-query secara spasial dan
diakses backend lewat SQL, bukan membaca file flat. Semua geometri
disimpan dengan **SRID 4326 (geodetic WGS 84)**.

## Struktur folder

```
database/
├── .env.example              kredensial untuk setup native (Cara B)
├── migrations/               dijalankan BERURUTAN (urut nama file)
│   ├── 001_enable_postgis.sql     aktifkan ekstensi PostGIS
│   ├── 002_seed_hara_bogor.sql    CREATE TABLE hara_bogor + 191 INSERT
│   ├── 003_post_import.sql        index spasial GIST + komentar kolom
│   ├── 004_saved_regions.sql      tabel users + saved_regions
│   ├── 005_expert_persona.sql     role user + hara_advisories + audit
│   ├── 006_seed_users.sql         seed admin/expert/user awal
│   └── 007_land_suitability.sql   kriteria + view kesesuaian lahan tanaman
└── scripts/
    ├── init_db.sh            setup di PostgreSQL native (Cara B)
    └── generate_seed.sh       regenerasi 002_seed_*.sql dari Shapefile
```

`002_seed_hara_bogor.sql` adalah hasil konversi Shapefile (via `ogr2ogr`)
yang **di-commit ke repo**. Karena datanya sudah berupa SQL biasa, proses
setup tidak lagi butuh GDAL/`ogr2ogr` — baik lewat Docker maupun native.
Migrasi `004` menyiapkan tabel backend untuk auth user dan region yang
disimpan user.

## Cara setup

### Cara A — Docker (disarankan)

Tidak menyentuh folder ini secara manual. `docker-compose.yml` di root repo
otomatis menjalankan semua file `migrations/` saat container pertama kali
dibuat. Lihat [README utama](../README.md).

### Cara B — PostgreSQL native (tanpa Docker)

Perlu PostgreSQL + PostGIS terpasang langsung di mesin.

1. Pasang ekstensi PostGIS sesuai versi PostgreSQL-mu, mis. untuk versi 16:

   ```bash
   sudo apt-get install -y postgresql-16-postgis-3
   ```

2. Salin & sesuaikan kredensial (port, user, password):

   ```bash
   cp database/.env.example database/.env
   ```

3. Jalankan setup — membuat database lalu menjalankan semua migrasi:

   ```bash
   ./database/scripts/init_db.sh
   ```

   Output sukses diakhiri `Selesai. Tabel 'hara_bogor' siap dipakai.` dan
   migrasi `003` menampilkan **191** fitur dengan **srid 4326**.

## Regenerasi data (jarang dipakai)

Hanya jika file Shapefile sumber berubah. Perlu `ogr2ogr` (paket GDAL):

```bash
./database/scripts/generate_seed.sh   # perbarui 002_seed_hara_bogor.sql
```

Lalu commit perubahan `002_seed_hara_bogor.sql`.

## Tabel `hara_bogor`

| Kolom        | Tipe                          | Keterangan                |
|--------------|-------------------------------|---------------------------|
| `id`         | serial (PK)                   | FID dari shapefile        |
| `geom`       | geometry(MultiPolygon, 4326)  | poligon area, WGS 84      |
| `objectid`   | numeric                       | OBJECTID asli             |
| `unitname`   | varchar                       | jenis bentang lahan       |
| `name`       | varchar                       | nama area                 |
| `lithology`  | varchar                       | litologi                  |
| `soil_great` | varchar                       | great soil group          |
| `slope__`    | varchar                       | kelas kemiringan (%)      |
| `ph_rata2`   | numeric                       | pH rata-rata              |
| `n_rata2`    | numeric                       | Nitrogen rata-rata        |
| `p_rata2`    | numeric                       | Fosfor rata-rata          |
| `k_rata2`    | numeric                       | Kalium rata-rata          |
| ...          |                               | kolom atribut lain ikut   |

Index: `hara_bogor_pk` (primary key) dan `idx_hara_bogor_geom` (GIST spasial).

Contoh query spasial — cari area hara yang memuat satu titik koordinat:

```sql
SELECT name, ph_rata2, n_rata2, p_rata2, k_rata2
FROM hara_bogor
WHERE ST_Contains(geom, ST_SetSRID(ST_MakePoint(106.8, -6.6), 4326));
```

## Kesesuaian lahan tanaman (migrasi `007`)

Fasilitas penentuan kesesuaian lahan untuk **3 tanaman simulasi**: `jagung`,
`kacang_tanah`, `kakao`. Metode **bucket / hukum minimum Liebig (limiting
factor)** mengikuti FAO matching (Djaenudin et al. 2011 / Permentan 79/2013,
lihat `reference/penelitian/`): tiap parameter dicocokkan ke kelas
**S1 / S2 / S3 / N**, lalu kelas akhir lahan = **kelas terburuk** antar parameter.

Parameter yang dinilai hanya atribut numeric yang ada di `hara_bogor`:
**pH (`ph_rata2`), N (`n_rata2`), P (`p_rata2`), K (`k_rata2`)**. Nilai sentinel
`-9999` = no-data dan otomatis menghasilkan kelas **N**.

### Tabel `crop_suitability_criteria`

Ambang bucket per tanaman per parameter (PK `(crop, parameter)`), 3×4 = 12 baris.
Kolom `s1_min..s3_max` mendefinisikan rentang `[min, max)` tiap kelas; di luar
ketiga rentang → N. `max` = `NULL` berarti tak terbatas (kelebihan hara bukan
pembatas pada model basic ini).

### View `hara_crop_suitability`

Selalu sinkron dengan data hara (bukan tabel materialized). Kolom:

| Kolom              | Keterangan                                            |
|--------------------|-------------------------------------------------------|
| `hara_area_id`     | FK ke `hara_bogor.id`                                  |
| `crop`             | `jagung` / `kacang_tanah` / `kakao`                   |
| `class`            | kelas akhir `S1`/`S2`/`S3`/`N` (= terburuk antar param)|
| `limiting_factors` | array parameter penyebab kelas terburuk               |
| `ph_class` … `k_class` | kelas per parameter (transparansi)                |

Contoh — tanaman apa yang cocok di satu titik koordinat:

```sql
SELECT s.crop, s.class, s.limiting_factors
FROM hara_bogor h
JOIN hara_crop_suitability s ON s.hara_area_id = h.id
WHERE ST_Contains(h.geom, ST_SetSRID(ST_MakePoint(106.8, -6.6), 4326))
ORDER BY s.crop;
```
