import unittest

from table_image_highlighter import (
    apply_direct_storage_html_highlights,
    try_highlight_ac_image,
    try_highlight_table_cell_diff,
    try_highlight_table_row,
)


def _normalize_compare_text(text: str) -> str:
    return " ".join(str(text or "").lower().split()).strip()


def _visible_line_text(text: str) -> str:
    return " ".join(str(text or "").split()).strip()


def _escape_text(value: str) -> str:
    return (
        str(value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _window_bounds(window, total_len):
    if not window:
        return (0, total_len)
    return window


def _debug_skip_once(_note: str) -> None:
    return None


class TableImageHighlighterTests(unittest.TestCase):
    def test_direct_highlight_marks_only_one_new_duplicate_table(self):
        table_html = "<table><tr><td>A</td></tr></table>"
        previous = f"<div>{table_html}</div>"
        current = f"<div>{table_html}{table_html}</div>"

        result = apply_direct_storage_html_highlights(previous, current)

        self.assertEqual(result.count("data-dac='hl'"), 1)
        self.assertEqual(result.count("<table>"), 2)

    def test_table_row_highlight_stays_row_level(self):
        html = "<table><tbody><tr><td>ID</td><td>Name</td></tr><tr><td>1</td><td>Updated</td></tr></tbody></table>"

        result = try_highlight_table_row(
            "| 1 | Updated |",
            html,
            "replaced",
            normalize_compare_text=_normalize_compare_text,
        )

        self.assertIn("<tr data-dac='hl'", result)
        self.assertNotIn("<div data-dac='hl'", result)

    def test_table_cell_diff_highlights_only_changed_cell(self):
        html = "<table><tbody><tr><td>1</td><td>New</td></tr></tbody></table>"

        result = try_highlight_table_cell_diff(
            "| 1 | Old |",
            "| 1 | New |",
            html,
            normalize_compare_text=_normalize_compare_text,
            visible_line_text=_visible_line_text,
            try_highlight_text_block=None,
        )

        self.assertIn("<td data-dac='hl'", result)
        self.assertNotIn("<tr data-dac='hl'", result)

    def test_ambiguous_duplicate_ac_image_without_scope_is_skipped(self):
        block = '<ac:image><ri:attachment ri:filename="same.png" /></ac:image>'
        html = f"<p>{block}</p><p>{block}</p>"

        result = try_highlight_ac_image(
            "!same.png!",
            html,
            "added",
            debug_skip_once=_debug_skip_once,
        )

        self.assertEqual(result, html)


if __name__ == "__main__":
    unittest.main()
