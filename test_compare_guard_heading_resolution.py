import unittest
import pathlib
import sys
import tempfile
import os

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "standalone_clone"))

from comment_preserve_publish import _load_auto_heading_baseline, _resolve_auto_heading_title, _resolve_changed_heading_titles, _save_auto_heading_baseline
from scdp_compare_guard import _find_heading_section_bounds


class CompareGuardHeadingResolutionTests(unittest.TestCase):
    def test_heading_wrapped_by_inline_comment_marker_still_matches(self):
        storage = (
            "<h1>Executive Summary</h1>"
            "<p>Before.</p>"
            '<h1><ac:inline-comment-marker ac:ref="ref-1">Naming Conventions</ac:inline-comment-marker></h1>'
            "<h2>Policy Naming Conventions</h2>"
            "<p>Target content.</p>"
            "<h1>Physical Design</h1>"
            "<p>After.</p>"
        )

        bounds = _find_heading_section_bounds(storage, "Naming Conventions", heading_level=1)

        self.assertIsNotNone(bounds)
        section_html = storage[bounds["heading_start"]:bounds["section_end"]]
        self.assertIn("Policy Naming Conventions", section_html)
        self.assertNotIn("Physical Design", section_html)

    def test_auto_heading_resolution_returns_only_changed_heading(self):
        markdown = "# Alpha\nSame text.\n\n# Beta\nUpdated text.\n"
        storage = "<h1>Alpha</h1><p>Same text.</p><h1>Beta</h1><p>Old text.</p>"

        with tempfile.TemporaryDirectory() as temp_dir:
            md_path = pathlib.Path(temp_dir) / "sample.md"
            md_path.write_text(markdown, encoding="utf-8")

            resolved = _resolve_auto_heading_title(str(md_path), storage, split_level=1)

        self.assertEqual(resolved, "Beta")

    def test_auto_heading_resolution_fails_when_multiple_headings_changed(self):
        markdown = "# Alpha\nNew alpha.\n\n# Beta\nNew beta.\n"
        storage = "<h1>Alpha</h1><p>Old alpha.</p><h1>Beta</h1><p>Old beta.</p>"

        with tempfile.TemporaryDirectory() as temp_dir:
            md_path = pathlib.Path(temp_dir) / "sample.md"
            md_path.write_text(markdown, encoding="utf-8")

            with self.assertRaises(SystemExit) as context:
                _resolve_auto_heading_title(str(md_path), storage, split_level=1)

        self.assertIn("multiple split-level sections differ", str(context.exception))

    def test_auto_heading_resolution_lists_multiple_changed_headings_in_order(self):
        markdown = "# Alpha\nNew alpha.\n\n# Beta\nOld beta.\n\n# Gamma\nNew gamma.\n"
        storage = "<h1>Alpha</h1><p>Old alpha.</p><h1>Beta</h1><p>Old beta.</p><h1>Gamma</h1><p>Old gamma.</p>"

        with tempfile.TemporaryDirectory() as temp_dir:
            md_path = pathlib.Path(temp_dir) / "sample.md"
            md_path.write_text(markdown, encoding="utf-8")

            resolved = _resolve_changed_heading_titles(str(md_path), storage, split_level=1)

        self.assertEqual(resolved, ["Alpha", "Gamma"])

    def test_changed_heading_resolution_prefers_last_published_markdown_baseline(self):
        baseline_markdown = "# Alpha\nSame text.\n\n# Beta\nOld beta.\n\n# Gamma\nSame gamma.\n"
        markdown = "# Alpha\nSame text.\n\n# Beta\nNew beta.\n\n# Gamma\nSame gamma.\n"
        noisy_storage = (
            "<h1>Alpha</h1><p>Completely different storage rendering.</p>"
            "<h1>Beta</h1><p>Also different.</p>"
            "<h1>Gamma</h1><p>Still different.</p>"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            md_path = pathlib.Path(temp_dir) / "sample.md"
            md_path.write_text(markdown, encoding="utf-8")

            resolved = _resolve_changed_heading_titles(
                str(md_path),
                noisy_storage,
                split_level=1,
                baseline_markdown=baseline_markdown,
            )

        self.assertEqual(resolved, ["Beta"])

    def test_changed_heading_resolution_detects_body_change_without_heading_change(self):
        baseline_markdown = "# Fabric Setup\nOriginal body text.\n\n# Access Polices\nUnchanged body.\n"
        markdown = "# Fabric Setup\nOriginal body text with local edit.\n\n# Access Polices\nUnchanged body.\n"
        storage = (
            "<h1>Fabric Setup</h1><p>Storage rendering can differ.</p>"
            "<h1>Access Polices</h1><p>Other storage rendering can differ too.</p>"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            md_path = pathlib.Path(temp_dir) / "sample.md"
            md_path.write_text(markdown, encoding="utf-8")

            resolved = _resolve_changed_heading_titles(
                str(md_path),
                storage,
                split_level=1,
                baseline_markdown=baseline_markdown,
            )

        self.assertEqual(resolved, ["Fabric Setup"])

    def test_auto_heading_baseline_reuses_equivalent_copied_markdown_file(self):
        original_markdown = "# Introduction\nSame text.\n\n# Access Polices\nOriginal body.\n"
        copied_markdown = "# Introduction\nSame text.\n\n# Access Polices\nOriginal body.\n"

        with tempfile.TemporaryDirectory() as temp_dir:
            original_md_path = pathlib.Path(temp_dir) / "workspace-copy.md"
            copied_md_path = pathlib.Path(temp_dir) / "downloads-copy.md"
            original_md_path.write_text(original_markdown, encoding="utf-8")
            copied_md_path.write_text(copied_markdown, encoding="utf-8")

            _save_auto_heading_baseline(
                temp_dir,
                "470213898",
                str(original_md_path),
                1,
                {
                    "Introduction": "Same text.",
                    "Access Polices": "Original body.",
                },
            )

            payload = _load_auto_heading_baseline(temp_dir, "470213898", str(copied_md_path), 1)

        self.assertIsNotNone(payload)
        self.assertEqual(payload.get("page_id"), "470213898")


if __name__ == "__main__":
    unittest.main()