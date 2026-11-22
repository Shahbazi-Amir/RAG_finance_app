#!/usr/bin/env bash
# Creates a separate offline source bundle. Never modifies SOURCE_REPO.
set -euo pipefail
umask 077
BUNDLE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
: "${SOURCE_REPO:?Provide actual local Git checkout of RAG_finance_app}"
: "${LAB_ROOT:?Provide fresh, isolated target folder}"
[[ "$LAB_ROOT" = /* ]] || { echo 'STOP_LAB_ROOT_NOT_ABSOLUTE' >&2; exit 70; }
[[ "$LAB_ROOT" != *PRODUCT_FIRST_START_PREP* && "$LAB_ROOT" != *CENTRAL_FIRST_START_20261121* && "$LAB_ROOT" != *[[:space:]]* ]] || { echo 'STOP_PROTECTED_PATH' >&2; exit 70; }
[[ ! -e "$LAB_ROOT/lab.env" ]] || { echo 'STOP_PREEXISTING_LAB_ENV' >&2; exit 70; }
[[ "$(git -C "$SOURCE_REPO" rev-parse --is-inside-work-tree)" == true ]] || { echo 'STOP_INVALID_GIT_REPO' >&2; exit 70; }
expected="9ff95a59570f5f6c6188479d9c37cf684ef836c599e89d9faa2bb0e17a4946f7"
[[ "$(shasum -a 256 "$BUNDLE_ROOT/MIGRATIONS_001_010_PINNED.tsv" | awk '{print $1}')" == "$expected" ]] || { echo 'STOP_MIGRATION_MANIFEST_SHA256' >&2; exit 70; }
mkdir -p "$LAB_ROOT/source" "$LAB_ROOT/work" "$LAB_ROOT/secrets"
chmod 0700 "$LAB_ROOT" "$LAB_ROOT/work" "$LAB_ROOT/secrets"
chmod 0755 "$LAB_ROOT/source"
cp "$BUNDLE_ROOT/MIGRATIONS_001_010_PINNED.tsv" "$LAB_ROOT/source/manifest.tsv"
tail -n +2 "$BUNDLE_ROOT/MIGRATIONS_001_010_PINNED.tsv" | while IFS=$'\t' read -r ver direction sha path blob; do
  [[ "$ver" =~ ^0(0[1-9]|10)$ || "$ver" == '010' ]] || { echo 'STOP_BAD_MIGRATION_VERSION' >&2; exit 70; }
  [[ "$direction" == UP || "$direction" == DOWN ]] || { echo 'STOP_BAD_DIRECTION' >&2; exit 70; }
  name="${path##*/}"
  [[ "$name" == *.sql && "$name" != 011* ]] || { echo 'STOP_UNEXPECTED_SQL_SOURCE_PATH' >&2; exit 70; }
  git -C "$SOURCE_REPO" cat-file -e "$sha^{commit}" || { echo "STOP_MISSING_LOCAL_GIT_COMMIT_$sha" >&2; exit 70; }
  git -C "$SOURCE_REPO" show "$sha:$path" > "$LAB_ROOT/source/$name"
  [[ "$(git hash-object "$LAB_ROOT/source/$name")" == "$blob" ]] || { echo "STOP_GIT_BLOB_MISMATCH_$name" >&2; exit 70; }
done
for name in db55_verify_staging.sql db55_no_dispatch_bridge.sql; do
  git -C "$SOURCE_REPO" show "bfd6b1d9ed23e5f4cc6f126b579f90d7c877a7a6:infra/postgres/staging/$name" > "$LAB_ROOT/source/$name"
done
[[ "$(git hash-object "$LAB_ROOT/source/db55_verify_staging.sql")" == 'e2115d8cebc649fdf05d3fbee4ef435ad5f39a47' ]] || { echo 'STOP_DB55_VERIFIER_PIN' >&2; exit 70; }
[[ "$(git hash-object "$LAB_ROOT/source/db55_no_dispatch_bridge.sql")" == 'a79e46c87857eb2b77fd26863e1cf85fead31b38' ]] || { echo 'STOP_DB55_BRIDGE_PIN' >&2; exit 70; }
[[ "$(find "$LAB_ROOT/source" -maxdepth 1 -name '*.sql' | wc -l | tr -d ' ')" == 22 ]] || { echo 'STOP_UNEXPECTED_SQL_FILE_COUNT' >&2; exit 70; }
chmod 0644 "$LAB_ROOT/source"/*
( cd "$LAB_ROOT/source" && shasum -a 256 *.sql manifest.tsv > SHA256SUMS )
# Unique, newly named scratch Docker resources; no chance of using a demo volume.
lab_id="$(openssl rand -hex 6)"
{
  printf 'LAB_PROJECT=ragfinance_f3_db_lab_%s\n' "$lab_id"
  printf 'LAB_VOLUME=rag_finance_f3_LAB_%s\n' "$lab_id"
  printf 'LAB_RESTORE_VOLUME=rag_finance_f3_RESTORE_%s\n' "$lab_id"
  printf 'LAB_DB=rag_finance_f3_lab\n'
  printf 'LAB_SECRETS=%q\n' "$LAB_ROOT/secrets"
  printf 'LAB_SOURCE=%q\n' "$LAB_ROOT/source"
  printf 'LAB_WORK=%q\n' "$LAB_ROOT/work"
} > "$LAB_ROOT/lab.env"
chmod 0600 "$LAB_ROOT/lab.env"
chmod 0644 "$LAB_ROOT/source/SHA256SUMS"
echo 'SOURCE_BUNDLE=22_SQL_FILES_PIN_VERIFIED'
echo 'DEMO_DATABASE=UNTOUCHED'
echo "LAB_PROJECT=$(sed -n 's/^LAB_PROJECT=//p' "$LAB_ROOT/lab.env")"
