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


class CommentScaleScenarioTests(unittest.TestCase):
    def test_large_page_with_many_repeated_paragraphs_keeps_comments_local(self):
        repeated = "Shared boilerplate for repeated scale coverage."
        old_parts = []
        new_parts = []
        markers = []

        for index in range(1, 31):
            old_parts.append(f"<h2>Section {index}</h2><p>{repeated} Unique target {index} old.</p>")
            new_parts.append(f"<h2>Section {index}</h2><p>{repeated} Unique target {index} new.</p>")
            if index % 6 == 0:
                old_storage_so_far = "".join(old_parts)
                markers.append(_marker(old_storage_so_far, f"old.", f"ref-scale-{index}", occurrence=1))

        old_storage = "".join(old_parts)
        new_storage = "".join(new_parts)

        markers = []
        for index in range(6, 31, 6):
            markers.append(_marker(old_storage, "old.", f"ref-scale-{index}", occurrence=index // 6))

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            markers,
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, len(markers))
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertIn('<ac:inline-comment-marker ac:ref="ref-scale-6">new.</ac:inline-comment-marker>', updated)
        self.assertIn('<ac:inline-comment-marker ac:ref="ref-scale-30">new.</ac:inline-comment-marker>', updated)
        self.assertNotIn('<ac:inline-comment-marker ac:ref="ref-scale-30">new.</ac:inline-comment-marker></p><h2>Section 1</h2>', updated)

    def test_many_comments_in_same_section_do_not_pull_later_comments_backward(self):
        repeated_intro = "This paragraph repeats enough context to exercise delta tracking."
        old_storage = "<h2>Scale Section</h2>" + "".join(
            f"<p>{repeated_intro} Token {index} old.</p>" for index in range(1, 21)
        )
        new_storage = "<h2>Scale Section</h2>" + "".join(
            f"<p>{repeated_intro} Token {index} new.</p>" for index in range(1, 21)
        )

        markers = [
            _marker(old_storage, "old.", f"ref-many-{index}", occurrence=index)
            for index in range(1, 21)
        ]

        updated, reanchored, skipped, deleted_icons = _inject_inline_markers(
            new_storage,
            markers,
            open_ref_ids=set(),
            section_span=(0, len(new_storage)),
        )

        self.assertEqual(reanchored, 20)
        self.assertEqual(skipped, 0)
        self.assertEqual(deleted_icons, 0)
        self.assertIn(
            f'<p>{repeated_intro} Token 20 <ac:inline-comment-marker ac:ref="ref-many-20">new.</ac:inline-comment-marker></p>',
            updated,
        )
        self.assertNotIn(
            f'<p>{repeated_intro} Token 1 <ac:inline-comment-marker ac:ref="ref-many-20">new.</ac:inline-comment-marker></p>',
            updated,
        )


if __name__ == "__main__":
    unittest.main()