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


class CommentScenarioSuiteTests(unittest.TestCase):
    def test_exact_match_anchor_stays_exact(self):
        storage = "<p>Alpha target beta.</p>"

        updated, reanchored, skipped, _icons = _inject_inline_markers(
            storage,
            [_marker(storage, "target", "ref-exact")],
            open_ref_ids=set(),
            section_span=(0, len(storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertIn('<p>Alpha <ac:inline-comment-marker ac:ref="ref-exact">target</ac:inline-comment-marker> beta.</p>', updated)

    def test_replaced_word_stays_on_replacement_text(self):
        old_storage = "<p>Alpha old beta.</p>"
        new_storage = "<p>Alpha new beta.</p>"

        updated, reanchored, skipped, _icons = _inject_inline_markers(
            new_storage,
            [_marker(old_storage, "old", "ref-word")],
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertIn('<p>Alpha <ac:inline-comment-marker ac:ref="ref-word">new</ac:inline-comment-marker> beta.</p>', updated)

    def test_replaced_sentence_stays_on_rewritten_sentence(self):
        old_storage = "<p>Before. Original sentence lives here. After.</p>"
        new_storage = "<p>Before. Rewritten sentence lives here now. After.</p>"

        updated, reanchored, skipped, _icons = _inject_inline_markers(
            new_storage,
            [_marker(old_storage, "Original sentence lives here.", "ref-sentence")],
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertIn(
            '<p>Before. <ac:inline-comment-marker ac:ref="ref-sentence">Rewritten sentence lives here now.</ac:inline-comment-marker> After.</p>',
            updated,
        )

    def test_repeated_anchor_prefers_nearest_occurrence(self):
        old_storage = "<p>Alpha token.</p><p>Beta token.</p>"
        new_storage = old_storage

        updated, reanchored, skipped, _icons = _inject_inline_markers(
            new_storage,
            [_marker(old_storage, "token", "ref-repeat", occurrence=2)],
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertIn('<p>Beta <ac:inline-comment-marker ac:ref="ref-repeat">token</ac:inline-comment-marker>.</p>', updated)
        self.assertNotIn('<p>Alpha <ac:inline-comment-marker ac:ref="ref-repeat">token</ac:inline-comment-marker>.</p>', updated)

    def test_prior_insertions_do_not_pull_later_repeated_anchor_backward(self):
        prefix = "".join(f"<p>Prefix {index} stable text.</p>" for index in range(12))
        old_storage = prefix + "<p>same token same token</p>"
        new_storage = old_storage

        markers = [_marker(old_storage, f"Prefix {index}", f"ref-prefix-{index}") for index in range(12)]
        markers.append(_marker(old_storage, "token", "ref-repeat-late", occurrence=2))

        updated, reanchored, skipped, _icons = _inject_inline_markers(
            new_storage,
            markers,
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 13)
        self.assertEqual(skipped, 0)
        self.assertIn(
            '<p>same token same <ac:inline-comment-marker ac:ref="ref-repeat-late">token</ac:inline-comment-marker></p>',
            updated,
        )
        self.assertNotIn(
            '<p>same <ac:inline-comment-marker ac:ref="ref-repeat-late">token</ac:inline-comment-marker> same token</p>',
            updated,
        )

    def test_replaced_text_with_repeated_context_stays_in_local_section(self):
        prefix = (
            "The following table text is intentionally long so both sections share the same local context "
            "before the changed phrase appears in the paragraph "
        )
        old_storage = (
            "<h2>First Section</h2>"
            f"<p>{prefix}stable reference.</p>"
            "<h2>Second Section</h2>"
            f"<p>{prefix}folling text replace.</p>"
        )
        new_storage = (
            "<h2>First Section</h2>"
            f"<p>{prefix}stable reference.</p>"
            "<h2>Second Section</h2>"
            f"<p>{prefix}following text updated.</p>"
        )

        updated, reanchored, skipped, _icons = _inject_inline_markers(
            new_storage,
            [_marker(old_storage, "folling text replace.", "ref-local-replace")],
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 1)
        self.assertEqual(skipped, 0)
        self.assertIn(
            '<p>The following table text is intentionally long so both sections share the same local context before the changed phrase appears in the paragraph <ac:inline-comment-marker ac:ref="ref-local-replace">following text updated.</ac:inline-comment-marker></p>',
            updated,
        )
        self.assertNotIn('ref="ref-local-replace">stable reference.', updated)

    def test_deleted_comments_in_different_headings_stay_local(self):
        old_storage = (
            "<h2>First Heading</h2>"
            "<p>Delete first block.</p>"
            "<h2>Second Heading</h2>"
            "<p>Delete second block.</p>"
        )
        new_storage = "<h2>First Heading</h2><h2>Second Heading</h2>"

        updated, reanchored, skipped, _icons = _inject_inline_markers(
            new_storage,
            [
                _marker(old_storage, "Delete first block.", "ref-first"),
                _marker(old_storage, "Delete second block.", "ref-second"),
            ],
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 2)
        self.assertEqual(skipped, 0)
        self.assertIn('<h2><ac:inline-comment-marker ac:ref="ref-first">First Heading</ac:inline-comment-marker></h2>', updated)
        self.assertIn('<h2><ac:inline-comment-marker ac:ref="ref-second">Second Heading</ac:inline-comment-marker></h2>', updated)

    def test_mixed_scenarios_work_together(self):
        old_storage = (
            "<h2>Section One</h2>"
            "<p>Exact anchor stays.</p>"
            "<p>Alpha old beta.</p>"
            "<h3>Margine</h3>"
            "<p>Deleted sentence lives here.</p>"
            "<p>First token.</p>"
            "<p>Second token.</p>"
            "<h2>Section Two</h2>"
            "<p>Delete lower block.</p>"
        )
        new_storage = (
            "<h2>Section One</h2>"
            "<p>Exact anchor stays.</p>"
            "<p>Alpha new beta.</p>"
            "<h3>Margine</h3>"
            "<p>First token.</p>"
            "<p>Second token.</p>"
            "<h2>Section Two</h2>"
        )

        markers = [
            _marker(old_storage, "anchor", "ref-exact"),
            _marker(old_storage, "old", "ref-word"),
            _marker(old_storage, "Deleted sentence lives here.", "ref-deleted"),
            _marker(old_storage, "token", "ref-repeat", occurrence=2),
            _marker(old_storage, "Delete lower block.", "ref-lower"),
        ]

        updated, reanchored, skipped, _icons = _inject_inline_markers(
            new_storage,
            markers,
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 5)
        self.assertEqual(skipped, 0)
        self.assertIn('<p>Exact <ac:inline-comment-marker ac:ref="ref-exact">anchor</ac:inline-comment-marker> stays.</p>', updated)
        self.assertIn('<p>Alpha <ac:inline-comment-marker ac:ref="ref-word">new</ac:inline-comment-marker> beta.</p>', updated)
        self.assertIn('<h3><ac:inline-comment-marker ac:ref="ref-deleted">Margine</ac:inline-comment-marker></h3>', updated)
        self.assertIn('<p>Second <ac:inline-comment-marker ac:ref="ref-repeat">token</ac:inline-comment-marker>.</p>', updated)
        self.assertIn('<h2><ac:inline-comment-marker ac:ref="ref-lower">Section Two</ac:inline-comment-marker></h2>', updated)


if __name__ == "__main__":
    unittest.main()