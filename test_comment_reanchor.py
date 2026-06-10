import json
import os
import tempfile
import unittest

from comment_preserve_publish import _enrich_markers_from_history, _inject_inline_markers, _supplement_markers_from_history
from comment_preserve_publish import _record_comment_ref_heading_ownership, _resolve_owned_comment_refs_for_heading
from comment_preserve_publish import _supplement_markers_from_inline_properties


class CommentReanchorTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()