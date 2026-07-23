from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PluginMarketplaceTests(unittest.TestCase):
    def test_repo_marketplace_points_to_stageflow_plugin_root(self) -> None:
        marketplace = json.loads((ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
        plugin_manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))

        self.assertEqual(marketplace["name"], "stage-flow")
        self.assertEqual(marketplace["interface"]["displayName"], "Stage Flow")

        self.assertEqual(len(marketplace["plugins"]), 1)
        entry = marketplace["plugins"][0]
        self.assertEqual(entry["name"], plugin_manifest["name"])
        self.assertEqual(entry["source"], {"source": "local", "path": "./"})
        self.assertEqual(entry["policy"]["installation"], "AVAILABLE")
        self.assertEqual(entry["policy"]["authentication"], "ON_INSTALL")
        self.assertNotIn("products", entry["policy"])
        self.assertEqual(entry["category"], "Productivity")


if __name__ == "__main__":
    unittest.main()
