#!/usr/bin/env bash
# generate_seed.sh
# Mengubah Shapefile hara tanah menjadi file SQL portabel:
#   database/migrations/002_seed_hara_bogor.sql
#
# File SQL hasilnya DI-COMMIT ke repo, sehingga proses setup database
# (native maupun Docker) TIDAK butuh GDAL/ogr2ogr lagi.
#
# Jalankan skrip ini HANYA jika data sumber di reference/data-hara-bogor/
# berubah. Untuk setup biasa, cukup pakai init_db.sh atau Docker.
#
# Prasyarat: ogr2ogr (paket GDAL).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

SHP="$REPO_ROOT/reference/data-hara-bogor/Hara_pHNPK_Bogorsekitarnya.shp"
OUT="$REPO_ROOT/database/migrations/002_seed_hara_bogor.sql"

if ! command -v ogr2ogr >/dev/null 2>&1; then
    echo "ERROR: ogr2ogr tidak ditemukan. Install paket GDAL dulu." >&2
    exit 1
fi
if [[ ! -f "$SHP" ]]; then
    echo "ERROR: Shapefile tidak ditemukan: $SHP" >&2
    exit 1
fi

echo ">> Membuat $OUT dari Shapefile ..."
# -t_srs EPSG:4326  : pastikan geometri dalam WGS 84 (geodetic)
# -dim 2            : buang dimensi Z (selalu 0 pada data ini)
# -nlt MULTIPOLYGON : tipe geometri konsisten
ogr2ogr -f PGDump "$OUT" "$SHP" \
    -nln hara_bogor \
    -t_srs EPSG:4326 \
    -nlt MULTIPOLYGON \
    -dim 2 \
    -lco GEOMETRY_NAME=geom \
    -lco FID=id \
    -lco CREATE_SCHEMA=OFF \
    -lco SPATIAL_INDEX=NONE

echo ">> Selesai. Jangan lupa commit perubahan $OUT."
