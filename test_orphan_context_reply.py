import unittest

from comment_preserve_publish import (
    _build_orphan_context_reply_storage,
    _build_orphan_context_targets,
    _format_heading_path_for_display,
    _reply_already_contains_orphan_context,
)


class OrphanContextReplyTests(unittest.TestCase):
    def test_format_heading_path_for_display_uses_arrow_separator(self):
        heading_path = [
            {"level": 1, "text": "Studio Part", "normalized_text": "studio part"},
            {"level": 2, "text": "Domains, Pools and AAEP", "normalized_text": "domains, pools and aaep"},
        ]

        self.assertEqual(
            _format_heading_path_for_display(heading_path),
            "Studio Part -> Domains, Pools and AAEP",
        )

    def test_build_orphan_context_targets_maps_orphan_ref_to_comment_and_path(self):
        storage_anchor_audit = {
            "details": [
                {
                    "ref": "ref-1",
                    "visible_after_publish": True,
                    "after_anchor_text_preview": "",
                },
                {
                    "ref": "ref-2",
                    "visible_after_publish": True,
                    "after_anchor_text_preview": "still anchored",
                },
            ]
        }
        inline_props = [
            {"comment_id": "comment-1", "ref": "ref-1", "anchor_html": "deleted text"},
            {"comment_id": "comment-2", "ref": "ref-2", "anchor_html": "live text"},
        ]
        markers = [
            {
                "ref": "ref-1",
                "anchor_html": "deleted text",
                "heading_path": [
                    {"level": 1, "text": "Studio Part", "normalized_text": "studio part"},
                    {"level": 2, "text": "Domains, Pools and AAEP", "normalized_text": "domains, pools and aaep"},
                ],
            }
        ]

        targets = _build_orphan_context_targets(
            storage_anchor_audit,
            inline_props,
            markers,
            fallback_heading_title="Studio Part",
        )

        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0]["comment_id"], "comment-1")
        self.assertEqual(targets[0]["heading_path_text"], "Studio Part -> Domains, Pools and AAEP")
        self.assertIn("Original location:", targets[0]["reply_storage"])

    def test_reply_already_contains_orphan_context_matches_same_reply(self):
        reply_storage = _build_orphan_context_reply_storage(
            "Studio Part -> Domains, Pools and AAEP",
            "deleted text",
        )

        existing_replies = [
            {
                "body": {
                    "storage": {
                        "value": reply_storage,
                    }
                }
            }
        ]

        self.assertTrue(_reply_already_contains_orphan_context(existing_replies, reply_storage))


if __name__ == "__main__":
    unittest.main()