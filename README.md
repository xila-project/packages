# Xila package registry

This repository is the package registry for [Xila](https://github.com/xila-project/core): **metadata only**, like `crates.io-index`. It holds one entry per released package version and the developer keys allowed to publish them; the `.xpk` archives stay where each project releases them. It is served as static files at [registry.xila.dev](https://registry.xila.dev/), so a client fetches exactly the entry it needs: no search service, database or running server.

> [!IMPORTANT]
> Entries are not yet signed by the **repository key**, and there is no signed index with expiry. Until then the registry proves which developer key signed each archive, but devices cannot yet authenticate the registry itself. See [security and architecture](docs/architecture.md).

## Layout

```text
keys/developers/<id>.json                       developer (publisher) keys
packages/<identifier, dots as />/<version>.json registry entries
```

For example, `xila.pixel-painter` 0.1.0 is `packages/xila/pixel-painter/0.1.0.json`. The formats are defined in [`xila-project/package_manager`](https://github.com/xila-project/package_manager): [registry entry](https://github.com/xila-project/package_manager/blob/main/schemas/registry-entry.schema.json) and [developer key](https://github.com/xila-project/package_manager/blob/main/schemas/developer-key.schema.json).

- A **developer key** (`id`, `author`, Ed25519 `public_key`, `namespaces`) signs package manifests and may only publish identifiers whose first label is in its `namespaces` (`xila-project` publishes `xila.*`).
- A **registry entry** pins one released archive by HTTPS URL, SHA-256 and size, names its `publisher`, and copies identity, compatibility, capabilities, display name and metadata from the archive's signed manifest. It is **generated from the archive, never written by hand**.

## Publishing a version

1. Release a signed `.xpk` in your project (for example with the [reusable packaging workflow](https://github.com/xila-project/package_manager/blob/main/docs/reusable-wasm-package-workflow.md)).
2. Generate its entry with [`xila-package`](https://github.com/xila-project/package_manager/tree/main/crates/builder):
   ```sh
   xila-package registry entry app.xpk publisher.pub <publisher-id> https://…/app.xpk packages/<namespace>/<name>/<version>.json
   ```
3. Open a pull request. The first contribution of a publisher also adds its `keys/developers/<id>.json`.

Published versions are **immutable**: a pull request may add entries but never modify or delete one; release a new version instead.

## Validation and publication

[`tools/validate.sh`](tools/validate.sh) installs `xila-package` at a pinned package_manager revision, then:

- refuses changes to already published entries (pull requests);
- downloads every entry's archive and runs `xila-package registry check --archives`, which checks key files, entry placement and canonical form, namespace authorization, and each archive's size, SHA-256, signature and copied fields;
- builds `_site/` from `keys/` and `packages/`, unchanged.

**Validate package registry** runs it on pull requests and on `main`, with read-only permissions. **Publish package registry** runs it on `main` and deploys `_site/` to GitHub Pages. Neither workflow builds or executes application code, and neither uses signing secrets. Run `bash tools/validate.sh` locally (needs `cargo`, `curl` and `jq`; set `XILA_PACKAGE` to reuse an existing binary).

## Licensing

Refer to [LICENSE](LICENSE). Package authors are responsible for stating appropriate licenses for their own published applications.
