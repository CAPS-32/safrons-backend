# SAFRONS Backend

Backend FastAPI untuk aplikasi SAFRONS. Backend ini menangani API, autentikasi
JWT, dan akses baca ke database PostgreSQL + PostGIS untuk data unsur hara
wilayah Bogor.

## Stack

- FastAPI
- PostgreSQL + PostGIS
- SQLAlchemy
- Pydantic Settings
- JWT bearer auth
- Pytest

## Pembagian Tanggung Jawab

- Backend menangani API, auth JWT, validasi request, response untuk frontend,
  dan dokumentasi endpoint.
- Database/GIS ditangani terpisah oleh role database/GIS. Backend hanya membaca
  tabel `hara_bogor` dan tidak mengubah struktur data GIS.

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
| `GET` | `/api/v1/hara/point?lon=106.8&lat=-6.6` | Mencari region hara berdasarkan titik koordinat map |

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
