#!/usr/bin/env bash
# Validate the registry with the pinned xila-package and build the static site.
#
# usage: tools/validate.sh [base-ref]
#   base-ref: refuse changes to already published entries (pull requests).
# Set XILA_PACKAGE to an existing xila-package binary to skip installing one.
set -euo pipefail

# package_manager revision providing `xila-package registry check`.
PACKAGE_MANAGER_REVISION=04a770747f233666ed2de6c8aefae1fa6844efe3

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

builder="${XILA_PACKAGE:-}"
if [[ -z "$builder" ]]; then
  tools=".tools/xila-package-$PACKAGE_MANAGER_REVISION"
  if [[ ! -x "$tools/bin/xila-package" ]]; then
    cargo install --locked --quiet --root "$tools" \
      --git https://github.com/xila-project/package_manager --rev "$PACKAGE_MANAGER_REVISION" xila-package-builder
  fi
  builder="$root/$tools/bin/xila-package"
fi

# Published versions are immutable: a new release is a new <version>.json.
if [[ $# -ge 1 ]]; then
  changed="$(git diff --name-only --diff-filter=MDRT "$1"...HEAD -- packages)"
  if [[ -n "$changed" ]]; then
    printf 'published registry entries must not change:\n%s\n' "$changed" >&2
    exit 1
  fi
fi

downloads="$(mktemp -d)"
trap 'rm -rf "$downloads"' EXIT
find packages -name '*.json' -type f -print0 | sort -z | while IFS= read -r -d '' entry; do
  url="$(jq -er '.archive.url' "$entry")"
  case "$url" in https://*) ;; *) echo "$entry: archive URL must be HTTPS" >&2; exit 1 ;; esac
  curl --fail --silent --show-error --location --proto '=https' --retry 3 \
    --output "$downloads/${url##*/}" "$url"
done
"$builder" registry check "$root" --archives "$downloads"

# The static site serves the reviewed files unchanged.
rm -rf _site
mkdir _site
cp -R keys packages _site/
echo "Built _site with $(find _site/packages -name '*.json' | wc -l) registry entries"
