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