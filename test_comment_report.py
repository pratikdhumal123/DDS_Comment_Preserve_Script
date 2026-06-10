import unittest

from comment_preserve_publish import (
    _build_comment_audit_summary,
    _build_comment_delta,
    _build_comment_marker_map,
    _build_reinjection_payload_audit,
    _build_storage_anchor_audit_from_markers,
    _extract_inline_markers,
    _inject_inline_markers,
)


class CommentReportTests(unittest.TestCase):
    def test_resolved_comment_fields_are_reported(self):
        before_all = [
            {"id": "active-1", "status": "current", "author": "bot", "body_plain": "active body"},
            {"id": "resolved-1", "status": "resolved", "author": "bot", "body_plain": "resolved body"},
            {"id": "resolved-missing", "status": "resolved", "author": "bot", "body_plain": "gone body"},
        ]
        after_all = [
            {"id": "active-1", "status": "current", "author": "bot", "body_plain": "active body"},
            {"id": "resolved-1", "status": "resolved", "author": "bot", "body_plain": "resolved body"},
            {"id": "resolved-new", "status": "resolved", "author": "bot", "body_plain": "new resolved body"},
        ]

        delta = _build_comment_delta(
            before_active=[before_all[0]],
            after_active=[after_all[0]],
            before_all=before_all,
            after_all=after_all,
        )

        self.assertEqual(delta["resolved_preserved_count"], 1)
        self.assertEqual(delta["resolved_missing_count"], 1)
        self.assertEqual(delta["resolved_new_count"], 1)
        self.assertEqual(delta["resolved_preserved_ids"], ["resolved-1"])
        self.assertEqual(delta["resolved_missing_ids"], ["resolved-missing"])
        self.assertEqual(delta["resolved_new_ids"], ["resolved-new"])
        self.assertEqual(delta["resolved_preserved_preview"][0]["id"], "resolved-1")

        summary = _build_comment_audit_summary(
            before_comments=[before_all[1]],
            after_comments=[after_all[1]],
            preserved_ids=["resolved-1"],
        )

        self.assertEqual(summary["total_preserved"], 1)
        self.assertEqual(summary["same_location_count"], 1)
        self.assertEqual(summary["avg_similarity_percent"], 100.0)
        self.assertEqual(summary["method"], "comment_body_similarity_only")

    def test_storage_anchor_audit_marks_exact_visible_anchor(self):
        section = '<p>Alpha <ac:inline-comment-marker ac:ref="ref-1">target</ac:inline-comment-marker> beta.</p>'

        summary = _build_storage_anchor_audit_from_markers(
            before_markers=_extract_inline_markers(section),
            after_markers=_extract_inline_markers(section),
        )

        self.assertEqual(summary["recoverable_marker_count"], 1)
        self.assertEqual(summary["visible_marker_count"], 1)
        self.assertEqual(summary["exact_position_count"], 1)
        self.assertEqual(summary["details"][0]["classification"], "exact_local_position")

    def test_storage_anchor_audit_does_not_count_heading_pinned_delete_as_exact(self):
        before_section = (
            '<h2>Local Heading</h2>'
            '<p><ac:inline-comment-marker ac:ref="ref-1">Deleted sentence lives here.</ac:inline-comment-marker></p>'
        )
        after_section = (
            '<h2><ac:inline-comment-marker ac:ref="ref-1">Local Heading</ac:inline-comment-marker></h2>'
        )

        summary = _build_storage_anchor_audit_from_markers(
            before_markers=_extract_inline_markers(before_section),
            after_markers=_extract_inline_markers(after_section),
        )

        self.assertEqual(summary["recoverable_marker_count"], 1)
        self.assertEqual(summary["visible_marker_count"], 1)
        self.assertEqual(summary["exact_position_count"], 0)
        self.assertEqual(
            summary["details"][0]["classification"],
            "reanchored_with_changed_local_context",
        )

    def test_reinjection_payload_audit_flags_markers_dropped_after_save(self):
        target_markers = [{"ref": "ref-1"}, {"ref": "ref-2"}, {"ref": "ref-3"}]
        payload_section = (
            '<p><ac:inline-comment-marker ac:ref="ref-1">Alpha</ac:inline-comment-marker></p>'
            '<p><ac:inline-comment-marker ac:ref="ref-2">Beta</ac:inline-comment-marker></p>'
            '<p><ac:inline-comment-marker ac:ref="ref-3">Gamma</ac:inline-comment-marker></p>'
        )
        saved_section = (
            '<p><ac:inline-comment-marker ac:ref="ref-1">Alpha</ac:inline-comment-marker></p>'
        )

        summary = _build_reinjection_payload_audit(target_markers, payload_section, saved_section)

        self.assertEqual(summary["target_ref_count"], 3)
        self.assertEqual(summary["payload_visible_marker_count"], 3)
        self.assertEqual(summary["saved_visible_marker_count"], 1)
        self.assertEqual(summary["dropped_after_save_count"], 2)
        self.assertEqual(summary["dropped_after_save_refs_preview"], ["ref-2", "ref-3"])

    def test_extract_inline_markers_includes_nested_markers(self):
        section = (
            '<h2><ac:inline-comment-marker ac:ref="ref-outer">'
            '<ac:inline-comment-marker ac:ref="ref-middle">'
            '<ac:inline-comment-marker ac:ref="ref-inner">Hardware Overview</ac:inline-comment-marker>'
            '</ac:inline-comment-marker>'
            '</ac:inline-comment-marker></h2>'
        )

        markers = _extract_inline_markers(section)

        self.assertEqual([marker["ref"] for marker in markers], ["ref-outer", "ref-middle", "ref-inner"])

    def test_build_comment_marker_map_links_comment_ids_to_marker_refs(self):
        comments = [
            {"id": "470213931", "body_plain": "comment 01", "status": "current"},
            {"id": "470213933", "body_plain": "comment 02", "status": "current"},
        ]
        inline_props = [
            {"comment_id": "470213931", "ref": "ref-1", "anchor_html": "comment 01"},
            {"comment_id": "470213933", "ref": "ref-2", "anchor_html": "comment 02"},
        ]
        marker_details_by_ref = {
            "ref-1": {"ref": "ref-1", "after_anchor_text_preview": "demo01", "classification": "visible_same_anchor_text_but_context_changed"},
            "ref-2": {"ref": "ref-2", "after_anchor_text_preview": "hardware overview", "classification": "reanchored_with_changed_local_context"},
        }

        summary = _build_comment_marker_map(
            comments,
            inline_props,
            marker_details_by_ref=marker_details_by_ref,
            visible_refs={"ref-1", "ref-2"},
        )

        self.assertEqual(summary[0]["comment_id"], "470213931")
        self.assertEqual(summary[0]["ref"], "ref-1")
        self.assertEqual(summary[0]["visible_anchor_text_preview"], "demo01")
        self.assertEqual(summary[1]["classification"], "reanchored_with_changed_local_context")
        self.assertTrue(summary[0]["visible_in_section"])

    def test_short_label_replacement_stays_inline(self):
        old_storage = '<h2>Hardware Overview</h2><p>Cisco Application comment 01 is stable.</p>'
        new_storage = '<h2>Hardware Overview</h2><p>Cisco Application demo01 is stable.</p>'
        marker = {
            'ref': 'ref-short-label-1',
            'anchor_html': 'comment 01',
            'left_context': 'Cisco Application ',
            'right_context': ' is stable.',
            'start': old_storage.index('comment 01'),
            'end': old_storage.index('comment 01') + len('comment 01'),
            'heading_path': [
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
            '<p>Cisco Application <ac:inline-comment-marker ac:ref="ref-short-label-1">demo01</ac:inline-comment-marker> is stable.</p>',
            updated,
        )


if __name__ == "__main__":
    unittest.main()