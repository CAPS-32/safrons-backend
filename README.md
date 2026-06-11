<div align="center">
  <img src="public\safrons.png" alt="SAFRONS Logo" height="100">

  # SAFRONS Backend

  Layanan backend API berbasis FastAPI, PostgreSQL, dan PostGIS untuk mendukung analisis kesuburan hara regional dan evaluasi kesesuaian lahan pertanian.

  [![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688?style=flat-square&logo=fastapi)](#)
  [![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python)](#)
  [![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0.0-D11919?style=flat-square)](#)
  [![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql)](#)
  [![PostGIS](https://img.shields.io/badge/PostGIS-3-002E5B?style=flat-square)](#)
  [![JWT Auth](https://img.shields.io/badge/JWT%20Auth-Bearer-black?style=flat-square&logo=json-web-tokens)](#)
  [![Pytest](https://img.shields.io/badge/Pytest-8.0.0-0A9EDC?style=flat-square&logo=pytest)](#)
</div>

---

Backend FastAPI untuk aplikasi SAFRONS. Backend ini menangani API, autentikasi
JWT, dan akses baca ke database PostgreSQL + PostGIS untuk data unsur hara
wilayah Bogor. User juga bisa menyimpan region hara dari titik map yang dipilih.
Expert dapat menambahkan advisory, memperbarui data hara, dan membuat area hara
baru agar bisa dilihat user.

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
- `slope__`
- `texture_of`

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
- `slope__`
- `texture_of`

Contoh query spasial untuk mencari area hara dari satu titik koordinat:

```sql
SELECT name, ph_rata2, n_rata2, p_rata2, k_rata2
FROM hara_bogor
WHERE ST_Contains(geom, ST_SetSRID(ST_MakePoint(106.8, -6.6), 4326));
```

## CARA LAIN - Setup Database Native (tanpa Docker)

Detail setup database native ada di [database/README.md](database/README.md).

---

## Panduan Deployment

### 1. Deployment ke Railway (Paling Direkomendasikan)

Railway mendukung deployment berbasis Dockerfile secara otomatis. Backend SAFRONS sudah dilengkapi dengan `Dockerfile` di root folder yang otomatis dideteksi oleh Railway untuk mem-build Docker image dan menjalankannya.

#### Langkah-langkah:
1. **Buat Database PostgreSQL dengan PostGIS di Railway**:
   - Jangan gunakan tombol bawaan \"Provision PostgreSQL\" karena database PostgreSQL standar di Railway tidak menyertakan modul PostGIS secara default. Jika database PostgreSQL bawaan sudah otomatis terbuat, silakan **hapus database bawaan** tersebut agar tidak membingungkan.
   - Klik **New** -> **Docker Image** -> Masukkan name image: `postgis/postgis:16-3.4` (atau versi postgis stabil lainnya).
   - Masuk ke tab **Variables** pada service database PostGIS baru tersebut dan tambahkan variabel environment database dasar (seperti `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, dan `PORT` jika diperlukan).

2. **Deploy Backend**:
   - Klik **New** -> **GitHub Repo** -> Pilih repositori `safrons-backend` Anda.
   - Railway akan otomatis mendeteksi `Dockerfile` di root folder untuk mem-build Docker image backend dan menjalankan container-nya.

3. **Konfigurasi Environment Variables di Service Backend**:
   Masuk ke service backend di Railway, buka tab **Variables**, lalu tambahkan variabel berikut:
   - `DATABASE_URL`: Isi dengan URL koneksi ke database PostGIS yang Anda buat di atas, contoh: `postgresql://<user>:<password>@<host>:<port>/<database>` (atau gunakan reference variable bawaan Railway).
   - `APP_ENV`: `production` atau `staging`
   - `BACKEND_CORS_ORIGINS`: `["https://<domain-frontend-anda>", "http://localhost:5173"]` (Sesuaikan dengan domain frontend Anda)
   - `JWT_SECRET_KEY`: *(Generate string random yang panjang dan aman)*
   - `JWT_ALGORITHM`: `HS256`
   - `ACCESS_TOKEN_EXPIRE_MINUTES`: `60` (atau sesuai kebutuhan)
   - `PORT`: `8000` *(Backend kami menggunakan `${PORT:-8000}` untuk mendeteksi port dinamis dari Railway)*

4. **Verifikasi**:
   - Setelah deployment selesai, buka domain publik yang disediakan oleh Railway untuk service backend.
   - Akses endpoint health check pada domain tersebut: `/health` (misalnya `https://<domain-backend-anda>/health`).
   - Migrasi database dan seeding data hara sebanyak 191 poligon akan berjalan secara otomatis di background saat aplikasi pertama kali dijalankan.

---

### 2. Deployment ke VPS (Ubuntu/Debian)

Deployment di VPS menggunakan FastAPI (Uvicorn), systemd untuk service manager, PostgreSQL + PostGIS native, dan Nginx sebagai reverse proxy dengan SSL dari Certbot.

#### Langkah 1: Install Dependencies System
Masuk ke VPS via SSH, lalu install package yang diperlukan:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git nginx curl

# Install PostgreSQL 16 & PostGIS 3
sudo apt install -y postgresql-16 postgresql-16-postgis-3
```

#### Langkah 2: Setup Database PostgreSQL & PostGIS
1. Masuk ke prompt PostgreSQL:
   ```bash
   sudo -i -u postgres psql
   ```
2. Buat database dan user baru:
   ```sql
   CREATE DATABASE safrons;
   CREATE USER safrons WITH PASSWORD 'safrons_secure_password';
   GRANT ALL PRIVILEGES ON DATABASE safrons TO safrons;
   \c safrons
   CREATE EXTENSION IF NOT EXISTS postgis;
   GRANT ALL ON SCHEMA public TO safrons;
   \q
   ```

#### Langkah 3: Clone Repository & Setup Virtual Environment
1. Clone repositori ke `/var/www/safrons-backend`:
   ```bash
   sudo mkdir -p /var/www/safrons-backend
   sudo chown -R $USER:$USER /var/www/safrons-backend
   git clone <URL_REPO_ANDA> /var/www/safrons-backend
   cd /var/www/safrons-backend
   ```
2. Buat virtual environment & install app:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -e .
   ```
3. Buat file `.env` di `/var/www/safrons-backend/.env`:
   ```env
   APP_NAME="SAFRONS API"
   APP_ENV="production"
   DEBUG=False
   DATABASE_URL="postgresql://safrons:safrons_secure_password@localhost:5432/safrons"
   BACKEND_CORS_ORIGINS=["https://domain-frontend.com"]
   JWT_SECRET_KEY="generate-secret-key-yang-sangat-aman-di-sini"
   JWT_ALGORITHM="HS256"
   ACCESS_TOKEN_EXPIRE_MINUTES=60
   ```

#### Langkah 4: Setup Systemd Service
Buat file service systemd agar FastAPI berjalan di background dan otomatis restart saat VPS reboot.
1. Buat file konfigurasi service:
   ```bash
   sudo nano /etc/systemd/system/safrons-backend.service
   ```
2. Masukkan konfigurasi berikut:
   ```ini
   [Unit]
   Description=SAFRONS Backend FastAPI Service
   After=network.target postgresql.service

   [Service]
   User=ubuntu
   WorkingDirectory=/var/www/safrons-backend
   EnvironmentFile=/var/www/safrons-backend/.env
   ExecStart=/var/www/safrons-backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
   *(Sesuaikan `User=ubuntu` dengan username VPS Anda).*
3. Reload systemd, jalankan, dan aktifkan service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl start safrons-backend
   sudo systemctl enable safrons-backend
   ```
4. Cek status service:
   ```bash
   sudo systemctl status safrons-backend
   ```

#### Langkah 5: Setup Nginx & SSL (Certbot)
1. Buat file konfigurasi server block Nginx baru:
   ```bash
   sudo nano /etc/nginx/sites-available/safrons-backend
   ```
2. Tambahkan konfigurasi reverse proxy:
   ```nginx
   server {
       listen 80;
       server_name api.domain-anda.com; # Ganti dengan domain/subdomain Anda

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```
3. Aktifkan konfigurasi dan restart Nginx:
   ```bash
   sudo ln -s /etc/nginx/sites-available/safrons-backend /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```
4. Install SSL gratis menggunakan Certbot:
   ```bash
   sudo apt install -y certbot python3-certbot-nginx
   sudo certbot --nginx -d api.domain-anda.com
   ```
   Ikuti petunjuk untuk menyelesaikan setup SSL HTTPS.

5. Selesai! Backend Anda sekarang berjalan aman menggunakan HTTPS di VPS.

