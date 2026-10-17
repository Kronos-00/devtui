#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SOURCE="${1:?Usage: apply-patches.sh CLEAN_HELIX_SOURCE}"
EXPECTED="$(cat "$ROOT/prototype/helix/HELIX_COMMIT")"
[ "$(git -C "$SOURCE" rev-parse HEAD)" = "$EXPECTED" ] || {
  echo 'Source revision differs from HELIX_COMMIT' >&2; exit 1;
}
[ -z "$(git -C "$SOURCE" status --porcelain)" ] || {
  echo 'Refusing to apply patches over local source changes' >&2; exit 1;
}
while IFS= read -r name; do
  case "$name" in ''|'#'*) continue ;; esac
  case "$name" in *'/'*|*'..'*) echo 'Invalid patch manifest entry' >&2; exit 1 ;; esac
  git -C "$SOURCE" apply --check "$ROOT/prototype/helix/patches/$name"
  git -C "$SOURCE" apply --index "$ROOT/prototype/helix/patches/$name"
  printf 'Applied %s\n' "$name"
done < "$ROOT/prototype/helix/patches/series"
ACTUAL_TREE="$(git -C "$SOURCE" write-tree)"
EXPECTED_TREE="$(cat "$ROOT/prototype/helix/HELIX_TREE")"
[ "$ACTUAL_TREE" = "$EXPECTED_TREE" ] || {
  printf 'Patched source tree mismatch: expected %s, received %s\n' "$EXPECTED_TREE" "$ACTUAL_TREE" >&2
  exit 1
}
printf '%s\n' "$ACTUAL_TREE"
