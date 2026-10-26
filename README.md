# Xila package registry

This repository is the community-facing source of package publication declarations for [Xila](https://github.com/xila-project/core).

The intended registry is **static and directly addressable**: clients will eventually request an individual package descriptor by its identifier instead of downloading an entire catalog. No search service, database, or permanently running server is required.

> [!IMPORTANT]
> This repository currently implements an **unauthenticated, development-only registry preview**. The JSON representation, package declaration schema, signing format, and cryptographic trust root are **not yet the production Xila package protocol**. Do not implement trusted installations against this preview or treat an HTTPS download as an authorized package. See [security and architecture](docs/architecture.md).

## Contributing an application

1. Build the application and publish an immutable `.xpk` archive in a release of your project. The final archive specification is being defined in [Xila core issue #402](https://github.com/xila-project/core/issues/402).
2. Record the archive's SHA-256 hash, its exact byte length, its target, and the minimum compatible Xila application binary interface version.
3. Create `packages/<namespace>/<application>/<version>.toml` using [the example](examples/weather-1.0.0.toml). The identifier is `<namespace>.<application>`.
4. Open a pull request. Validation checks the declaration, versions, naming convention, and basic metadata. A maintainer must still review provenance, content, permissions and ownership.

Use a distinct namespace to avoid collisions. The `xila` namespace is reserved for official applications by convention; this convention is not yet enforced by an authenticated publisher policy. Existing versions must never be replaced with different bytes. Prefer creating a new version.

**The archive files are not stored in Git.** The example uses an external release URL, and generated descriptors point to that immutable release artifact.

## Local development

Requires Python 3.12 or later; no third-party Python dependencies are required.

```sh
python -m unittest discover -s tests -v
python tools/registry.py validate
python tools/registry.py build
```

The generated preview is written to `_site/v1`:

```text
v1/
  registry.json
  packages/
    community/
      weather.json
```

The registry is initially empty, so its default output contains only `registry.json`. The sample manifest under `examples/` is intentionally **not published**. A package descriptor is generated only after an actual manifest is contributed under `packages/`.

## Automation

- **Validate package registry**: runs unit tests, checks submitted declarations, and uploads a generated preview on pull requests and changes to the main branch. This workflow has read-only GitHub permissions.
- **Publish static package registry preview**: after a change is merged into the main branch, regenerates the preview and publishes it using GitHub Pages. This workflow never builds or executes third-party application code and does not use secret signing keys.

To enable GitHub Pages publishing, configure repository **Settings → Pages → Build and deployment → Source: GitHub Actions**. No custom domain is required. The GitHub Pages preview is **not a trusted software distribution endpoint** until the production signature protocol is implemented.

Before accepting outside contributions, configure GitHub branch protection to require successful validation and maintainer approval. Publishing must never consume unreviewed pull-request code with privileged credentials.

## Long-term separation of responsibilities

The planned `Xila-Project/package-manager` repository will be the Rust workspace shared by both this registry and `xila/core`. The Rust workspace should eventually own the authoritative archive and manifest schema, signature verification, offline installation logic, repository metadata, and host-side authoring tools. This repository should then use the shared host tooling instead of independently maintaining the preview Python publisher.

Follow the [architecture notes](docs/architecture.md), [package format issue #402](https://github.com/xila-project/core/issues/402), and [repository design issue #492](https://github.com/xila-project/core/issues/492).

## Licensing

Refer to [LICENSE](LICENSE). Package authors are responsible for stating appropriate licenses for their own published applications.
