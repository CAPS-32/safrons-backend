#!/usr/bin/env bash
# init_db.sh
# Inisialisasi database pada PostgreSQL yang TERPASANG LANGSUNG di mesin
# (tanpa Docker). Untuk setup via Docker, pakai `docker compose up` saja.
#
# Langkah:
#   1. Buat database (jika belum ada)
#   2. Jalankan semua migrasi di database/migrations/ secara berurutan:
#        001_enable_postgis.sql   -> aktifkan PostGIS
#        002_seed_hara_bogor.sql  -> tabel hara_bogor + 191 baris data
#        003_post_import.sql      -> index spasial & komentar
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
MIGRATIONS="$REPO_ROOT/database/migrations"

# Muat kredensial dari database/.env bila ada.
if [[ -f "$REPO_ROOT/database/.env" ]]; then
    set -a; source "$REPO_ROOT/database/.env"; set +a
fi

PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5433}"
PGUSER="${PGUSER:-postgres}"
PGDATABASE="${PGDATABASE:-safrons}"
PGPASSWORD="${PGPASSWORD:-postgres}"
export PGPASSWORD

psql_admin() { psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d postgres "$@"; }
psql_db()    { psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -v ON_ERROR_STOP=1 "$@"; }

echo ">> [1/2] Membuat database '$PGDATABASE' (jika belum ada) ..."
if ! psql_admin -tAc "SELECT 1 FROM pg_database WHERE datname='$PGDATABASE'" | grep -q 1; then
    psql_admin -c "CREATE DATABASE \"$PGDATABASE\";"
    echo "   database dibuat."
else
    echo "   database sudah ada, dilewati."
fi

echo ">> [2/2] Menjalankan migrasi ..."
for f in "$MIGRATIONS"/*.sql; do
    echo "   - $(basename "$f")"
    psql_db -q -f "$f"
done

echo ">> Selesai. Tabel 'hara_bogor' siap dipakai."
