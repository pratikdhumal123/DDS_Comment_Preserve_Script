import unittest

from comment_preserve_publish import _inject_inline_markers


def _nth_index(text: str, needle: str, occurrence: int = 1) -> int:
    start = -1
    for _ in range(occurrence):
        start = text.index(needle, start + 1)
    return start


def _marker(old_storage: str, anchor: str, ref: str, occurrence: int = 1) -> dict:
    anchor_start = _nth_index(old_storage, anchor, occurrence)
    return {
        "ref": ref,
        "anchor_html": anchor,
        "left_context": old_storage[max(0, anchor_start - 80):anchor_start],
        "right_context": old_storage[anchor_start + len(anchor):anchor_start + len(anchor) + 80],
        "start": anchor_start,
        "end": anchor_start + len(anchor),
    }


class CommentStructuralScenarioTests(unittest.TestCase):
    def test_bullet_item_replacement_stays_on_rewritten_item(self):
        old_storage = "<ul><li>Alpha old bullet.</li><li>Neighbor bullet.</li></ul>"
        new_storage = "<ul><li>Alpha new bullet.</li><li>Neighbor bullet.</li></ul>"

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            [_marker(old_storage, "old", "ref-list-replace")],
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertIn(
            '<ul><li>Alpha <ac:inline-comment-marker ac:ref="ref-list-replace">new</ac:inline-comment-marker> bullet.</li><li>Neighbor bullet.</li></ul>',
            updated,
        )

    def test_bullet_item_reorder_does_not_jump_to_same_phrase_in_neighbor_item(self):
        old_storage = (
            "<ul>"
            "<li>Alpha target phrase one.</li>"
            "<li>Beta target phrase two.</li>"
            "</ul>"
        )
        new_storage = (
            "<ul>"
            "<li>Beta target phrase two.</li>"
            "<li>Alpha target phrase one.</li>"
            "</ul>"
        )

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            [_marker(old_storage, "target phrase one.", "ref-list-reorder")],
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertIn(
            '<li>Alpha <ac:inline-comment-marker ac:ref="ref-list-reorder">target phrase one.</ac:inline-comment-marker></li>',
            updated,
        )
        self.assertNotIn(
            '<li>Beta <ac:inline-comment-marker ac:ref="ref-list-reorder">target phrase two.</ac:inline-comment-marker></li>',
            updated,
        )

    def test_numbered_item_renumber_only_keeps_comment_on_same_item_text(self):
        old_storage = "<ol><li>Original numbered step.</li><li>Second step.</li></ol>"
        new_storage = "<ol start=\"4\"><li>Original numbered step.</li><li>Second step.</li></ol>"

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            [_marker(old_storage, "Original numbered step.", "ref-list-renumber")],
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertIn(
            '<li><ac:inline-comment-marker ac:ref="ref-list-renumber">Original numbered step.</ac:inline-comment-marker></li>',
            updated,
        )

    def test_list_item_split_prefers_best_local_fragment(self):
        old_storage = "<ul><li>Alpha stable target phrase and trailing context.</li></ul>"
        new_storage = "<ul><li>Alpha stable target phrase.</li><li>Trailing context moved into second bullet.</li></ul>"

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            [_marker(old_storage, "target phrase and trailing context.", "ref-list-split")],
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertIn(
            '<li>Alpha stable <ac:inline-comment-marker ac:ref="ref-list-split">target phrase.</ac:inline-comment-marker></li>',
            updated,
        )

    def test_list_item_merge_uses_local_context_not_only_last_token(self):
        old_storage = "<ul><li>Alpha stable lead.</li><li>Beta target sentence.</li></ul>"
        new_storage = "<ul><li>Alpha stable lead. Beta target sentence merged.</li></ul>"

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            [_marker(old_storage, "Beta target sentence.", "ref-list-merge")],
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertIn(
            '<li>Alpha stable lead. <ac:inline-comment-marker ac:ref="ref-list-merge">Beta target sentence merged.</ac:inline-comment-marker></li>',
            updated,
        )

    def test_table_cell_replacement_stays_in_same_cell(self):
        old_storage = (
            "<table><tbody>"
            "<tr><td>Rack old value</td><td>Stable</td></tr>"
            "</tbody></table>"
        )
        new_storage = (
            "<table><tbody>"
            "<tr><td>Rack new value</td><td>Stable</td></tr>"
            "</tbody></table>"
        )

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            [_marker(old_storage, "old", "ref-table-cell")],
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertIn(
            '<tr><td>Rack <ac:inline-comment-marker ac:ref="ref-table-cell">new</ac:inline-comment-marker> value</td><td>Stable</td></tr>',
            updated,
        )

    def test_table_row_delete_does_not_jump_to_same_value_in_other_row(self):
        old_storage = (
            "<table><tbody>"
            "<tr><td>Node A</td><td>Target value</td></tr>"
            "<tr><td>Node B</td><td>Target value</td></tr>"
            "</tbody></table>"
        )
        new_storage = (
            "<table><tbody>"
            "<tr><td>Node B</td><td>Target value</td></tr>"
            "</tbody></table>"
        )

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            [_marker(old_storage, "Target value", "ref-table-delete", occurrence=1)],
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertNotIn(
            '<ac:inline-comment-marker ac:ref="ref-table-delete">Target value</ac:inline-comment-marker>',
            updated,
        )
        self.assertIn('ref-table-delete', updated)

    def test_table_row_reorder_preserves_comment_on_same_row_content_when_context_is_strong(self):
        old_storage = (
            "<table><tbody>"
            "<tr><td>Node A</td><td>Leaf role</td></tr>"
            "<tr><td>Node B</td><td>Spine role</td></tr>"
            "</tbody></table>"
        )
        new_storage = (
            "<table><tbody>"
            "<tr><td>Node B</td><td>Spine role</td></tr>"
            "<tr><td>Node A</td><td>Leaf role</td></tr>"
            "</tbody></table>"
        )

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            [_marker(old_storage, "Leaf role", "ref-table-reorder")],
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertIn(
            '<tr><td>Node A</td><td><ac:inline-comment-marker ac:ref="ref-table-reorder">Leaf role</ac:inline-comment-marker></td></tr>',
            updated,
        )
        self.assertNotIn(
            '<tr><td>Node B</td><td><ac:inline-comment-marker ac:ref="ref-table-reorder">Spine role</ac:inline-comment-marker></td></tr>',
            updated,
        )

    def test_table_to_paragraph_transform_preserves_comment_on_rewritten_text_when_row_identity_survives(self):
        old_storage = (
            '<h2>Inventory</h2>'
            '<table><tbody><tr><td>Node A</td><td>Primary fabric role</td></tr></tbody></table>'
        )
        new_storage = (
            '<h2>Inventory</h2>'
            '<p>Node A now serves as the primary fabric role in this environment.</p>'
        )

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            [_marker(old_storage, 'Primary fabric role', 'ref-table-to-para')],
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertIn(
            '<p>Node A now serves as the <ac:inline-comment-marker ac:ref="ref-table-to-para">primary fabric role</ac:inline-comment-marker> in this environment.</p>',
            updated,
        )

    def test_macro_body_rewrite_keeps_comment_inside_same_macro(self):
        old_storage = (
            '<ac:structured-macro ac:name="info">'
            '<ac:rich-text-body><p>Alpha old macro text.</p></ac:rich-text-body>'
            '</ac:structured-macro>'
        )
        new_storage = (
            '<ac:structured-macro ac:name="info">'
            '<ac:rich-text-body><p>Alpha new macro text.</p></ac:rich-text-body>'
            '</ac:structured-macro>'
        )

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            [_marker(old_storage, "old", "ref-macro-rewrite")],
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertIn(
            '<ac:rich-text-body><p>Alpha <ac:inline-comment-marker ac:ref="ref-macro-rewrite">new</ac:inline-comment-marker> macro text.</p></ac:rich-text-body>',
            updated,
        )

    def test_macro_to_paragraph_relocation_keeps_comment_on_visible_text(self):
        old_storage = (
            '<ac:structured-macro ac:name="info">'
            '<ac:rich-text-body><p>Alpha target phrase stable tail.</p></ac:rich-text-body>'
            '</ac:structured-macro>'
        )
        new_storage = '<p>Alpha target phrase updated stable tail.</p>'

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            [_marker(old_storage, 'target phrase', 'ref-macro-to-paragraph')],
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertIn(
            '<p>Alpha <ac:inline-comment-marker ac:ref="ref-macro-to-paragraph">target phrase</ac:inline-comment-marker> updated stable tail.</p>',
            updated,
        )

    def test_paragraph_split_prefers_fragment_with_strongest_context(self):
        old_storage = '<p>Alpha stable context target phrase and trailing context.</p>'
        new_storage = '<p>Alpha stable context target phrase.</p><p>Trailing context moved away.</p>'

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            [_marker(old_storage, 'target phrase and trailing context.', 'ref-split-paragraph')],
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertIn(
            '<p>Alpha stable context <ac:inline-comment-marker ac:ref="ref-split-paragraph">target phrase.</ac:inline-comment-marker></p>',
            updated,
        )

    def test_paragraph_to_table_transform_preserves_visible_phrase_when_row_identity_is_strong(self):
        old_storage = '<p>Node A uses target phrase for role assignment.</p>'
        new_storage = '<table><tbody><tr><td>Node A</td><td>target phrase updated for role assignment</td></tr></tbody></table>'

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            [_marker(old_storage, 'target phrase', 'ref-paragraph-to-table')],
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertIn(
            '<tr><td>Node A</td><td><ac:inline-comment-marker ac:ref="ref-paragraph-to-table">target phrase</ac:inline-comment-marker> updated for role assignment</td></tr>',
            updated,
        )

    def test_mixed_inline_format_anchor_spanning_multiple_tags_preserves_full_visible_phrase(self):
        old_storage = '<p>Alpha target phrase stable tail.</p>'
        new_storage = '<p>Alpha <strong>target</strong> <a href="https://x">phrase</a> <code>updated</code> stable tail.</p>'

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            [_marker(old_storage, 'target phrase', 'ref-mixed-format')],
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertNotIn('<strong><ac:inline-comment-marker ac:ref="ref-mixed-format">target</ac:inline-comment-marker></strong>', updated)
        self.assertIn('ac:ref="ref-mixed-format"', updated)

    def test_two_paragraphs_merged_into_one_preserves_comment_on_local_segment(self):
        old_storage = '<p>Alpha stable sentence.</p><p>Beta target sentence.</p>'
        new_storage = '<p>Alpha stable sentence. Beta target sentence merged.</p>'

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            [_marker(old_storage, 'Beta target sentence.', 'ref-merge-paragraph')],
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertIn(
            '<p>Alpha stable sentence. <ac:inline-comment-marker ac:ref="ref-merge-paragraph">Beta target sentence merged.</ac:inline-comment-marker></p>',
            updated,
        )

    def test_cross_heading_moved_and_rewritten_content_follows_only_when_context_is_strong(self):
        old_storage = (
            '<h2>Source</h2>'
            '<p>Alpha stable lead target phrase and trailing context.</p>'
            '<h2>Destination</h2>'
            '<p>Destination overview text.</p>'
        )
        new_storage = (
            '<h2>Source</h2>'
            '<p>Source placeholder now removed.</p>'
            '<h2>Destination</h2>'
            '<p>Alpha stable lead target phrase rewritten with trailing context preserved.</p>'
        )
        anchor = 'target phrase and trailing context.'
        anchor_start = old_storage.index(anchor)
        marker = {
            'ref': 'ref-cross-heading-strong',
            'anchor_html': anchor,
            'left_context': old_storage[max(0, anchor_start - 80):anchor_start],
            'right_context': old_storage[anchor_start + len(anchor):anchor_start + len(anchor) + 80],
            'start': anchor_start,
            'end': anchor_start + len(anchor),
            'heading_path': [
                {'level': 2, 'text': 'Source', 'normalized_text': 'source'},
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
            '<h2>Destination</h2><p>Alpha stable lead <ac:inline-comment-marker ac:ref="ref-cross-heading-strong">target phrase rewritten with trailing context preserved.</ac:inline-comment-marker></p>',
            updated,
        )

    def test_duplicate_heavy_reordered_sections_keep_comment_in_original_section(self):
        repeated = 'shared boilerplate text repeated for locality control'
        old_storage = (
            '<h2>Section A</h2>'
            f'<p>{repeated} alpha unique target.</p>'
            '<h2>Section B</h2>'
            f'<p>{repeated} beta unique target.</p>'
            '<h2>Section C</h2>'
            f'<p>{repeated} gamma unique target.</p>'
        )
        new_storage = (
            '<h2>Section C</h2>'
            f'<p>{repeated} gamma unique target.</p>'
            '<h2>Section A</h2>'
            f'<p>{repeated} alpha unique target.</p>'
            '<h2>Section B</h2>'
            f'<p>{repeated} beta unique target.</p>'
        )

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            [_marker(old_storage, 'alpha unique target.', 'ref-section-reorder')],
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertIn(
            f'<p>{repeated} <ac:inline-comment-marker ac:ref="ref-section-reorder">alpha unique target.</ac:inline-comment-marker></p>',
            updated,
        )


if __name__ == "__main__":
    unittest.main()