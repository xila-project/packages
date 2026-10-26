"""Regression tests for the static package registry publisher."""
from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from tools.registry import ManifestError, build, collect, load_manifest, version_key


EXAMPLE = """schema = 1

[package]
name = "community.weather"
version = "{version}"
summary = "A small weather application"
license = "MIT"
source = "https://github.com/example/weather"

[[artifacts]]
target = "wasm32-wasip1"
minimum_xila_abi = 1
url = "https://github.com/example/weather/releases/download/v{version}/weather.xpk"
sha256 = "{digest}"
size = 10240
"""


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "packages"
        self.root.mkdir()

    def add_version(self, version="1.0.0", digest="a" * 64, data=None):
        path = self.root / "community" / "weather" / f"{version}.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data if data is not None else EXAMPLE.format(
            version=version, digest=digest), encoding="utf-8")
        return path

    def test_empty_registry(self):
        self.assertEqual(collect(self.root), {})
        output = Path(self.temp.name) / "public"
        build({}, output)
        self.assertTrue((output / "v1" / "registry.json").is_file())
        self.assertFalse((output / "v1" / "packages").exists())

    def test_sorted_versions_and_direct_lookup(self):
        self.add_version("1.0.0")
        self.add_version("1.3.0-rc.1")
        self.add_version("1.2.0")
        self.add_version("1.3.0")
        entries = collect(self.root)
        self.assertEqual([e["version"] for e in entries["community.weather"]],
                         ["1.3.0", "1.3.0-rc.1", "1.2.0", "1.0.0"])
        output = Path(self.temp.name) / "public"
        build(entries, output)
        self.assertTrue((output / "v1/packages/community/weather.json").exists())

    def test_rejects_invalid_hash(self):
        self.add_version(digest="not-a-sha256")
        with self.assertRaisesRegex(ManifestError, "sha256"):
            collect(self.root)

    def test_rejects_path_mismatch(self):
        path = self.add_version()
        path.write_text(path.read_text().replace("community.weather", "community.other"),
                        encoding="utf-8")
        with self.assertRaisesRegex(ManifestError, "package name"):
            collect(self.root)

    def test_rejects_duplicate_targets(self):
        path = self.add_version()
        doc = path.read_text()
        path.write_text(doc + doc.split("[[artifacts]]", 1)[1].join(
            ["[[artifacts]]", "[[artifacts]]"]), encoding="utf-8")
        with self.assertRaises((ManifestError,)):
            collect(self.root)

    def test_rejects_insecure_artifact_url(self):
        path = self.add_version()
        path.write_text(path.read_text().replace(
            "https://github.com/example/weather/releases",
            "http://github.com/example/weather/releases"), encoding="utf-8")
        with self.assertRaisesRegex(ManifestError, "HTTPS"):
            collect(self.root)

    def test_rejects_unknown_fields(self):
        path = self.add_version()
        path.write_text(path.read_text().replace(
            "source = ", "unreviewed = true\nsource = "), encoding="utf-8")
        with self.assertRaisesRegex(ManifestError, "package fields"):
            collect(self.root)

    def test_rejects_forged_version_path(self):
        path = self.add_version()
        other = path.with_name("2.0.0.toml")
        path.rename(other)
        with self.assertRaisesRegex(ManifestError, "version must match"):
            collect(self.root)

    def test_rejects_symlink(self):
        external = Path(self.temp.name) / "outside.toml"
        external.write_text("not a manifest", encoding="utf-8")
        (self.root / "link.toml").symlink_to(external)
        with self.assertRaisesRegex(ManifestError, "unexpected file"):
            collect(self.root)

    def test_rejects_numeric_prerelease_leading_zeros(self):
        with self.assertRaises(ManifestError):
            version_key("1.0.0-rc.01")

    def test_semantic_version_order(self):
        values = ["1.0.0-beta", "1.0.0-alpha.1", "1.0.0",
                  "1.0.0-alpha", "1.0.0-alpha.beta"]
        self.assertEqual(sorted(values, key=version_key),
                         ["1.0.0-alpha", "1.0.0-alpha.1",
                          "1.0.0-alpha.beta", "1.0.0-beta", "1.0.0"])


if __name__ == "__main__":
    unittest.main()
