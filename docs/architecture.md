# Registry architecture and trust boundaries

## Repository responsibilities

- **`xila-project/registry` (this repository, formerly `packages`):** reviewed developer keys and per-version registry entries (metadata only), their validation and their publication as static files at `registry.xila.dev`.
- **`xila-project/package_manager`:** every format and rule: archive and manifest formats, signature verification, registry entries and developer keys, and the `xila-package` CLI (`registry entry`, `registry verify`, `registry check`). It depends on neither Core nor this repository; this repository runs it at a pinned revision and keeps no validator of its own.
- **Application repositories** (for example `xila-project/applications`): build, sign and release the `.xpk` archives, which stay in their releases.
- **`xila-project/applications`** also holds the on-device `package` installer.

## Documents

| Document | Written by | Signed by | Answers |
|---|---|---|---|
| Developer manifest (`xila-package.json`, app repository) | developer | — | what to ship |
| Runtime manifest (`.xila/manifest.json`, inside the `.xpk`) | `xila-package bundle build` | developer key | exactly what the package contains (every file's SHA-256) |
| Registry entry (`packages/…/<version>.json`, here) | `xila-package registry entry` | repository key | where the archive is, and that the registry vouches for it |

An entry pins its archive by SHA-256 and size, so it transitively pins the signed runtime manifest; its copied fields must equal that manifest.

## Static distribution model

1. A developer releases a signed, immutable `.xpk` and submits its generated entry (and, the first time, its developer key).
2. Validation checks keys, placement, namespace authorization and each archive; a maintainer reviews provenance, content and permissions.
3. `main` is published unchanged to GitHub Pages. Archives are fetched from their release URLs; because entries pin their hash, any mirror or CDN can serve them without being trusted.
4. A client resolves `xila.clock` to `packages/xila/clock/<version>.json`, downloads the archive, and verifies it end to end before installing.

There is deliberately **no mandatory search** endpoint or dynamic server; a search index can be added later without changing lookup.

## Trust model

Devices will trust only the **repository key** and verify: repository key → developer key (with its namespaces) → package signature → file hashes. Two keys, two checks: the developer signature stays on the archive end to end, and the repository key vouches for both the entry and the developer key.

The formats and checks are specified in [package_manager's registry trust model](https://github.com/xila-project/package_manager/blob/main/docs/registry-trust.md):

- `root.json`, signed offline by the **root key**, names the keys allowed to sign the next root and the online **repository keys**;
- the repository key signs every entry and developer key (detached `.sig`), and an **index** (snapshot of every file's hash) with an increasing **version** and an **expiry**, so devices reject stale, rolled-back or mixed metadata.

**Not implemented yet:**

- Devices: the on-device installer still trusts a single developer key; it must verify from the pinned root key.
- Publishing every intermediate `root.json` version, needed once the root key rotates.
- A developer-key **revocation** list (until then, removing a key and re-signing is noticed by devices with a fresh index).

A SHA-256 digest or a developer signature alone does not grant permission to execute: capabilities and installation policy remain separate decisions.

## Constraints

- Published versions are immutable; a new release is a new entry.
- Formats and adapters must respect microcontroller memory limits: the package reader streams and never needs an entire archive in memory, and clients fetch one entry rather than a global catalog.
- Publication never builds or executes contributed code and never uses signing secrets on pull-request code.
