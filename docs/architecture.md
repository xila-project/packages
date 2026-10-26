# Registry architecture and trust boundaries

## Repository responsibilities

- **`Xila-Project/packages` (this repository):** Reviewed contributor submissions, package release declarations, publishing workflows, and static files served by GitHub Pages.
- **`Xila-Project/package-manager` (planned):** Reusable Rust libraries and authoring tools. This repository must not depend on `xila/core`. The core system and package registry can both depend on stable, versioned package-manager crates.
- **`Xila-Project/core`:** Xila-specific adapters for the virtual file system, network and application loader, plus the package manager executable and application policy.

A possible Rust workspace:

```text
package-manager/
  crates/
    package-format/          # bounded no_std archive/manifest parser and writer
    verification/            # migrate the existing Xila core verification crate
    package-installer/       # offline installation transactions via injected storage traits
    package-repository/      # optional authenticated index and version selection
  tools/
    package-builder/         # host-only archive creator, signing and inspection
    registry-publisher/      # host-only validation and static repository generation
```

The split is illustrative, not a commitment to these exact crate names or dependencies. **The `verification` crate already exists in `xila/core/libraries/verification` (merged in core pull request #518). Migrate it with tests and stable interfaces rather than creating a second cryptographic implementation.** Separate interfaces from executable and platform glue. No unconditional network or desktop dependencies in constrained-device crates.

Related work: [overall application package management #308](https://github.com/xila-project/core/issues/308), [archive format #402](https://github.com/xila-project/core/issues/402), [verification #490](https://github.com/xila-project/core/issues/490), [offline installer #491](https://github.com/xila-project/core/issues/491), [repository #492](https://github.com/xila-project/core/issues/492), [command line #493](https://github.com/xila-project/core/issues/493), and [host builder #494](https://github.com/xila-project/core/issues/494).

## Static distribution model

1. Contributors submit source provenance, release identity, declared compatibility and immutable artifact hashes.
2. Validation checks the declaration. Reviews and publisher policy decide whether a package may be admitted.
3. A trusted publisher generates canonical, **signed** index metadata (not implemented yet).
4. GitHub Pages or any static HTTPS origin serves metadata at a predictable path.
5. GitHub Releases or an interchangeable object store hosts content-addressed immutable package archives.
6. Xila fetches and authenticates metadata, streams the archive through the verifier and delegates activation to its offline installer.

There is deliberately **no mandatory search** endpoint or dynamic server. The client resolves `community.weather` to a known descriptor path. Later, a separate static website search index or optional search service may be added without changing package lookup. An update check can consult only installed package identifiers.

## Security constraints

The current publisher is a **non-production preview**. A SHA-256 digest without authenticated metadata does not establish publisher identity or permission to execute the binary. Do not silently promote preview JSON to a trusted protocol.

The production format needs explicit answers for:

- Canonical signed bytes, metadata versions, trusted keys, key rotation, expiry and rollback resistance.
- Registry and publisher identity; reserved namespaces and conflicts between repositories.
- Immutable release artifacts and authenticated hash/size/target bindings.
- Authenticating index descriptors without downloading an unbounded global catalog.
- Secure resolution of download redirects, safe TLS policies, bounds for network and parsing, replay resistance, and offline installations.
- Review policy and privileges. A repository signature must not automatically grant filesystem or device capabilities.

All formats and adapters must obey the memory limits for microcontrollers. The package reader should be streaming and should not require an entire archive in memory. The final TAR-versus-CPIO decision and canonical manifest are authoritative in issue #402, **not** in this registry preview.

## Future migration to the shared Rust workspace

The Python program in this repository is a small, dependency-free bootstrap for a static registry proof of concept. It is **not** an additional canonical Xila manifest implementation. When the package-manager workspace publishes an authoritative host validator and index generator, switch this repository's workflows to invoke that shared tool at a pinned version, and remove the provisional serializer.

Do not have `package-manager` depend on this registry: that would introduce a dependency cycle. The registry depends on the shared tools, never the reverse.
