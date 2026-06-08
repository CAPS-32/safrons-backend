# SAFRONS Backend

Backend FastAPI untuk aplikasi SAFRONS. Backend ini menangani API, autentikasi
JWT, dan akses baca ke database PostgreSQL + PostGIS untuk data unsur hara
wilayah Bogor. User juga bisa menyimpan region hara dari titik map yang dipilih.
Expert dapat menambahkan advisory, memperbarui data hara, dan membuat area hara
baru agar bisa dilihat user.

## Stack

- FastAPI
- PostgreSQL + PostGIS
- SQLAlchemy
- Pydantic Settings
- JWT bearer auth
- Pytest

## Pembagian Tanggung Jawab

- Backend menangani API, auth JWT, role access, validasi request, response untuk
  frontend, dan dokumentasi endpoint.
- Database/GIS seed awal ditangani terpisah oleh role database/GIS. Backend
  membaca tabel `hara_bogor`, lalu role expert dapat menambah dan mengubah data
  hara melalui endpoint khusus.

## Setup Lokal dengan DOCKER - (disarankan, paling mudah)

Dari folder ini:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Edit `.env` jika username, password, port, atau secret lokal berbeda.

Jalankan database:

```powershell
docker compose up -d
docker compose ps
```

Koneksi database default dari `.env.example`:

```text
postgresql://safrons:safrons@localhost:5436/safrons
```

Jalankan API:

```powershell
uvicorn app.main:app --reload
```

