from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mllo_web.app.api.services.graphdb_client import GraphDBClient
from mllo_web.app.api.services.namespace_filter import filter_results
from mllo_web.app.api.services.settings_model import load_settings
from mllo_web.core.graph.ontology_queries import PREFIX_QUERY


CONSTRUCT_NAMESPACE = "https://spec.industrialontologies.org/ontology/construct/"
LEGACY_NAMESPACES = (
    "http://www.semanticweb.org/mnd14/ml/",
    "https://spec.industrialontologies.org/ontology/core/Core/",
)


class NewIriCompatibilityTests(unittest.TestCase):
    def test_construct_namespace_is_exposed_and_visible(self) -> None:
        self.assertIn(f'("ml" "{CONSTRUCT_NAMESPACE}")', PREFIX_QUERY)
        self.assertIn(f'("iof-core" "{CONSTRUCT_NAMESPACE}")', PREFIX_QUERY)

        row = {"class": f"{CONSTRUCT_NAMESPACE}MachineLearningModel"}
        self.assertEqual(filter_results([row]), [row])

    def test_runtime_sources_do_not_use_legacy_ontology_iris(self) -> None:
        source_root = Path(__file__).resolve().parents[1] / "mllo_web"
        runtime_source = "\n".join(
            path.read_text(encoding="utf-8")
            for pattern in ("*.py", "*.ts", "*.tsx")
            for path in source_root.rglob(pattern)
        )

        for namespace in LEGACY_NAMESPACES:
            self.assertNotIn(namespace, runtime_source)
        self.assertNotIn("ml:executes", runtime_source)
        self.assertNotIn("iof-core:hasDateTimeValue", runtime_source)

    def test_graphdb_client_defaults_to_mllo5(self) -> None:
        self.assertEqual(GraphDBClient().default_repo, "mllo5")

    def test_legacy_saved_repo_settings_migrate_to_mllo5(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "mlle_settings.json"
            settings_path.write_text(
                json.dumps(
                    {
                        "graphdb_default_repo": "mllo4",
                        "graphdb_repo_allowlist": ["mllo4", "shared"],
                    }
                ),
                encoding="utf-8",
            )
            with patch(
                "mllo_web.app.api.services.settings_model.get_settings_path",
                return_value=settings_path,
            ):
                settings = load_settings()

        self.assertEqual(settings.graphdb_default_repo, "mllo5")
        self.assertEqual(settings.graphdb_repo_allowlist, ["mllo5", "shared"])


if __name__ == "__main__":
    unittest.main()
