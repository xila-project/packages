#!/usr/bin/env bash
# Print the path of xila-package at the pinned package_manager revision,
# installing it under .tools/ on first use. Set XILA_PACKAGE to reuse an
# existing binary.
set -euo pipefail

# package_manager revision providing `xila-package registry check | sign | verify-signed`.
PACKAGE_MANAGER_REVISION=3d0ab51d7f3c852b69f6578ea241b4d9cc6ca672

if [[ -n "${XILA_PACKAGE:-}" ]]; then
  echo "$XILA_PACKAGE"
  exit 0
fi
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tools="$root/.tools/xila-package-$PACKAGE_MANAGER_REVISION"
if [[ ! -x "$tools/bin/xila-package" ]]; then
  # Own target directory: a shared CARGO_TARGET_DIR/build.target-dir can hold
  # stale artifacts from other package_manager revisions.
  CARGO_TARGET_DIR="$root/.tools/target" cargo install --locked --quiet --root "$tools" \
    --git https://github.com/xila-project/package_manager --rev "$PACKAGE_MANAGER_REVISION" xila-package-builder >&2
fi
echo "$tools/bin/xila-package"
