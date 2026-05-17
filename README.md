# Safrons Backend

Backend untuk proyek Capstone Safrons. Menyediakan data **hara tanah**
(pH, N, P, K) area Bogor & sekitarnya, Jawa Barat, dalam database
PostgreSQL + PostGIS.

## Isi repositori

```
safrons-backend/
├── docker-compose.yml        # database PostgreSQL + PostGIS (cara termudah)
├── .env.example              # konfigurasi opsional untuk Docker
├── database/                 # migrasi & skrip database — lihat database/README.md
│   ├── migrations/           # SQL yang dijalankan berurutan
│   └── scripts/              # skrip setup native (tanpa Docker)
└── reference/
    └── data-hara-bogor/      # data GIS sumber (Shapefile) — arsip, read-only
```

## Persiapan — pilih SATU cara

### Cara A — Docker (disarankan, paling mudah, lintas OS)

Cocok untuk Windows/Mac/Linux. Hanya perlu **Docker Desktop** terpasang —
tidak perlu install PostgreSQL, PostGIS, atau GDAL.

```bash
git clone <url-repo>
cd safrons-backend
docker compose up -d
```

Saat pertama dijalankan, container otomatis membuat database `safrons`,
mengaktifkan PostGIS, dan mengisi tabel `hara_bogor` (191 baris). Tunggu
sampai status `healthy`:

```bash
docker compose ps
```

Database siap di **`localhost:5432`**. Selesai.

Perintah berguna:

| Perintah | Fungsi |
|----------|--------|
| `docker compose up -d`      | jalankan database |
| `docker compose ps`         | cek status |
| `docker compose logs -f db` | lihat log |
| `docker compose stop`       | hentikan (data tetap tersimpan) |
| `docker compose down`       | hapus container (data tetap, di volume) |
| `docker compose down -v`    | hapus container **+ data** (reset total) |

> Jika port 5432 sudah dipakai di mesinmu: `cp .env.example .env`, lalu
> ubah `DB_PORT` (mis. `5434`), lalu `docker compose up -d` lagi.

### Cara B — PostgreSQL native (tanpa Docker)

Hanya jika tidak memakai Docker. Perlu PostgreSQL + PostGIS terpasang
langsung di mesin. Lihat langkah lengkap di
[database/README.md](database/README.md).

## Koneksi database

Nilai default (Docker, tanpa `.env`):

| Parameter | Nilai     |
|-----------|-----------|
| Host      | `localhost` |
| Port      | `5432` (atau `DB_PORT`) |
| Database  | `safrons` |
| User      | `postgres` |
| Password  | `postgres` |

Connection string:

```
postgresql://postgres:postgres@localhost:5432/safrons
```

> Ganti password sebelum dipakai di lingkungan non-lokal.

## Data: tabel `hara_bogor`

191 poligon area, geometri **WGS 84 (SRID 4326)**. Kolom utama: `geom`,
`name`, `ph_rata2`, `n_rata2`, `p_rata2`, `k_rata2`, `lithology`,
`soil_great`, `slope__`. Detail & contoh query spasial ada di
[database/README.md](database/README.md).

Contoh — cari area hara pada satu titik koordinat (longitude, latitude):

```sql
SELECT name, ph_rata2, n_rata2, p_rata2, k_rata2
FROM hara_bogor
WHERE ST_Contains(geom, ST_SetSRID(ST_MakePoint(106.8, -6.6), 4326));
```
