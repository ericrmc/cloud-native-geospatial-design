#!/usr/bin/env bash
#
# Regenerate Confluence pages and push to all configured target spaces.
#
# Usage:
#   ./push-all.sh            Dry run — shows what would happen, no HTTP calls.
#   ./push-all.sh --apply    Real push to every configured space.
#
# Each space's push runs in a subshell so env vars from one cannot leak
# into the next. Per-space state files (state-<host>-<space>.json in this
# directory) keep the page-ID mappings independent — one space's push
# cannot clobber another's.
#
# Pre-flight: verifies both env files exist, that the CONF_EMAIL placeholder
# has been replaced, and that CONF_TOKEN is non-empty. Stops at the first
# failure so partial pushes do not silently progress.
#
# Credentials live in ~/.config/atlassian/<space>.env (chmod 600 each,
# parent dir chmod 700). See confluence/README.md "Credentials" for setup.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ENV_DIR="$HOME/.config/atlassian"

# Each entry: "label|env-file-path". Add more spaces by appending here.
TARGETS=(
  "Planning Victoria — CNG|$ENV_DIR/planningvic-cng.env"
  "Public Transport Victoria — CNG|$ENV_DIR/publictransportvic-cng.env"
)

APPLY=0
case "${1:-}" in
  "")        APPLY=0 ;;
  --apply)   APPLY=1 ;;
  -h|--help) sed -n '3,20p' "$0" | sed 's/^# \{0,1\}//' ; exit 0 ;;
  *)         echo "Unknown argument: $1" >&2 ; echo "Usage: $0 [--apply]" >&2 ; exit 2 ;;
esac

# ---------- pre-flight ----------

echo "=== Pre-flight ==="

env_files=()
for entry in "${TARGETS[@]}"; do
  env_files+=("${entry#*|}")
done

for f in "${env_files[@]}"; do
  if [ ! -f "$f" ]; then
    echo "Missing env file: $f" >&2
    exit 1
  fi
done

echo "Current CONF_EMAIL lines:"
grep -H '^CONF_EMAIL=' "${env_files[@]}"

if grep -q "# paste your Atlassian Cloud email" "${env_files[@]}"; then
  echo ""
  echo "Error: at least one env file still has the email placeholder. Fill in CONF_EMAIL before running." >&2
  exit 1
fi

if grep -qE '^CONF_TOKEN=$' "${env_files[@]}"; then
  echo ""
  echo "Error: at least one env file has an empty CONF_TOKEN." >&2
  exit 1
fi

echo ""
echo "Credentials look filled in."

# ---------- convert ----------

echo ""
echo "=== Regenerating Confluence pages ==="
cd "$HERE"
python3 convert.py

# ---------- push to each space ----------

push_one() {
  local label="$1"
  local env_file="$2"

  echo ""
  echo "=== $label ==="

  # Subshell isolates env vars from the parent and from other pushes.
  (
    set -a
    # shellcheck disable=SC1090
    source "$env_file"
    set +a

    if [ "$APPLY" = "1" ]; then
      python3 push.py
    else
      DRY_RUN=1 python3 push.py
    fi
  )
}

for entry in "${TARGETS[@]}"; do
  label="${entry%%|*}"
  env_file="${entry#*|}"
  push_one "$label" "$env_file"
done

echo ""
if [ "$APPLY" = "1" ]; then
  echo "=== Done. All spaces updated. ==="
  echo "State files: $(ls "$HERE"/state-*.json 2>/dev/null | xargs -n1 basename | paste -sd, -)"
else
  echo "=== Done (dry run). Re-run with --apply to actually push. ==="
fi
