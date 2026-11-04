#!/usr/bin/env bash
# Sign the validated registry into _site with the repository key.
#
# usage: XILA_REGISTRY_SIGNING_SEED_B64=… tools/sign.sh
#   The seed is the base64 of a raw 32-byte Ed25519 seed whose public key is a
#   repository key of root.json. Run tools/validate.sh first.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
builder="$(bash tools/xila-package.sh)"

: "${XILA_REGISTRY_SIGNING_SEED_B64:?repository signing seed is not set}"
secrets="$(mktemp -d)"
trap 'rm -rf "$secrets"' EXIT
chmod 700 "$secrets"
(umask 077 && printf '%s' "$XILA_REGISTRY_SIGNING_SEED_B64" | base64 --decode > "$secrets/repository.seed")

# Index valid for 30 days; publication re-signs it weekly.
rm -rf _site
"$builder" registry sign "$root" root.pub "$secrets/repository.seed" _site --expires-in-days 30