Buka:

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/docs
```

Jalankan test:

```powershell
pytest
```

## Endpoint API

### Health

| Method | Path | Fungsi |
|---|---|---|
| `GET` | `/health` | Cek status API |
| `GET` | `/api/v1/health` | Cek status API versi v1 |

### Auth JWT

| Method | Path | Fungsi |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Membuat user baru |
| `POST` | `/api/v1/auth/login` | Login dan mendapatkan JWT access token |
| `GET` | `/api/v1/auth/me` | Mengambil data user yang sedang login |

Gunakan token login seperti ini:

```text
Authorization: Bearer <access_token>
```

Contoh register:

```json
{
  "email": "user@example.com",
  "password": "strong-password",
  "full_name": "Backend User"
}
```

Register selalu membuat role `user`. Role yang tersedia:

- `user`: membaca data hara dan mengelola saved regions miliknya sendiri
- `expert`: membuat advisory, update data hara, dan membuat area hara baru
- `admin`: semua akses expert, plus promosi role user

Contoh login:

```json
{
  "email": "user@example.com",
  "password": "strong-password"
}
```

### API Unsur Hara Untuk Map

Endpoint ini disiapkan untuk frontend map. Setiap region/poligon bisa
ditampilkan bersama nilai unsur haranya.

| Method | Path | Fungsi |
|---|---|---|
| `GET` | `/api/v1/hara/areas` | Mengambil semua region sebagai GeoJSON `FeatureCollection` |
| `GET` | `/api/v1/hara/areas/{id}` | Mengambil detail satu region hara |
| `GET` | `/api/v1/hara/areas/{id}/diagnosis` | Mengambil diagnosis sistem pakar otomatis untuk region hara |
| `GET` | `/api/v1/hara/areas/{id}/advisories` | Mengambil advisory aktif dari expert untuk region hara |
| `GET` | `/api/v1/hara/point?lon=106.8&lat=-6.6` | Mencari region hara berdasarkan titik koordinat map |
| `GET` | `/api/v1/hara/point/diagnosis?lon=106.8&lat=-6.6` | Mencari region dari titik map lalu mengembalikan diagnosis sistem pakar |

Setiap feature hara berisi:

- geometri poligon
- `id`
- `name`
- `ph_rata2`
- `n_rata2`
- `p_rata2`
- `k_rata2`
- `lithology`
- `soil_great`
- `slope__`

### Sistem Pakar Hara

Endpoint diagnosis bersifat publik dan menghasilkan rekomendasi umum berbasis
data `hara_bogor` yang sudah ada. Sistem pakar memakai rule deterministik:

- pH diklasifikasikan dari kelas reaksi tanah umum.
- N, P, dan K diklasifikasikan relatif terhadap distribusi dataset saat ini,
  karena data tidak menyimpan satuan atau metode ekstraksi laboratorium.
- `slope__` dipakai untuk memberi peringatan risiko erosi/nutrient loss.
- Baris `Water`, `No Data`, atau nilai sentinel `-9999` menghasilkan status
  `insufficient_data`.

Perhitungan dilakukan dalam urutan berikut:

1. Backend mengambil `HaraFeature` dari `hara_bogor` berdasarkan `area_id` atau
   titik `lon`/`lat`.
2. Jika `name` adalah `Water`/`No Data`, atau salah satu nilai `ph_rata2`,
   `n_rata2`, `p_rata2`, `k_rata2` bernilai `NULL` atau `-9999`, response
   langsung berstatus `insufficient_data`.
3. Jika data valid, setiap faktor dihitung menjadi `status`, `status_label`,
   `severity`, dan `message`.
4. Recommendation dibuat dari faktor yang perlu perhatian. Prioritasnya:
   terrain/slope, pH, lalu N, P, K.

Klasifikasi pH:

| Nilai `ph_rata2` | Status | Severity |
|---|---|---|
| `< 4.5` | `very_acid` | `critical` |
| `4.5 - < 5.6` | `acid` | `attention` |
| `5.6 - < 6.6` | `slightly_acid` | `watch` |
| `6.6 - < 7.6` | `neutral` | `info` |
| `7.6 - < 8.6` | `slightly_alkaline` | `watch` |
| `>= 8.6` | `alkaline` | `attention` |

Klasifikasi N/P/K memakai batas persentil dataset `hara_bogor` saat ini, bukan
ambang pupuk umum, karena kolom data tidak menyimpan satuan atau metode uji lab.

| Faktor | Very low | Low | Medium | High | Very high |
|---|---:|---:|---:|---:|---:|
| `n_rata2` | `<= 1.989691` | `<= 2.450581` | `<= 4.158587` | `<= 5.5412572` | `> 5.5412572` |
| `p_rata2` | `<= 6.672457` | `<= 7.790811` | `<= 8.022388` | `<= 8.970512` | `> 8.970512` |
| `k_rata2` | `<= 146.97696` | `<= 197.49262` | `<= 331.24494` | `<= 447.9228` | `> 447.9228` |

Severity N/P/K:

| Status | Severity |
|---|---|
| `very_low` | `critical` |
| `low` | `attention` |
| `medium` | `info` |
| `high`, `very_high` | `watch` |

Klasifikasi slope:

| Nilai `slope__` | Status | Severity |
|---|---|---|
| `<2` | `flat` | `info` |
| `0-8`, `2-8` | `gentle` | `info` |
| `9-15` | `moderate` | `watch` |
| `16-25`, `26-40` | `steep` | `attention` |
| `41-60`, `>60` | `very_steep` | `critical` |
| kosong/tidak dikenal | `unknown` | `watch` |

Sumber dan catatan verifikasi:

- pH: memakai tabel `pH H2O` pada *Petunjuk Teknis Analisis Kimia Tanah,
  Tanaman, Air, dan Pupuk*. Sumber ini terverifikasi sebagai item resmi
  Repositori Kementerian Pertanian, handle
  <https://repository.pertanian.go.id/handle/123456789/14959>, terbit 2005,
  penulis Sulaeman, Suparto, dan Eviati, penerbit Balai Penelitian Tanah.
  PDF-nya tersedia di:
  <https://repository.pertanian.go.id/bitstream/handle/123456789/14959/juknis_kimia.pdf?sequence=1>.
  Pada Lampiran 3 "Kriteria penilaian hasil analisis tanah", dokumen tersebut
  memuat kelas pH H2O: `<4,5`, `4,5-5,5`, `5,5-6,5`, `6,6-7,5`,
  `7,6-8,5`, dan `>8,5`.
- N/P/K: ambang pada sistem ini bukan ambang pupuk dari literatur. Ambang
  dihitung dari distribusi data lokal `hara_bogor` dengan persentil 20, 40, 60,
  dan 80 karena dataset tidak menyimpan satuan atau metode ekstraksi lab untuk
  `n_rata2`, `p_rata2`, dan `k_rata2`. Fungsi SQL yang dipakai untuk menghitung
  persentil adalah `percentile_cont`, yang didokumentasikan PostgreSQL:
  <https://www.postgresql.org/docs/current/functions-aggregate.html>.
- Slope: kelas `slope__` mengikuti nilai kelas yang sudah ada di dataset
  `hara_bogor`, bukan angka dari FAO. Pemakaian slope sebagai indikator risiko
  erosi didukung oleh panduan FAO untuk pemetaan erosi, yang memakai kelas
  kemiringan dalam matriks erodibilitas:
  <https://www.fao.org/4/x5302e/x5302e07.htm>.

Contoh response ringkas:

```json
{
  "rule_set_version": "hara-general-v1",
  "status": "ready",
  "summary": "High-priority constraints found for Slope.",
  "factors": [
    {
      "key": "ph",
      "label": "pH",
      "value": 5.016667,
      "status": "acid",
      "status_label": "Acid",
      "severity": "attention",
      "message": "Soil reaction is acidic and may limit nutrient availability."
    }
  ],
  "recommendations": []
}
```

### Saved Regions

Endpoint ini membutuhkan JWT bearer token. Frontend mengirim titik yang dipilih
user di map, lalu backend mencari region `hara_bogor` yang memuat titik itu dan
menyimpannya untuk user tersebut.

| Method | Path | Fungsi |
|---|---|---|
| `POST` | `/api/v1/saved-regions` | Simpan region dari titik map |
| `GET` | `/api/v1/saved-regions` | Ambil semua region tersimpan milik user |
| `GET` | `/api/v1/saved-regions/{id}` | Ambil satu region tersimpan milik user |
| `PATCH` | `/api/v1/saved-regions/{id}` | Ubah label region tersimpan |
| `DELETE` | `/api/v1/saved-regions/{id}` | Hapus region tersimpan |

Contoh request:

```json
{
  "lon": 106.8,
  "lat": -6.6,
  "label": "Lahan contoh"
}
```

Response berisi titik yang dipilih, `hara_area_id`, label, waktu simpan, dan
feature hara yang sudah ter-resolve.

### Admin

Endpoint ini membutuhkan JWT user dengan role `admin`.

| Method | Path | Fungsi |
|---|---|---|
| `PATCH` | `/api/v1/admin/users/{user_id}/role` | Mengubah role user menjadi `user`, `expert`, atau `admin` |

Contoh request:

```json
{
  "role": "expert"
}
```

Admin pertama dibuat atau dipromosikan manual lewat database/seed.

### Expert

Endpoint ini membutuhkan JWT user dengan role `expert` atau `admin`.

| Method | Path | Fungsi |
|---|---|---|
| `POST` | `/api/v1/expert/hara/areas/{area_id}/advisories` | Membuat advisory publik untuk region hara |
| `PATCH` | `/api/v1/expert/advisories/{advisory_id}` | Mengubah advisory |
| `PATCH` | `/api/v1/expert/hara/areas/{area_id}` | Mengubah sebagian field data hara |
| `POST` | `/api/v1/expert/hara/areas` | Membuat area hara baru dengan GeoJSON Polygon/MultiPolygon |

Contoh update hara:

```json
{
  "ph_rata2": 6.2,
  "soil_great": "Updated soil"
}
```

Contoh advisory:

```json
{
  "title": "Perbaikan pH tanah",
  "content": "Aplikasikan dolomit berdasarkan hasil pengukuran lapangan.",
  "category": "soil",
  "is_active": true
}
```

Setiap perubahan expert ke area hara dicatat di tabel audit
`hara_area_changes`.

## Environment Values

| Variable | Fungsi |
|---|---|
| `APP_NAME` | Nama tampilan API |
| `APP_ENV` | Environment runtime, misalnya `local`, `staging`, atau `production` |
| `DEBUG` | Mengaktifkan mode debug untuk development lokal |
| `API_V1_PREFIX` | Prefix route API versi v1 |
| `BACKEND_CORS_ORIGINS` | Daftar origin frontend yang diizinkan |
| `DATABASE_URL` | URL koneksi SQLAlchemy ke PostgreSQL/PostGIS |
| `POSTGRES_USER` | User PostgreSQL untuk Docker Compose |
| `POSTGRES_PASSWORD` | Password PostgreSQL untuk Docker Compose |
| `POSTGRES_DB` | Nama database PostgreSQL untuk Docker Compose |
| `DB_PORT` | Port PostgreSQL di host lokal |
| `JWT_SECRET_KEY` | Secret untuk menandatangani JWT |
| `JWT_ALGORITHM` | Algoritma JWT, saat ini `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Durasi berlaku access token |

