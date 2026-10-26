#!/usr/bin/env python3
"""Build an unsigned static package registry preview from contributor manifests.

Host-only tooling; no package code is executed and no artifacts are downloaded.
The JSON output is not authenticated and must not be trusted by Xila devices.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tomllib
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = ROOT / "packages"
OUTPUT = ROOT / "_site"
NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
VERSION = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)
HASH = re.compile(r"^[0-9a-f]{64}$")
TARGET = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}$")


class ManifestError(ValueError):
    pass


def check(condition: bool, message: str) -> None:
    if not condition:
        raise ManifestError(message)


def string(value: object, field: str, limit: int = 256) -> str:
    check(isinstance(value, str) and 0 < len(value) <= limit and
          value == value.strip() and bool(value),
          f"{field}: expected a nonempty trimmed string (maximum {limit} characters)")
    return value


def https_url(value: object, field: str) -> str:
    value = string(value, field, 2048)
    parsed = urlsplit(value)
    try:
        valid_port = parsed.port in (None, 443)
    except ValueError as error:
        raise ManifestError(f"{field}: invalid port") from error
    check(parsed.scheme == "https" and bool(parsed.hostname) and
          not parsed.username and not parsed.password and not parsed.fragment and
          valid_port, f"{field}: expected an HTTPS URL without credentials or fragments")
    return value


def version_key(value: str) -> tuple:
    match = VERSION.fullmatch(value)
    check(match is not None, f"invalid semantic version: {value!r}")
    major, minor, patch, prerelease, metadata = match.groups()
    check(metadata is None, "build metadata is not supported for immutable versions")
    ordering = ()
    if prerelease is not None:
        parts = prerelease.split(".")
        check(all(not (part.isdigit() and len(part) > 1 and part[0] == "0")
                  for part in parts), "leading zeros in numeric prerelease identifier")
        ordering = tuple((0, int(part)) if part.isdigit() else (1, part)
                         for part in parts)
    return int(major), int(minor), int(patch), int(prerelease is None), ordering


def load_manifest(path: Path, root: Path = MANIFESTS) -> dict:
    relative = path.relative_to(root)
    check(len(relative.parts) == 3 and path.suffix == ".toml",
          "expected packages/<namespace>/<name>/<version>.toml")
    namespace, package_name = relative.parts[:2]
    for value in (namespace, package_name):
        check(1 <= len(value) <= 48 and NAME.fullmatch(value) is not None,
              f"invalid namespace or package name: {value}")
    version = path.stem
    version_key(version)
    try:
        with path.open("rb") as stream:
            source = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ManifestError(str(error)) from error

    check(set(source) == {"schema", "package", "artifacts"},
          "top-level fields must be schema, package, artifacts")
    check(type(source["schema"]) is int and source["schema"] == 1,
          "unsupported manifest schema")
    package = source["package"]
    check(isinstance(package, dict) and
          {"name", "version", "summary", "license", "source"} <= package.keys() and
          package.keys() <= {"name", "version", "summary", "license", "source", "homepage"},
          "invalid package fields")
    identifier = f"{namespace}.{package_name}"
    check(package["name"] == identifier, f"package name must be {identifier}")
    check(package["version"] == version, f"version must match filename: {version}")
    package["summary"] = string(package["summary"], "summary", 500)
    package["license"] = string(package["license"], "license", 128)
    package["source"] = https_url(package["source"], "source")
    if "homepage" in package:
        package["homepage"] = https_url(package["homepage"], "homepage")

    artifacts = source["artifacts"]
    check(isinstance(artifacts, list) and 1 <= len(artifacts) <= 32,
          "artifacts must contain 1-32 entries")
    targets = set()
    for artifact in artifacts:
        check(isinstance(artifact, dict) and
              set(artifact) == {"target", "minimum_xila_abi", "url", "sha256", "size"},
              "invalid artifact fields")
        target = string(artifact["target"], "target", 64)
        check(TARGET.fullmatch(target) is not None and target not in targets,
              "invalid or duplicate artifact target")
        targets.add(target)
        check(type(artifact["minimum_xila_abi"]) is int and
              0 <= artifact["minimum_xila_abi"] <= 65535,
              "minimum_xila_abi out of range")
        url = https_url(artifact["url"], "artifact URL")
        check(urlsplit(url).path.endswith(".xpk"),
              "artifact URL must point to an .xpk file")
        check(isinstance(artifact["sha256"], str) and HASH.fullmatch(artifact["sha256"]) is not None,
              "sha256 must be a lowercase 64-character hexadecimal digest")
        check(type(artifact["size"]) is int and 0 < artifact["size"] < 2 ** 31,
              "artifact size must be 1-2147483647 bytes")

    return {"name": identifier, "version": version,
            "summary": package["summary"], "license": package["license"],
            "source": package["source"],
            **({"homepage": package["homepage"]} if "homepage" in package else {}),
            "artifacts": artifacts}


def collect(root: Path = MANIFESTS) -> dict[str, list[dict]]:
    check(root.exists() and root.is_dir(), "packages directory is missing")
    packages = defaultdict(list)
    seen = set()
    for path in sorted(root.rglob("*")):
        check(not path.is_symlink(), f"symbolic links are forbidden in the package registry: {path}")
        if path.is_dir():
            continue
        if path == root / ".gitkeep":
            continue
        check(path.is_file() and path.suffix == ".toml",
              f"unexpected file in packages directory: {path}")
        try:
            entry = load_manifest(path, root)
        except ManifestError as error:
            raise ManifestError(f"{path.relative_to(root)}: {error}") from error
        identity = (entry["name"], entry["version"])
        check(identity not in seen, f"duplicate package version: {identity}")
        seen.add(identity)
        packages[entry["name"]].append(entry)
    for versions in packages.values():
        versions.sort(key=lambda entry: version_key(entry["version"]), reverse=True)
    return dict(sorted(packages.items()))


def build(packages: dict[str, list[dict]], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    root = output / "v1"
    root.mkdir(parents=True, exist_ok=True)
    # The root is deliberately not a package catalog. Direct identity lookups only.
    write_json(root / "registry.json", {
        "format_version": 1,
        "description": "Unauthenticated development preview; not a production trust root",
        "package_count": len(packages),
    })
    for identity, versions in packages.items():
        namespace, name = identity.split(".", 1)
        write_json(root / "packages" / namespace / f"{name}.json", {
            "format_version": 1, "name": identity, "versions": versions,
        })


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "build"))
    args = parser.parse_args()
    try:
        packages = collect()
        print(f"Validated {sum(map(len, packages.values()))} versions across "
              f"{len(packages)} packages")
        if args.command == "build":
            if OUTPUT.exists():
                check(OUTPUT.is_dir() and not OUTPUT.is_symlink(),
                      "unexpected _site path; refusing to replace it")
                shutil.rmtree(OUTPUT)
            build(packages, OUTPUT)
            print(f"Generated static preview under {OUTPUT}")
        return 0
    except ManifestError as error:
        print(f"Registry validation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
