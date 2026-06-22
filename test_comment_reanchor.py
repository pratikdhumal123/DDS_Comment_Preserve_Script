import json
import os
import tempfile
import unittest
from unittest import mock

from comment_preserve_publish import _enrich_markers_from_history, _inject_inline_markers, _supplement_markers_from_history
from comment_preserve_publish import _reconcile_existing_markers_from_inline_properties
from comment_preserve_publish import _record_comment_ref_heading_ownership, _resolve_owned_comment_refs_for_heading
from comment_preserve_publish import _seed_missing_orphan_markers, _supplement_markers_from_inline_properties
from comment_preserve_publish import _update_page_with_storage


class CommentReanchorTests(unittest.TestCase):
    def test_inline_property_reconcile_updates_existing_marker_to_unique_current_selection(self):
        storage_html = (
            "<h1>ACI Hardening</h1>"
            "<h2>Overview</h2>"
            "<p>Overview text.</p>"
            "<h2>Building Blocks</h2>"
            "<p>A Tenant in ACI is a container that does not map.</p>"
        )
        markers = [
            {
                "ref": "ref-bb-body",
                "anchor_html": "Overview",
                "left_context": "",
                "right_context": "",
                "start": storage_html.index("Overview"),
                "end": storage_html.index("Overview") + len("Overview"),
            }
        ]

        reconciled_markers, reconciled = _reconcile_existing_markers_from_inline_properties(
            storage_html,
            (0, len(storage_html)),
            markers,
            [{"ref": "ref-bb-body", "anchor_html": "A Tenant in ACI is a container that does not map"}],
        )

        self.assertEqual(reconciled, 1)
        self.assertEqual(
            reconciled_markers[0]["anchor_html"],
            "A Tenant in ACI is a container that does not map",
        )

    def test_inline_property_reconcile_skips_ambiguous_selection(self):
        storage_html = (
            "<h1>Section 1</h1><p>Shared text.</p>"
            "<h1>Section 2</h1><p>Shared text.</p>"
        )
        markers = [
            {
                "ref": "ref-shared",
                "anchor_html": "Section 1",
                "left_context": "",
                "right_context": "",
                "start": 0,
                "end": len("Section 1"),
            }
        ]

        reconciled_markers, reconciled = _reconcile_existing_markers_from_inline_properties(
            storage_html,
            (0, len(storage_html)),
            markers,
            [{"ref": "ref-shared", "anchor_html": "Shared text."}],
        )

        self.assertEqual(reconciled, 0)
        self.assertEqual(reconciled_markers[0]["anchor_html"], "Section 1")

    def test_inline_property_reconcile_allows_unique_selection_without_owned_ref(self):
        storage_html = (
            "<h1>ACI Hardening</h1>"
            "<h2>Overview</h2>"
            "<p>Overview text.</p>"
            "<h2>Building Blocks</h2>"
            "<p>A Tenant in ACI is a container that does not map.</p>"
        )
        markers = [
            {
                "ref": "ref-bb-body",
                "anchor_html": "Overview",
                "left_context": "",
                "right_context": "",
                "start": storage_html.index("Overview"),
                "end": storage_html.index("Overview") + len("Overview"),
            }
        ]

        reconciled_markers, reconciled = _reconcile_existing_markers_from_inline_properties(
            storage_html,
            (0, len(storage_html)),
            markers,
            [{"ref": "ref-bb-body", "anchor_html": "A Tenant in ACI is a container that does not map"}],
            owned_refs=set(),
        )

        self.assertEqual(reconciled, 1)
        self.assertEqual(
            reconciled_markers[0]["anchor_html"],
            "A Tenant in ACI is a container that does not map",
        )

    def test_inline_property_reconcile_recovers_blank_marker_by_heading_path_branch(self):
        storage_html = (
            "<h1>Logical Design Updated</h1>"
            "<p>This section is divided in two sub-sections:</p>"
            "<ul>"
            "<li>Building Blocks: The purpose of this sub-section is to briefly describe each one of the Tenant objects.</li>"
            "</ul>"
            "<h1>Other Heading</h1>"
            "<p>This section is divided in two sub-sections:</p>"
            "<ul>"
            "<li>Building Blocks: The purpose of this sub-section is to briefly describe unrelated items.</li>"
            "</ul>"
        )
        markers = [
            {
                "ref": "ref-logical-inline-props",
                "anchor_html": "\u00a0",
                "left_context": "",
                "right_context": "",
                "start": 0,
                "end": 0,
                "heading_path": [
                    {"level": 1, "text": "Logical Design", "normalized_text": "logical design"},
                ],
            }
        ]

        reconciled_markers, reconciled = _reconcile_existing_markers_from_inline_properties(
            storage_html,
            (0, len(storage_html)),
            markers,
            [{"ref": "ref-logical-inline-props", "anchor_html": "sub-section is to briefly describe"}],
        )

        self.assertEqual(reconciled, 1)
        self.assertEqual(
            reconciled_markers[0]["anchor_html"],
            "sub-section is to briefly describe",
        )

    def test_inline_property_supplement_keeps_ambiguous_page_anchor_blocked_without_ownership(self):
        storage_html = (
            "<h1>Access Polices</h1>"
            "<p>Access infrastructure details.</p>"
            "<h1>System Settings</h1>"
            "<p>System infrastructure details.</p>"
        )

        markers, supplemented = _supplement_markers_from_inline_properties(
            storage_html,
            (0, storage_html.index("<h1>System Settings</h1>")),
            [],
            [{"ref": "ref-ambiguous-1", "anchor_html": "infrastructure"}],
        )

        self.assertEqual(supplemented, 0)
        self.assertEqual(markers, [])

    def test_inline_property_supplement_allows_owned_ref_when_anchor_is_unique_in_target_section(self):
        storage_html = (
            "<h1>Access Polices</h1>"
            "<p>Access infrastructure details.</p>"
            "<h1>System Settings</h1>"
            "<p>System infrastructure details.</p>"
        )

        markers, supplemented = _supplement_markers_from_inline_properties(
            storage_html,
            (0, storage_html.index("<h1>System Settings</h1>")),
            [],
            [{"ref": "ref-owned-1", "anchor_html": "infrastructure"}],
            owned_refs={"ref-owned-1"},
        )

        self.assertEqual(supplemented, 1)
        self.assertEqual(len(markers), 1)
        self.assertEqual(markers[0]["ref"], "ref-owned-1")
        self.assertEqual(markers[0]["anchor_html"], "infrastructure")

    def test_missing_orphan_refs_are_seeded_even_when_other_markers_exist(self):
        markers, supplemented = _seed_missing_orphan_markers(
            [
                {
                    "ref": "ref-existing-1",
                    "anchor_html": "Existing text",
                    "left_context": "",
                    "right_context": "",
                    "start": 0,
                    "end": 13,
                }
            ],
            [
                {"ref": "ref-existing-1", "anchor_html": "Existing text"},
                {"ref": "ref-missing-2", "anchor_html": "Deleted text"},
            ],
        )

        self.assertEqual(supplemented, 1)
        self.assertEqual(len(markers), 2)
        self.assertEqual(markers[1]["ref"], "ref-missing-2")
        self.assertEqual(markers[1]["anchor_html"], "\u00a0")
        self.assertTrue(markers[1].get("orphan_seeded"))

    def test_orphan_seeded_marker_reinjects_with_empty_character(self):
        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            "<h2>Surviving Section</h2><p>Current content remains.</p>",
            [
                {
                    "ref": "ref-orphan-seeded-1",
                    "anchor_html": "\u00a0",
                    "left_context": "",
                    "right_context": "",
                    "start": 0,
                    "end": 0,
                    "heading_path": [],
                    "orphan_seeded": True,
                }
            ],
            open_ref_ids=set(),
            section_span=(0, len("<h2>Surviving Section</h2><p>Current content remains.</p>")),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 1)
        self.assertTrue(updated.startswith('<ac:inline-comment-marker ac:ref="ref-orphan-seeded-1">\u00a0</ac:inline-comment-marker>'))
        self.assertNotIn('&#128172;', updated)

    def test_heading_ownership_baseline_records_and_resolves_refs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _record_comment_ref_heading_ownership(
                temp_dir,
                "470213898",
                "Access Polices",
                [
                    {
                        "ref": "ref-owned-1",
                        "heading_path": [
                            {"level": 1, "text": "Access Polices", "normalized_text": "access polices"},
                            {"level": 2, "text": "Domains", "normalized_text": "domains"},
                        ],
                    }
                ],
            )

            self.assertEqual(
                _resolve_owned_comment_refs_for_heading(temp_dir, "470213898", "Access Polices"),
                {"ref-owned-1"},
            )
            self.assertEqual(
                _resolve_owned_comment_refs_for_heading(temp_dir, "470213898", "System Settings"),
                set(),
            )

    def test_history_supplement_creates_missing_marker_from_inline_props(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            history_path = os.path.join(temp_dir, "467033120_20260529T200519Z_compare_guard.json")
            payload = {
                "compare": {
                    "storage": {
                        "chunks": [
                            {
                                "text": (
                                    "<h1>Physical Design</h1>"
                                    "<h2>Hardware Overview</h2>"
                                    "<p>The Cisco Nexus <ac:inline-comment-marker ac:ref=\"84caf64e-666b-4828-b775-fe2b8a25292a\">ACI-Mode</ac:inline-comment-marker> "
                                    "Switches list the supported hardware models.</p>"
                                )
                            }
                        ]
                    }
                }
            }
            with open(history_path, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(payload, handle)

            markers, supplemented = _supplement_markers_from_history(
                temp_dir,
                "467033120",
                "Physical Design",
                (1000, 1400),
                [],
                [{"ref": "84caf64e-666b-4828-b775-fe2b8a25292a", "anchor_html": "ACI-Mode"}],
            )

            self.assertEqual(supplemented, 1)
            self.assertEqual(len(markers), 1)
            self.assertEqual(markers[0]["ref"], "84caf64e-666b-4828-b775-fe2b8a25292a")
            self.assertEqual(markers[0]["anchor_html"], "ACI-Mode")
            self.assertEqual(
                [item["normalized_text"] for item in markers[0]["heading_path"]],
                ["physical design", "hardware overview"],
            )
            self.assertGreaterEqual(markers[0]["start"], 1000)

    @mock.patch("comment_preserve_publish.requests.get")
    @mock.patch("comment_preserve_publish.requests.put")
    def test_update_page_with_storage_fails_closed_on_version_conflict_without_retry(
        self,
        mock_put,
        mock_get,
    ):
        mock_put.return_value = mock.Mock(status_code=409, text="conflict")
        latest_resp = mock.Mock()
        latest_resp.json.return_value = {"version": {"number": 11}}
        latest_resp.raise_for_status.return_value = None
        mock_get.return_value = latest_resp

        result = _update_page_with_storage(
            "https://example.test/conf",
            "12345",
            10,
            "Demo Page",
            "<p>updated</p>",
            auth=None,
            headers={},
            allow_conflict_retry=False,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "version-conflict")
        self.assertEqual(result["http_status"], 409)
        self.assertEqual(result["requested_version"], 10)
        self.assertEqual(result["latest_version"], 11)
        mock_put.assert_called_once()
        mock_get.assert_called_once()

    @mock.patch("comment_preserve_publish.requests.get")
    @mock.patch("comment_preserve_publish.requests.put")
    def test_update_page_with_storage_retries_after_conflict_when_allowed(
        self,
        mock_put,
        mock_get,
    ):
        conflict_resp = mock.Mock(status_code=409, text="conflict")
        success_resp = mock.Mock(status_code=200, text="ok")
        mock_put.side_effect = [conflict_resp, success_resp]

        latest_resp = mock.Mock()
        latest_resp.json.return_value = {"version": {"number": 11}, "title": "Fresh Title"}
        latest_resp.raise_for_status.return_value = None
        mock_get.return_value = latest_resp

        result = _update_page_with_storage(
            "https://example.test/conf",
            "12345",
            10,
            "Demo Page",
            "<p>updated</p>",
            auth=None,
            headers={},
            allow_conflict_retry=True,
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["http_status"], 200)
        self.assertEqual(mock_put.call_count, 2)
        self.assertEqual(mock_get.call_count, 1)

        first_payload = mock_put.call_args_list[0].kwargs["json"]
        second_payload = mock_put.call_args_list[1].kwargs["json"]
        self.assertEqual(first_payload["version"]["number"], 10)
        self.assertEqual(second_payload["version"]["number"], 12)
        self.assertEqual(second_payload["title"], "Fresh Title")

    def test_history_supplement_skips_off_target_heading_candidate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            history_path = os.path.join(temp_dir, "467033120_20260529T200519Z_compare_guard.json")
            payload = {
                "compare": {
                    "storage": {
                        "chunks": [
                            {
                                "text": (
                                    "<h1>Logical Design</h1>"
                                    "<h2>Policy Model</h2>"
                                    "<p><ac:inline-comment-marker ac:ref=\"84caf64e-666b-4828-b775-fe2b8a25292a\">Policy</ac:inline-comment-marker> text.</p>"
                                )
                            }
                        ]
                    }
                }
            }
            with open(history_path, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(payload, handle)

            markers, supplemented = _supplement_markers_from_history(
                temp_dir,
                "467033120",
                "Physical Design",
                (1000, 1400),
                [],
                [{"ref": "84caf64e-666b-4828-b775-fe2b8a25292a", "anchor_html": "Policy"}],
            )

            self.assertEqual(supplemented, 0)
            self.assertEqual(markers, [])

    def test_history_enrichment_prefers_target_heading_candidate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            history_path = os.path.join(temp_dir, "467033120_20260529T200519Z_compare_guard.json")
            payload = {
                "compare": {
                    "storage": {
                        "chunks": [
                            {
                                "text": (
                                    "<h1>Physical Design</h1>"
                                    "<h2>Hardware Overview</h2>"
                                    "<p>The other component is the infrastructure switches connected in a leaf/spine topology. "
                                    "Cisco Nexus 9000 switches in ACI mode are the foundation of the ACI network. "
                                    "The Cisco Nexus <ac:inline-comment-marker ac:ref=\"84caf64e-666b-4828-b775-fe2b8a25292a\">ACI-Mode</ac:inline-comment-marker> "
                                    "Switches list the supported hardware models.</p>"
                                )
                            }
                        ]
                    }
                }
            }
            with open(history_path, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(payload, handle)

            markers = [
                {
                    "ref": "84caf64e-666b-4828-b775-fe2b8a25292a",
                    "anchor_html": "&#128172;",
                    "left_context": "",
                    "right_context": "",
                    "start": 120,
                    "end": 128,
                    "heading_path": [
                        {"level": 2, "text": "Tags", "normalized_text": "tags"},
                    ],
                }
            ]

            enriched, enriched_count = _enrich_markers_from_history(
                temp_dir,
                "467033120",
                "Physical Design",
                markers,
            )

            self.assertEqual(enriched_count, 1)
            self.assertEqual(enriched[0]["anchor_html"], "ACI-Mode")
            self.assertEqual(
                [item["normalized_text"] for item in enriched[0]["heading_path"]],
                ["physical design", "hardware overview"],
            )

    def test_history_enrichment_does_not_override_visible_current_anchor_with_stale_text(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            history_path = os.path.join(temp_dir, "467033120_20260529T200519Z_compare_guard.json")
            payload = {
                "compare": {
                    "storage": {
                        "chunks": [
                            {
                                "text": (
                                    "<h1>Physical Design</h1>"
                                    "<p><ac:inline-comment-marker ac:ref=\"84caf64e-666b-4828-b775-fe2b8a25292a\">Stale Anchor</ac:inline-comment-marker> text.</p>"
                                )
                            }
                        ]
                    }
                }
            }
            with open(history_path, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(payload, handle)

            markers = [
                {
                    "ref": "84caf64e-666b-4828-b775-fe2b8a25292a",
                    "anchor_html": "Live Anchor",
                    "left_context": "",
                    "right_context": "",
                    "start": 120,
                    "end": 131,
                    "heading_path": [
                        {"level": 1, "text": "Physical Design", "normalized_text": "physical design"},
                    ],
                }
            ]

            enriched, enriched_count = _enrich_markers_from_history(
                temp_dir,
                "467033120",
                "Physical Design",
                markers,
            )

            self.assertEqual(enriched_count, 0)
            self.assertEqual(enriched[0]["anchor_html"], "Live Anchor")

    def test_deleted_content_prefers_deepest_heading_path_when_context_is_too_weak(self):
        new_storage = (
            "<h2>Hardware Overview</h2>"
            "<p>Overview remains.</p>"
            "<h2>Physical Topology</h2>"
            "<p>Topology intro remains.</p>"
            "<h3>Fabric Connectivity</h3>"
            "<p>Fabric connectivity remains.</p>"
            "<h3>External Connectivity</h3>"
            "<p>External overview remains.</p>"
        )

        markers = [
            {
                "ref": "ref-external-delete-1",
                "anchor_html": "Deleted external sentence that no longer exists.",
                "left_context": "short context without heading name",
                "right_context": "",
                "start": 9999,
                "end": 10040,
                "heading_path": [
                    {"level": 2, "text": "Physical Topology", "normalized_text": "physical topology"},
                    {"level": 3, "text": "External Connectivity", "normalized_text": "external connectivity"},
                ],
            }
        ]

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            markers,
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertIn(
            '<h3><ac:inline-comment-marker ac:ref="ref-external-delete-1">External Connectivity</ac:inline-comment-marker></h3>',
            updated,
        )
        self.assertNotIn(
            '<h2><ac:inline-comment-marker ac:ref="ref-external-delete-1">Physical Topology</ac:inline-comment-marker></h2>',
            updated,
        )

    def test_exact_anchor_does_not_wrap_inside_link_href(self):
        new_storage = (
            '<p>More info can be found in the '
            '<a href="https://example.com/path/design-guide">Design Guide</a>.</p>'
            '<h3>External Connectivity</h3>'
        )

        markers = [
            {
                'ref': 'ref-link-safe-1',
                'anchor_html': 'design',
                'left_context': 'href="https://example.com/path/',
                'right_context': '-guide">Design Guide</a>.</p>',
                'start': 35,
                'end': 41,
                'heading_path': [
                    {'level': 3, 'text': 'External Connectivity', 'normalized_text': 'external connectivity'},
                ],
            }
        ]

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            markers,
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertIn('href="https://example.com/path/design-guide"', updated)
        self.assertIn(
            '<h3><ac:inline-comment-marker ac:ref="ref-link-safe-1">External Connectivity</ac:inline-comment-marker></h3>',
            updated,
        )
        self.assertNotIn('href="https://example.com/path/<ac:inline-comment-marker', updated)

    def test_deleted_content_anchors_to_nearest_nested_heading(self):
        old_storage = (
            "<h1>Introduction</h1>"
            "<h2>Testcase</h2>"
            "<p>Intro text before deleted content.</p>"
            "<h3>Margine</h3>"
            "<p>Deleted sentence lives here.</p>"
            "<h3>Sibling Heading</h3>"
            "<p>Sibling content remains.</p>"
        )
        new_storage = (
            "<h1>Introduction</h1>"
            "<h2>Testcase</h2>"
            "<p>Intro text before deleted content.</p>"
            "<h3>Margine</h3>"
            "<h3>Sibling Heading</h3>"
            "<p>Sibling content remains.</p>"
        )

        anchor = "Deleted sentence lives here."
        anchor_start = old_storage.index(anchor)
        markers = [
            {
                "ref": "ref-deleted-1",
                "anchor_html": anchor,
                "left_context": old_storage[max(0, anchor_start - 80):anchor_start],
                "right_context": old_storage[anchor_start + len(anchor):anchor_start + len(anchor) + 80],
                "start": anchor_start,
                "end": anchor_start + len(anchor),
            }
        ]

        updated, reanchored, skipped, _deleted_icons = _inject_inline_markers(
            new_storage,
            markers,
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertIn(
            '<h3><ac:inline-comment-marker ac:ref="ref-deleted-1">Margine</ac:inline-comment-marker></h3>',
            updated,
        )
        self.assertNotIn(
            '<h1><ac:inline-comment-marker ac:ref="ref-deleted-1">Introduction</ac:inline-comment-marker></h1>',
            updated,
        )
        self.assertNotIn(
            '<h2><ac:inline-comment-marker ac:ref="ref-deleted-1">Testcase</ac:inline-comment-marker></h2>',
            updated,
        )

    def test_deleted_parent_heading_keeps_child_content_comment_in_surviving_child_section(self):
        old_storage = (
            '<h1>Physical Design</h1>'
            '<h2>Hardware Overview</h2>'
            '<p>Alpha old beta.</p>'
            '<h1>Operations</h1>'
            '<p>Alpha old beta.</p>'
        )
        new_storage = (
            '<h2>Hardware Overview</h2>'
            '<p>Alpha new beta.</p>'
            '<h1>Operations</h1>'
            '<p>Alpha old beta.</p>'
        )

        anchor = 'old'
        anchor_start = old_storage.index('<p>Alpha old beta.</p>') + len('<p>Alpha ')
        marker = {
            'ref': 'ref-parent-deleted-word-1',
            'anchor_html': anchor,
            'left_context': old_storage[max(0, anchor_start - 80):anchor_start],
            'right_context': old_storage[anchor_start + len(anchor):anchor_start + len(anchor) + 80],
            'start': anchor_start,
            'end': anchor_start + len(anchor),
            'heading_path': [
                {'level': 1, 'text': 'Physical Design', 'normalized_text': 'physical design'},
                {'level': 2, 'text': 'Hardware Overview', 'normalized_text': 'hardware overview'},
            ],
        }

        section_end = new_storage.index('<h1>Operations</h1>')
        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            [marker],
            open_ref_ids=set(),
            section_span=(0, section_end),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertIn(
            '<h2>Hardware Overview</h2><p>Alpha <ac:inline-comment-marker ac:ref="ref-parent-deleted-word-1">new</ac:inline-comment-marker> beta.</p>',
            updated,
        )
        self.assertNotIn(
            '<h1>Operations</h1><p>Alpha <ac:inline-comment-marker ac:ref="ref-parent-deleted-word-1">old</ac:inline-comment-marker> beta.</p>',
            updated,
        )

    def test_deleted_h3_heading_falls_back_to_parent_h2_in_same_branch(self):
        old_storage = (
            '<h1>Physical Design</h1>'
            '<h2>Physical Topology</h2>'
            '<h3>External Connectivity</h3>'
            '<p>Deleted sentence lives here.</p>'
            '<h2>Hardware Overview</h2>'
            '<p>Other branch remains.</p>'
        )
        new_storage = (
            '<h1>Physical Design</h1>'
            '<h2>Physical Topology</h2>'
            '<p>Topology summary remains.</p>'
            '<h2>Hardware Overview</h2>'
            '<p>Other branch remains.</p>'
        )

        anchor = 'Deleted sentence lives here.'
        anchor_start = old_storage.index(anchor)
        marker = {
            'ref': 'ref-h3-deleted-1',
            'anchor_html': anchor,
            'left_context': old_storage[max(0, anchor_start - 80):anchor_start],
            'right_context': old_storage[anchor_start + len(anchor):anchor_start + len(anchor) + 80],
            'start': anchor_start,
            'end': anchor_start + len(anchor),
            'heading_path': [
                {'level': 1, 'text': 'Physical Design', 'normalized_text': 'physical design'},
                {'level': 2, 'text': 'Physical Topology', 'normalized_text': 'physical topology'},
                {'level': 3, 'text': 'External Connectivity', 'normalized_text': 'external connectivity'},
            ],
        }

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            [marker],
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertIn(
            '<h2><ac:inline-comment-marker ac:ref="ref-h3-deleted-1">Physical Topology</ac:inline-comment-marker></h2>',
            updated,
        )
        self.assertNotIn(
            '<h2><ac:inline-comment-marker ac:ref="ref-h3-deleted-1">Hardware Overview</ac:inline-comment-marker></h2>',
            updated,
        )

    def test_deleted_h1_heading_comment_does_not_jump_to_next_h1(self):
        new_storage = (
            '<h1>Introduction</h1>'
            '<p>Intro remains.</p>'
            '<h1>Naming Conventions</h1>'
            '<p>Naming section remains.</p>'
        )

        marker = {
            'ref': 'ref-h1-deleted-1',
            'anchor_html': 'Executive Summary',
            'left_context': '<h1>',
            'right_context': '</h1><h2>Requirements Mapping</h2>',
            'start': 120,
            'end': 137,
            'heading_path': [
                {'level': 1, 'text': 'Executive Summary', 'normalized_text': 'executive summary'},
            ],
        }

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            [marker],
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertTrue(
            updated.startswith('<ac:inline-comment-marker ac:ref="ref-h1-deleted-1">\u00a0</ac:inline-comment-marker>')
        )
        self.assertNotIn(
            '<h1><ac:inline-comment-marker ac:ref="ref-h1-deleted-1">Naming Conventions</ac:inline-comment-marker></h1>',
            updated,
        )

    def test_off_section_marker_does_not_block_deleted_heading_forward(self):
        new_storage = (
            '<h1>Elsewhere</h1>'
            '<p><ac:inline-comment-marker ac:ref="ref-off-section-1">Elsewhere text</ac:inline-comment-marker></p>'
            '<h1>Physical Design</h1>'
            '<h2>Hardware Overview</h2>'
            '<p>Current section content remains.</p>'
        )

        marker = {
            "ref": "ref-off-section-1",
            "anchor_html": "Deleted sentence that is gone.",
            "left_context": "Physical Design Hardware Overview deleted paragraph",
            "right_context": "",
            "start": 999,
            "end": 1026,
            "heading_path": [
                {"level": 1, "text": "Physical Design", "normalized_text": "physical design"},
                {"level": 2, "text": "Hardware Overview", "normalized_text": "hardware overview"},
            ],
        }

        section_start = new_storage.index('<h1>Physical Design</h1>')
        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            [marker],
            open_ref_ids=set(),
            section_span=(section_start, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertIn(
            '<h2><ac:inline-comment-marker ac:ref="ref-off-section-1">Hardware Overview</ac:inline-comment-marker></h2>',
            updated,
        )

    def test_replaced_content_does_not_jump_outside_active_section(self):
        old_storage = (
            '<h1>Introduction</h1>'
            '<p>Stable paragraph outside the target section.</p>'
            '<h1>Physical Design</h1>'
            '<h2>Hardware Overview</h2>'
            '<p>Alpha old beta.</p>'
            '<h1>Operations</h1>'
            '<p>Alpha old beta.</p>'
        )
        new_storage = (
            '<h1>Introduction</h1>'
            '<p>Stable paragraph outside the target section.</p>'
            '<h1>Physical Design</h1>'
            '<h2>Hardware Overview</h2>'
            '<p>Alpha new beta.</p>'
            '<h1>Operations</h1>'
            '<p>Alpha old beta.</p>'
        )

        anchor = 'old'
        anchor_start = old_storage.index('<p>Alpha old beta.</p>') + '<p>Alpha '.__len__()
        marker = {
            'ref': 'ref-section-local-word-1',
            'anchor_html': anchor,
            'left_context': old_storage[max(0, anchor_start - 80):anchor_start],
            'right_context': old_storage[anchor_start + len(anchor):anchor_start + len(anchor) + 80],
            'start': anchor_start,
            'end': anchor_start + len(anchor),
            'heading_path': [
                {'level': 1, 'text': 'Physical Design', 'normalized_text': 'physical design'},
                {'level': 2, 'text': 'Hardware Overview', 'normalized_text': 'hardware overview'},
            ],
        }

        section_start = new_storage.index('<h1>Physical Design</h1>')
        section_end = new_storage.index('<h1>Operations</h1>')
        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            [marker],
            open_ref_ids=set(),
            section_span=(section_start, section_end),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertIn(
            '<h2>Hardware Overview</h2><p>Alpha <ac:inline-comment-marker ac:ref="ref-section-local-word-1">new</ac:inline-comment-marker> beta.</p>',
            updated,
        )
        self.assertNotIn(
            '<h1>Operations</h1><p>Alpha <ac:inline-comment-marker ac:ref="ref-section-local-word-1">old</ac:inline-comment-marker> beta.</p>',
            updated,
        )

    def test_deleted_content_does_not_anchor_to_heading_outside_active_section(self):
        old_storage = (
            '<h1>Introduction</h1>'
            '<h2>Hardware Overview</h2>'
            '<p>Introduction hardware text.</p>'
            '<h1>Physical Design</h1>'
            '<h2>Hardware Overview</h2>'
            '<p>Deleted sentence lives here.</p>'
            '<h1>Operations</h1>'
            '<h2>Hardware Overview</h2>'
            '<p>Operations content remains.</p>'
        )
        new_storage = (
            '<h1>Introduction</h1>'
            '<h2>Hardware Overview</h2>'
            '<p>Introduction hardware text.</p>'
            '<h1>Physical Design</h1>'
            '<h2>Hardware Overview</h2>'
            '<h1>Operations</h1>'
            '<h2>Hardware Overview</h2>'
            '<p>Operations content remains.</p>'
        )

        anchor = 'Deleted sentence lives here.'
        anchor_start = old_storage.index(anchor)
        marker = {
            'ref': 'ref-section-local-delete-1',
            'anchor_html': anchor,
            'left_context': old_storage[max(0, anchor_start - 80):anchor_start],
            'right_context': old_storage[anchor_start + len(anchor):anchor_start + len(anchor) + 80],
            'start': anchor_start,
            'end': anchor_start + len(anchor),
            'heading_path': [
                {'level': 1, 'text': 'Physical Design', 'normalized_text': 'physical design'},
                {'level': 2, 'text': 'Hardware Overview', 'normalized_text': 'hardware overview'},
            ],
        }

        section_start = new_storage.index('<h1>Physical Design</h1>')
        section_end = new_storage.index('<h1>Operations</h1>')
        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            [marker],
            open_ref_ids=set(),
            section_span=(section_start, section_end),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertIn(
            '<h1>Physical Design</h1><h2><ac:inline-comment-marker ac:ref="ref-section-local-delete-1">Hardware Overview</ac:inline-comment-marker></h2>',
            updated,
        )
        self.assertNotIn(
            '<h1>Introduction</h1><h2><ac:inline-comment-marker ac:ref="ref-section-local-delete-1">Hardware Overview</ac:inline-comment-marker></h2>',
            updated,
        )
        self.assertNotIn(
            '<h1>Operations</h1><h2><ac:inline-comment-marker ac:ref="ref-section-local-delete-1">Hardware Overview</ac:inline-comment-marker></h2>',
            updated,
        )

    def test_deleted_single_word_does_not_rebind_to_unrelated_surviving_word(self):
        old_storage = (
            '<h1>Physical Design</h1>'
            '<h2>Hardware Overview</h2>'
            '<p>The other component is the infrastructure switches connected in a leaf/spine topology.</p>'
            '<p>Cisco Application Policy remains available.</p>'
        )
        new_storage = (
            '<h1>Physical Design</h1>'
            '<h2>Hardware Overview</h2>'
            '<p>Cisco Application Policy remains available.</p>'
        )

        anchor = 'infrastructure'
        anchor_start = old_storage.index(anchor)
        marker = {
            'ref': 'ref-deleted-single-word-1',
            'anchor_html': anchor,
            'left_context': old_storage[max(0, anchor_start - 80):anchor_start],
            'right_context': old_storage[anchor_start + len(anchor):anchor_start + len(anchor) + 80],
            'start': anchor_start,
            'end': anchor_start + len(anchor),
            'heading_path': [
                {'level': 1, 'text': 'Physical Design', 'normalized_text': 'physical design'},
                {'level': 2, 'text': 'Hardware Overview', 'normalized_text': 'hardware overview'},
            ],
        }

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            [marker],
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertIn(
            '<h2><ac:inline-comment-marker ac:ref="ref-deleted-single-word-1">Hardware Overview</ac:inline-comment-marker></h2>',
            updated,
        )
        self.assertNotIn(
            '<ac:inline-comment-marker ac:ref="ref-deleted-single-word-1">Application</ac:inline-comment-marker>',
            updated,
        )

    def test_exact_text_in_different_heading_with_weak_context_prefers_original_heading_path(self):
        new_storage = (
            '<h1>Physical Design</h1>'
            '<h2>Hardware Overview</h2>'
            '<p>Hardware section intro.</p>'
            '<h2>Physical Topology</h2>'
            '<p>The topology references Infrastructure Controller (APIC) identifiers for documentation only.</p>'
        )

        anchor = 'Infrastructure Controller (APIC)'
        marker = {
            'ref': 'ref-original-heading-1',
            'anchor_html': anchor,
            'left_context': 'managed centrally by the Cisco Application Policy ',
            'right_context': ' to automate fabric discovery and configuration.',
            'start': 200,
            'end': 200 + len(anchor),
            'heading_path': [
                {'level': 1, 'text': 'Physical Design', 'normalized_text': 'physical design'},
                {'level': 2, 'text': 'Hardware Overview', 'normalized_text': 'hardware overview'},
            ],
        }

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            [marker],
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertIn(
            '<h2><ac:inline-comment-marker ac:ref="ref-original-heading-1">Hardware Overview</ac:inline-comment-marker></h2>',
            updated,
        )
        self.assertNotIn(
            '<ac:inline-comment-marker ac:ref="ref-original-heading-1">Infrastructure Controller (APIC)</ac:inline-comment-marker>',
            updated,
        )

    def test_exact_text_in_different_heading_with_strong_context_follows_moved_content(self):
        new_storage = (
            '<h1>Physical Design</h1>'
            '<h2>Hardware Overview</h2>'
            '<p>This design is managed centrally by the Cisco Application Policy Infrastructure Controller (APIC) to automate fabric discovery and configuration.</p>'
            '<h2>Physical Topology</h2>'
            '<p>Topology summary.</p>'
        )

        anchor = 'Infrastructure Controller (APIC)'
        marker = {
            'ref': 'ref-moved-heading-1',
            'anchor_html': anchor,
            'left_context': 'managed centrally by the Cisco Application Policy ',
            'right_context': ' to automate fabric discovery and configuration.',
            'start': 260,
            'end': 260 + len(anchor),
            'heading_path': [
                {'level': 1, 'text': 'Physical Design', 'normalized_text': 'physical design'},
                {'level': 2, 'text': 'Physical Topology', 'normalized_text': 'physical topology'},
            ],
        }

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            [marker],
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertIn(
            '<ac:inline-comment-marker ac:ref="ref-moved-heading-1">Infrastructure Controller (APIC)</ac:inline-comment-marker>',
            updated,
        )
        self.assertNotIn(
            '<h2><ac:inline-comment-marker ac:ref="ref-moved-heading-1">Physical Topology</ac:inline-comment-marker></h2>',
            updated,
        )

    def test_multiple_deleted_comments_share_same_nearest_heading(self):
        old_storage = (
            "<h2>Testcase</h2>"
            "<h3>Margine</h3>"
            "<p>Deleted sentence lives here.</p>"
            "<p>Another deleted sentence lives here.</p>"
            "<h3>Sibling Heading</h3>"
            "<p>Sibling content remains.</p>"
        )
        new_storage = (
            "<h2>Testcase</h2>"
            "<h3>Margine</h3>"
            "<h3>Sibling Heading</h3>"
            "<p>Sibling content remains.</p>"
        )

        anchors = ["Deleted sentence lives here.", "Another deleted sentence lives here."]
        markers = []
        for index, anchor in enumerate(anchors, start=1):
            anchor_start = old_storage.index(anchor)
            markers.append(
                {
                    "ref": f"ref-deleted-{index}",
                    "anchor_html": anchor,
                    "left_context": old_storage[max(0, anchor_start - 80):anchor_start],
                    "right_context": old_storage[anchor_start + len(anchor):anchor_start + len(anchor) + 80],
                    "start": anchor_start,
                    "end": anchor_start + len(anchor),
                }
            )

        updated, reanchored, skipped, _deleted_icons = _inject_inline_markers(
            new_storage,
            markers,
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 2)
        self.assertEqual(skipped, 0)
        self.assertIn('<h3><ac:inline-comment-marker ac:ref="ref-deleted-2"><ac:inline-comment-marker ac:ref="ref-deleted-1">Margine</ac:inline-comment-marker></ac:inline-comment-marker></h3>', updated)
        self.assertNotIn('ref="ref-deleted-1">Sibling Heading', updated)
        self.assertNotIn('ref="ref-deleted-2">Sibling Heading', updated)

    def test_previous_deleted_heading_comments_survive_next_overwrite(self):
        next_storage = (
            "<h2>Testcase</h2>"
            "<h3>Margine</h3>"
            "<p>Keep content.</p>"
        )
        old_markers = [
            {
                "ref": "ref-old-1",
                "anchor_html": '<ac:inline-comment-marker ac:ref="ref-old-2">Margine</ac:inline-comment-marker>',
                "left_context": "<h2>Testcase</h2><h3>",
                "right_context": "</h3><p>Keep content.</p>",
                "start": len("<h2>Testcase</h2><h3>"),
                "end": len("<h2>Testcase</h2><h3>Margine"),
            },
            {
                "ref": "ref-old-2",
                "anchor_html": "Margine",
                "left_context": "<h2>Testcase</h2><h3>",
                "right_context": "</h3><p>Keep content.</p>",
                "start": len("<h2>Testcase</h2><h3>"),
                "end": len("<h2>Testcase</h2><h3>Margine"),
            },
            {
                "ref": "ref-new-3",
                "anchor_html": "Freshly deleted sentence.",
                "left_context": "<h3>Margine</h3><p>Keep content.</p><p>",
                "right_context": "</p>",
                "start": len("<h2>Testcase</h2><h3>Margine</h3><p>Keep content.</p><p>"),
                "end": len("<h2>Testcase</h2><h3>Margine</h3><p>Keep content.</p><p>Freshly deleted sentence."),
            },
        ]

        updated, reanchored, skipped, _deleted_icons = _inject_inline_markers(
            next_storage,
            old_markers,
            open_ref_ids=set(),
            section_span=(0, len(next_storage)),
        )

        self.assertEqual(reanchored, 3)
        self.assertEqual(skipped, 0)
        self.assertIn('ref="ref-old-1"', updated)
        self.assertIn('ref="ref-old-2"', updated)
        self.assertIn('ref="ref-new-3"', updated)
        self.assertIn('Margine', updated)
        self.assertIn('<h3><ac:inline-comment-marker ac:ref="ref-new-3"><ac:inline-comment-marker ac:ref="ref-old-1"><ac:inline-comment-marker ac:ref="ref-old-2">Margine</ac:inline-comment-marker></ac:inline-comment-marker></ac:inline-comment-marker></h3>', updated)
        self.assertNotIn('>Keep content.</ac:inline-comment-marker>', updated)

    def test_three_comments_on_one_deleted_line_stay_separate_on_heading(self):
        old_storage = (
            "<h2>References</h2>"
            "<p>The following table contains other source material that has been referenced in the creation of this document.</p>"
            "<p>Next paragraph.</p>"
        )
        new_storage = (
            "<h2>References</h2>"
            "<p>Next paragraph.</p>"
        )

        anchor = "The following table contains other source material that has been referenced in the creation of this document."
        anchor_start = old_storage.index(anchor)
        markers = []
        for index in range(1, 4):
            markers.append(
                {
                    "ref": f"ref-del-{index}",
                    "anchor_html": anchor,
                    "left_context": old_storage[max(0, anchor_start - 80):anchor_start],
                    "right_context": old_storage[anchor_start + len(anchor):anchor_start + len(anchor) + 80],
                    "start": anchor_start,
                    "end": anchor_start + len(anchor),
                }
            )

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            markers,
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 3)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertIn('<h2><ac:inline-comment-marker ac:ref="ref-del-3"><ac:inline-comment-marker ac:ref="ref-del-2"><ac:inline-comment-marker ac:ref="ref-del-1">References</ac:inline-comment-marker></ac:inline-comment-marker></ac:inline-comment-marker></h2>', updated)
        self.assertNotIn('>Next paragraph.</ac:inline-comment-marker>', updated)

    def test_deleted_duplicate_text_does_not_jump_to_other_heading(self):
        repeated_anchor = "Shared duplicate sentence that still exists later."
        spacer = "A" * 240
        old_storage = (
            "<h2>References</h2>"
            f"<p>{repeated_anchor}</p>"
            f"<p>{spacer}</p>"
            "<h3>Other Heading</h3>"
            f"<p>{repeated_anchor}</p>"
        )
        new_storage = (
            "<h2>References</h2>"
            f"<p>{spacer}</p>"
            "<h3>Other Heading</h3>"
            f"<p>{repeated_anchor}</p>"
        )

        anchor_start = old_storage.index(repeated_anchor)
        markers = [
            {
                "ref": "ref-duplicate-delete-1",
                "anchor_html": repeated_anchor,
                "left_context": old_storage[max(0, anchor_start - 100):anchor_start],
                "right_context": old_storage[anchor_start + len(repeated_anchor):anchor_start + len(repeated_anchor) + 100],
                "start": anchor_start,
                "end": anchor_start + len(repeated_anchor),
            }
        ]

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            markers,
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertIn(
            '<h2><ac:inline-comment-marker ac:ref="ref-duplicate-delete-1">References</ac:inline-comment-marker></h2>',
            updated,
        )
        self.assertNotIn(
            '<h3>Other Heading</h3><p><ac:inline-comment-marker ac:ref="ref-duplicate-delete-1">',
            updated,
        )

    def test_heading_rename_preserves_heading_and_internal_comment_context(self):
        old_storage = (
            "<h2>Policy Naming Conventions</h2>"
            "<p>Last Update: 17 June 2026, 10:01 AM</p>"
            "<p>comment 11</p>"
        )
        new_storage = (
            "<h2>Policy Naming Standard</h2>"
            "<p>Last Update: 17 June 2026, 10:01 AM</p>"
            "<p>comment 11 updated</p>"
        )

        heading_anchor = "Policy Naming Conventions"
        heading_start = old_storage.index(heading_anchor)
        markers = [
            {
                "ref": "ref-rename-heading",
                "anchor_html": heading_anchor,
                "left_context": old_storage[max(0, heading_start - 80):heading_start],
                "right_context": old_storage[heading_start + len(heading_anchor):heading_start + len(heading_anchor) + 80],
                "start": heading_start,
                "end": heading_start + len(heading_anchor),
            },
            {
                "ref": "ref-rename-body",
                "anchor_html": "comment 11",
                "left_context": "Last Update: 17 June 2026, 10:01 AM</p><p>",
                "right_context": "</p>",
                "start": old_storage.index("comment 11"),
                "end": old_storage.index("comment 11") + len("comment 11"),
            },
        ]

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            markers,
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 2)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertIn('ref="ref-rename-heading"', updated)
        self.assertIn('ref="ref-rename-body"', updated)
        self.assertIn(
            '<h2><ac:inline-comment-marker ac:ref="ref-rename-heading">Policy Naming Standard</ac:inline-comment-marker></h2>',
            updated,
        )
        self.assertIn(
            '<p><ac:inline-comment-marker ac:ref="ref-rename-body">comment 11</ac:inline-comment-marker> updated</p>',
            updated,
        )

    def test_nested_heading_rename_keeps_heading_comment_on_renamed_h3_in_same_branch(self):
        old_storage = (
            '<h1>Physical Design</h1>'
            '<h2>Physical Topology</h2>'
            '<h3>External Connectivity</h3>'
            '<p>Edge uplinks connect leaf nodes.</p>'
            '<h3>Management Plane</h3>'
            '<p>Management remains separate.</p>'
        )
        new_storage = (
            '<h1>Physical Design</h1>'
            '<h2>Physical Topology</h2>'
            '<h3>External Network Connectivity</h3>'
            '<p>Edge uplinks connect leaf nodes with updated routing.</p>'
            '<h3>Management Plane</h3>'
            '<p>Management remains separate.</p>'
        )

        heading_anchor = 'External Connectivity'
        heading_start = old_storage.index(heading_anchor)
        markers = [
            {
                'ref': 'ref-rename-nested-heading',
                'anchor_html': heading_anchor,
                'left_context': old_storage[max(0, heading_start - 80):heading_start],
                'right_context': old_storage[heading_start + len(heading_anchor):heading_start + len(heading_anchor) + 80],
                'start': heading_start,
                'end': heading_start + len(heading_anchor),
                'heading_path': [
                    {'level': 1, 'text': 'Physical Design', 'normalized_text': 'physical design'},
                    {'level': 2, 'text': 'Physical Topology', 'normalized_text': 'physical topology'},
                    {'level': 3, 'text': 'External Connectivity', 'normalized_text': 'external connectivity'},
                ],
            },
        ]

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            markers,
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertIn(
            '<h3><ac:inline-comment-marker ac:ref="ref-rename-nested-heading">External Network Connectivity</ac:inline-comment-marker></h3>',
            updated,
        )
        self.assertNotIn(
            '<h3><ac:inline-comment-marker ac:ref="ref-rename-nested-heading">Management Plane</ac:inline-comment-marker></h3>',
            updated,
        )

    def test_deleted_main_heading_places_comment_below_surviving_upper_heading(self):
        old_storage = (
            "<h1>Intro</h1>"
            "<h2>Removed Heading</h2>"
            "<p>Deleted sentence.</p>"
            "<h2>Keep</h2>"
            "<p>Body.</p>"
        )
        new_storage = (
            "<h1>Intro</h1>"
            "<h2>Keep</h2>"
            "<p>Body.</p>"
        )

        anchor = "Deleted sentence."
        anchor_start = old_storage.index(anchor)
        markers = [
            {
                "ref": "ref-main-heading-delete-1",
                "anchor_html": anchor,
                "left_context": old_storage[max(0, anchor_start - 80):anchor_start],
                "right_context": old_storage[anchor_start + len(anchor):anchor_start + len(anchor) + 80],
                "start": anchor_start,
                "end": anchor_start + len(anchor),
                "heading_path": [
                    {"level": 1, "text": "Intro", "normalized_text": "intro"},
                    {"level": 2, "text": "Removed Heading", "normalized_text": "removed heading"},
                ],
            }
        ]

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            markers,
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertEqual(
            updated,
            '<h1>Intro</h1><ac:inline-comment-marker ac:ref="ref-main-heading-delete-1">\u00a0</ac:inline-comment-marker><h2>Keep</h2><p>Body.</p>',
        )

    def test_deleted_heading_path_pins_comment_to_top_of_scope_with_blank_icon(self):
        new_storage = (
            "<h2>Surviving Section</h2>"
            "<p>Current content remains.</p>"
        )
        markers = [
            {
                "ref": "ref-deleted-heading-top",
                "anchor_html": "Deleted heading text.",
                "left_context": "<h2>Removed Section</h2><p>",
                "right_context": "</p>",
                "start": 0,
                "end": len("Deleted heading text."),
                "heading_path": [
                    {"level": 2, "text": "Removed Section", "normalized_text": "removed section"},
                ],
            }
        ]

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            markers,
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertTrue(updated.startswith('<ac:inline-comment-marker ac:ref="ref-deleted-heading-top">'))
        self.assertIn('\u00a0', updated)

    def test_deleted_heading_fallback_keeps_blank_target_when_heading_has_no_visible_text(self):
        new_storage = (
            "<h2>\u00a0</h2>"
            "<p>Current content remains.</p>"
        )
        markers = [
            {
                "ref": "ref-deleted-heading-empty-target",
                "anchor_html": "Deleted heading text.",
                "left_context": "<h2>Removed Section</h2><p>",
                "right_context": "</p>",
                "start": 0,
                "end": len("Deleted heading text."),
            }
        ]

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            markers,
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertIn(
            '<h2><ac:inline-comment-marker ac:ref="ref-deleted-heading-empty-target">\u00a0</ac:inline-comment-marker></h2>',
            updated,
        )

    def test_deleted_top_level_heading_pins_orphan_comment_to_top_of_document(self):
        old_storage = (
            "<h1>Logical Design</h1>"
            "<p>Deleted body text.</p>"
            "<h1>ACI Hardening</h1>"
            "<p>Surviving content.</p>"
        )
        new_storage = (
            "<h1>ACI Hardening</h1>"
            "<p>Surviving content.</p>"
        )
        anchor = "Deleted body text."
        anchor_start = old_storage.index(anchor)
        markers = [
            {
                "ref": "ref-deleted-h1-top",
                "anchor_html": anchor,
                "left_context": old_storage[max(0, anchor_start - 80):anchor_start],
                "right_context": old_storage[anchor_start + len(anchor):anchor_start + len(anchor) + 80],
                "start": anchor_start,
                "end": anchor_start + len(anchor),
                "heading_path": [
                    {"level": 1, "text": "Logical Design", "normalized_text": "logical design"},
                ],
            }
        ]

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            markers,
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertTrue(updated.startswith('<ac:inline-comment-marker ac:ref="ref-deleted-h1-top">\u00a0</ac:inline-comment-marker><h1>ACI Hardening</h1>'))

    def test_deleted_top_level_heading_comment_pins_orphan_to_top_when_context_mismatch(self):
        old_storage = (
            "<h1>Logical Design</h1>"
            "<p>Deleted branch context.</p>"
            "<h1>ACI Hardening</h1>"
            "<p>Surviving content.</p>"
        )
        new_storage = (
            "<h1>ACI Hardening</h1>"
            "<p>Completely different context.</p>"
        )

        heading_anchor = "Logical Design"
        heading_start = old_storage.index(heading_anchor)
        markers = [
            {
                "ref": "ref-deleted-h1-heading-top",
                "anchor_html": heading_anchor,
                "left_context": old_storage[max(0, heading_start - 80):heading_start],
                "right_context": old_storage[heading_start + len(heading_anchor):heading_start + len(heading_anchor) + 80],
                "start": heading_start,
                "end": heading_start + len(heading_anchor),
                "heading_path": [
                    {"level": 1, "text": "Logical Design", "normalized_text": "logical design"},
                ],
            }
        ]

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            markers,
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertTrue(updated.startswith('<ac:inline-comment-marker ac:ref="ref-deleted-h1-heading-top">\u00a0</ac:inline-comment-marker><h1>ACI Hardening</h1>'))

    def test_deleted_h1_body_comment_does_not_jump_to_next_h1_when_gap_filled(self):
        old_storage = (
            "<h1>Removed Heading</h1>"
            "<p>Shared body sentence.</p>"
            "<h1>Surviving Heading</h1>"
            "<p>Stable trailing paragraph.</p>"
        )
        new_storage = (
            "<h1>Surviving Heading</h1>"
            "<p>Shared body sentence.</p>"
            "<p>Stable trailing paragraph.</p>"
        )

        anchor = "Shared body sentence."
        anchor_start = old_storage.index(anchor)
        markers = [
            {
                "ref": "ref-deleted-h1-body-gap-fill",
                "anchor_html": anchor,
                "left_context": old_storage[max(0, anchor_start - 80):anchor_start],
                "right_context": old_storage[anchor_start + len(anchor):anchor_start + len(anchor) + 80],
                "start": anchor_start,
                "end": anchor_start + len(anchor),
                "heading_path": [
                    {"level": 1, "text": "Removed Heading", "normalized_text": "removed heading"},
                ],
            },
        ]

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            markers,
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertTrue(
            updated.startswith('<ac:inline-comment-marker ac:ref="ref-deleted-h1-body-gap-fill">\u00a0</ac:inline-comment-marker><h1>Surviving Heading</h1>')
        )
        self.assertNotIn(
            '<h1>Surviving Heading</h1><p><ac:inline-comment-marker ac:ref="ref-deleted-h1-body-gap-fill">Shared body sentence.</ac:inline-comment-marker></p>',
            updated,
        )

    def test_h1_heading_rename_preserves_heading_and_internal_comment_context(self):
        old_storage = (
            "<h1>Logical Design</h1>"
            "<p>comment 11</p>"
        )
        new_storage = (
            "<h1>Demo Text</h1>"
            "<p>comment 11 updated</p>"
        )

        heading_anchor = "Logical Design"
        heading_start = old_storage.index(heading_anchor)
        markers = [
            {
                "ref": "ref-rename-h1-heading",
                "anchor_html": heading_anchor,
                "left_context": old_storage[max(0, heading_start - 80):heading_start],
                "right_context": old_storage[heading_start + len(heading_anchor):heading_start + len(heading_anchor) + 80],
                "start": heading_start,
                "end": heading_start + len(heading_anchor),
                "heading_path": [
                    {"level": 1, "text": "Logical Design", "normalized_text": "logical design"},
                ],
            },
            {
                "ref": "ref-rename-h1-body",
                "anchor_html": "comment 11",
                "left_context": "</h1><p>",
                "right_context": "</p>",
                "start": old_storage.index("comment 11"),
                "end": old_storage.index("comment 11") + len("comment 11"),
                "heading_path": [
                    {"level": 1, "text": "Logical Design", "normalized_text": "logical design"},
                ],
            },
        ]

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            markers,
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 2)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertIn(
            '<h1><ac:inline-comment-marker ac:ref="ref-rename-h1-heading">Demo Text</ac:inline-comment-marker></h1>',
            updated,
        )
        self.assertIn(
            '<p><ac:inline-comment-marker ac:ref="ref-rename-h1-body">comment 11</ac:inline-comment-marker> updated</p>',
            updated,
        )

    def test_h1_heading_rename_preserves_unique_internal_comment_when_left_context_contains_old_heading(self):
        old_storage = (
            "<h1>Logical Design</h1>"
            "<p>This section is divided in two sub-sections:</p>"
            "<ul>"
            "<li>Building Blocks: The purpose of this sub-section is to briefly describe each one of the Tenant objects.</li>"
            "</ul>"
        )
        new_storage = (
            "<h1>Logical Design Updated</h1>"
            "<p>This section is divided in two sub-sections:</p>"
            "<ul>"
            "<li>Building Blocks: The purpose of this sub-section is to briefly describe each one of the Tenant objects.</li>"
            "</ul>"
        )

        heading_anchor = "Logical Design"
        body_anchor = "sub-section is to briefly describe"
        heading_start = old_storage.index(heading_anchor)
        body_start = old_storage.index(body_anchor)
        markers = [
            {
                "ref": "ref-logical-rename-heading",
                "anchor_html": heading_anchor,
                "left_context": old_storage[max(0, heading_start - 80):heading_start],
                "right_context": old_storage[heading_start + len(heading_anchor):heading_start + len(heading_anchor) + 80],
                "start": heading_start,
                "end": heading_start + len(heading_anchor),
                "heading_path": [
                    {"level": 1, "text": "Logical Design", "normalized_text": "logical design"},
                ],
            },
            {
                "ref": "ref-logical-rename-body",
                "anchor_html": body_anchor,
                "left_context": old_storage[max(0, body_start - 80):body_start],
                "right_context": old_storage[body_start + len(body_anchor):body_start + len(body_anchor) + 80],
                "start": body_start,
                "end": body_start + len(body_anchor),
                "heading_path": [
                    {"level": 1, "text": "Logical Design", "normalized_text": "logical design"},
                ],
            },
        ]

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            markers,
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 2)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertIn(
            '<h1><ac:inline-comment-marker ac:ref="ref-logical-rename-heading">Logical Design Updated</ac:inline-comment-marker></h1>',
            updated,
        )
        self.assertIn(
            '<li>Building Blocks: The purpose of this <ac:inline-comment-marker ac:ref="ref-logical-rename-body">sub-section is to briefly describe</ac:inline-comment-marker> each one of the Tenant objects.</li>',
            updated,
        )

    def test_h1_renamed_body_comment_becomes_orphan_when_duplicate_text_exists_under_other_h1(self):
        old_storage = (
            "<h1>Logical Design</h1>"
            "<p>Shared anchor sentence.</p>"
            "<h1>Other Heading</h1>"
            "<p>Shared anchor sentence.</p>"
        )
        new_storage = (
            "<h1>Other Heading</h1>"
            "<p>Shared anchor sentence.</p>"
            "<h1>Demo Text</h1>"
            "<p>Shared anchor sentence.</p>"
        )

        anchor = "Shared anchor sentence."
        anchor_start = old_storage.index(anchor)
        markers = [
            {
                "ref": "ref-rename-h1-duplicate-body",
                "anchor_html": anchor,
                "left_context": old_storage[max(0, anchor_start - 80):anchor_start],
                "right_context": old_storage[anchor_start + len(anchor):anchor_start + len(anchor) + 80],
                "start": anchor_start,
                "end": anchor_start + len(anchor),
                "heading_path": [
                    {"level": 1, "text": "Logical Design", "normalized_text": "logical design"},
                ],
            },
        ]

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            markers,
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertTrue(
            updated.startswith('<ac:inline-comment-marker ac:ref="ref-rename-h1-duplicate-body">\u00a0</ac:inline-comment-marker>')
        )
        self.assertNotIn(
            '<h1>Other Heading</h1><p><ac:inline-comment-marker ac:ref="ref-rename-h1-duplicate-body">Shared anchor sentence.</ac:inline-comment-marker></p>',
            updated,
        )

    def test_empty_anchor_comment_is_pinned_to_top_of_page_scope(self):
        new_storage = (
            "<h2>Surviving Section</h2>"
            "<p>Current content remains.</p>"
        )
        markers = [
            {
                "ref": "ref-orphan-top",
                "anchor_html": "\u00a0",
                "left_context": "",
                "right_context": "",
                "start": 0,
                "end": 0,
            }
        ]

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            markers,
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 1)
        self.assertTrue(updated.startswith('<ac:inline-comment-marker ac:ref="ref-orphan-top">\u00a0</ac:inline-comment-marker>'))
        self.assertIn('<h2>Surviving Section</h2>', updated)


if __name__ == "__main__":
    unittest.main()