## Struktur Folder

```text
safrons-backend/
├── app/                      # Aplikasi FastAPI
│   ├── api/                  # Router endpoint
│   ├── core/                 # Config dan security
│   ├── db/                   # Session dan base SQLAlchemy
│   ├── models/               # Model database milik backend
│   └── schemas/              # Schema request/response
├── tests/                    # Test API
├── database/                 # Setup PostGIS dan seed data hara
│   ├── migrations/
│   └── scripts/
├── reference/
│   └── data-hara-bogor/      # File GIS sumber, read-only reference
├── docker-compose.yml        # Database lokal PostgreSQL + PostGIS
├── pyproject.toml            # Dependency dan konfigurasi tooling Python
└── README.md
```

## Data: `hara_bogor`

Seed database berisi 191 area poligon dengan geometri WGS 84 / SRID 4326.
Migrasi backend juga membuat tabel `users` dan `saved_regions`.
Migrasi expert menambahkan `role`, `hara_advisories`, dan
`hara_area_changes`.
Kolom utama:

- `geom`
- `name`
- `ph_rata2`
- `n_rata2`
- `p_rata2`
- `k_rata2`
- `lithology`
- `soil_great`
- `slope__`

Contoh query spasial untuk mencari area hara dari satu titik koordinat:

```sql
SELECT name, ph_rata2, n_rata2, p_rata2, k_rata2
FROM hara_bogor
WHERE ST_Contains(geom, ST_SetSRID(ST_MakePoint(106.8, -6.6), 4326));
```

## CARA LAIN - Setup Database Native (tanpa Docker)

Detail setup database native ada di [database/README.md](database/README.md).
