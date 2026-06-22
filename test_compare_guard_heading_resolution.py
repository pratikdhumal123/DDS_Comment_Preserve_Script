import unittest
import pathlib
import sys
import tempfile
import os

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "standalone_clone"))

from comment_preserve_publish import _ANCHOR_REGION_AUTO_SENTINEL, _FULL_PAGE_AUTO_SENTINEL, _load_auto_heading_baseline, _resolve_auto_heading_title, _resolve_changed_heading_titles, _save_auto_heading_baseline, _select_auto_heading_target, _select_auto_publish_target
from scdp_compare_guard import _find_anchor_region_bounds, _find_heading_section_bounds


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

    def test_changed_heading_resolution_switches_to_full_page_when_baseline_heading_deleted(self):
        baseline_markdown = "# Introduction\nOld intro.\n\n# Naming Conventions\nSame text.\n"
        markdown = "# Naming Conventions\nSame text.\n"
        storage = "<h1>Introduction</h1><p>Old intro.</p><h1>Naming Conventions</h1><p>Same text.</p>"

        with tempfile.TemporaryDirectory() as temp_dir:
            md_path = pathlib.Path(temp_dir) / "sample.md"
            md_path.write_text(markdown, encoding="utf-8")

            resolved = _resolve_changed_heading_titles(
                str(md_path),
                storage,
                split_level=1,
                baseline_markdown=baseline_markdown,
            )

        self.assertEqual(resolved, [_FULL_PAGE_AUTO_SENTINEL])

    def test_changed_heading_resolution_switches_to_full_page_when_heading_renamed(self):
        baseline_markdown = "# Executive Summary\nOld body.\n\n# Naming Conventions\nSame text.\n"
        markdown = "# Updated Summary\nOld body with local edit.\n\n# Naming Conventions\nSame text.\n"
        storage = "<h1>Executive Summary</h1><p>Old body.</p><h1>Naming Conventions</h1><p>Same text.</p>"

        with tempfile.TemporaryDirectory() as temp_dir:
            md_path = pathlib.Path(temp_dir) / "sample.md"
            md_path.write_text(markdown, encoding="utf-8")

            resolved = _resolve_changed_heading_titles(
                str(md_path),
                storage,
                split_level=1,
                baseline_markdown=baseline_markdown,
            )

        self.assertEqual(resolved, [_FULL_PAGE_AUTO_SENTINEL])

    def test_auto_heading_target_blocks_deleted_or_renamed_full_page_fallback_by_default(self):
        with self.assertRaises(SystemExit) as context:
            _select_auto_heading_target([_FULL_PAGE_AUTO_SENTINEL], allow_full_page_fallback=False)

        self.assertIn("Blocked by default", str(context.exception))

    def test_auto_heading_target_requires_opt_in_for_multiple_changed_sections(self):
        with self.assertRaises(SystemExit) as context:
            _select_auto_heading_target(["Alpha", "Beta"], allow_full_page_fallback=False)

        self.assertIn("--allow-full-page-fallback", str(context.exception))

    def test_auto_heading_target_allows_explicit_full_page_fallback(self):
        resolved = _select_auto_heading_target([_FULL_PAGE_AUTO_SENTINEL], allow_full_page_fallback=True)

        self.assertEqual(resolved, _FULL_PAGE_AUTO_SENTINEL)

    def test_auto_publish_target_uses_anchor_region_for_full_page_sentinel_when_available(self):
        resolved = _select_auto_publish_target(
            [_FULL_PAGE_AUTO_SENTINEL],
            allow_full_page_fallback=False,
            anchor_region_available=True,
        )

        self.assertEqual(resolved, _ANCHOR_REGION_AUTO_SENTINEL)

    def test_auto_publish_target_prefers_single_concrete_heading_even_when_anchor_region_available(self):
        resolved = _select_auto_publish_target(
            ["replaced content > Access Polices"],
            allow_full_page_fallback=False,
            anchor_region_available=True,
        )

        self.assertEqual(resolved, "replaced content > Access Polices")

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

    def test_auto_heading_baseline_accepts_legacy_unqualified_split_level_keys(self):
        markdown = "# Intro\n\n## Alpha\nBody a.\n\n# Other\n\n## Beta\nBody b.\n"

        with tempfile.TemporaryDirectory() as temp_dir:
            md_path = pathlib.Path(temp_dir) / "workspace-copy.md"
            other_md_path = pathlib.Path(temp_dir) / "downloads-copy.md"
            md_path.write_text(markdown, encoding="utf-8")
            other_md_path.write_text(markdown, encoding="utf-8")

            _save_auto_heading_baseline(
                temp_dir,
                "470213899",
                str(md_path),
                2,
                {
                    "Alpha": "Body a.",
                    "Beta": "Body b.",
                },
            )

            payload = _load_auto_heading_baseline(temp_dir, "470213899", str(other_md_path), 2)

        self.assertIsNotNone(payload)
        self.assertEqual(payload.get("page_id"), "470213899")

    def test_auto_heading_baseline_path_match_is_case_insensitive_on_windows_paths(self):
        markdown = "# Intro\n\n## Alpha\nBody a.\n"

        with tempfile.TemporaryDirectory() as temp_dir:
            md_path = pathlib.Path(temp_dir) / "sample.md"
            md_path.write_text(markdown, encoding="utf-8")

            _save_auto_heading_baseline(
                temp_dir,
                "470213900",
                str(md_path).lower(),
                2,
                {
                    "Alpha": "Body a.",
                },
            )

            payload = _load_auto_heading_baseline(temp_dir, "470213900", str(md_path).upper(), 2)

        self.assertIsNotNone(payload)
        self.assertEqual(payload.get("page_id"), "470213900")

    def test_changed_heading_resolution_uses_parent_path_for_duplicate_split_level_titles(self):
        markdown = "# Alpha\n\n## Overview\nNew alpha overview.\n\n# Beta\n\n## Overview\nOld beta overview.\n"
        storage = (
            "<h1>Alpha</h1><h2>Overview</h2><p>Old alpha overview.</p>"
            "<h1>Beta</h1><h2>Overview</h2><p>Old beta overview.</p>"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            md_path = pathlib.Path(temp_dir) / "sample.md"
            md_path.write_text(markdown, encoding="utf-8")

            resolved = _resolve_changed_heading_titles(str(md_path), storage, split_level=2)

        self.assertEqual(resolved, ["Alpha > Overview"])

    def test_changed_heading_resolution_ignores_unresolved_legacy_duplicate_titles(self):
        markdown = (
            "# Introduction\n\n## References\nUpdated refs.\n\n"
            "# Alpha\n\n## Overview\nAlpha body.\n\n"
            "# Beta\n\n## Overview\nBeta body.\n"
        )
        baseline_sections_by_title = {
            "References": "Old refs.",
            "Overview": "Legacy overview body that cannot disambiguate duplicates.",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            md_path = pathlib.Path(temp_dir) / "sample.md"
            md_path.write_text(markdown, encoding="utf-8")

            resolved = _resolve_changed_heading_titles(
                str(md_path),
                "",
                split_level=2,
                baseline_sections_by_title=baseline_sections_by_title,
            )

        self.assertEqual(resolved, ["Introduction > References"])

    def test_find_heading_section_bounds_accepts_path_qualified_heading(self):
        storage = (
            "<h1>Alpha</h1><h2>Overview</h2><p>Alpha body.</p>"
            "<h1>Beta</h1><h2>Overview</h2><p>Beta body.</p>"
        )

        bounds = _find_heading_section_bounds(storage, "Beta > Overview", heading_level=2)

        self.assertIsNotNone(bounds)
        section_html = storage[bounds["heading_start"]:bounds["section_end"]]
        self.assertIn("Beta body.", section_html)
        self.assertNotIn("Alpha body.", section_html)

    def test_find_anchor_region_bounds_returns_body_between_anchor_macros(self):
        storage = (
            '<p><ac:structured-macro ac:name="anchor"><ac:parameter ac:name="">docautomation_start</ac:parameter></ac:structured-macro></p>'
            '<h1>Intro</h1><p>Managed body.</p>'
            '<p><ac:structured-macro ac:name="anchor"><ac:parameter ac:name="">docautomation_end</ac:parameter></ac:structured-macro></p>'
            '<p>Outside.</p>'
        )

        bounds = _find_anchor_region_bounds(storage, "docautomation_start", "docautomation_end")

        self.assertIsNotNone(bounds)
        managed_html = storage[bounds["body_start"]:bounds["section_end"]]
        self.assertIn("Managed body.", managed_html)
        self.assertNotIn("Outside.", managed_html)


if __name__ == "__main__":
    unittest.main()