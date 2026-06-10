import re
from difflib import SequenceMatcher
from html import unescape
from typing import List, Tuple

from highlight_scenarios import inline_span_style, paragraph_style


def _normalize_text(text: str) -> str:
    value = str(text or "")
    value = re.sub(r"\s+", " ", value).strip().lower()
    return value


def _strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", str(text or ""))


def _style_for(kind: str) -> str:
    return paragraph_style(kind)


def _inline_span_style(kind: str) -> str:
    return inline_span_style(kind)


def _apply_phrase_highlight(inner_html: str, phrase: str, kind: str) -> Tuple[str, bool]:
    text = str(phrase or "").strip()
    if not text:
        return inner_html, False

    parts = re.split(r"(<[^>]+>)", str(inner_html or ""))
    span_style = _inline_span_style(kind)
    changed = False

    for index in range(0, len(parts), 2):
        text_part = parts[index]
        if not text_part:
            continue

        pattern = re.compile(rf"(?<!\w)({re.escape(text)})(?!\w)", flags=re.IGNORECASE)
        updated_text, count = pattern.subn(
            rf"<span data-dac='hl' style='{span_style}'>\1</span>",
            text_part,
            count=1,
        )
        if count:
            parts[index] = updated_text
            changed = True
            break

    return "".join(parts), changed


def _apply_word_highlights(inner_html: str, words: List[str], kind: str) -> Tuple[str, bool]:
    parts = re.split(r"(<[^>]+>)", str(inner_html or ""))
    span_style = _inline_span_style(kind)
    seen = set()
    changed = False

    candidates = []
    for word in words:
        token = str(word or "").strip()
        key = token.lower()
        if len(token) < 3 or key in seen:
            continue
        seen.add(key)
        candidates.append(token)

    if not candidates:
        return inner_html, False

    for index in range(0, len(parts), 2):
        text_part = parts[index]
        if not text_part:
            continue
        for word in candidates:
            pattern = re.compile(rf"(?<!\w)({re.escape(word)})(?!\w)", flags=re.IGNORECASE)
            updated_text, count = pattern.subn(
                rf"<span data-dac='hl' style='{span_style}'>\1</span>",
                text_part,
                count=1,
            )
            if count:
                text_part = updated_text
                changed = True
        parts[index] = text_part

    return "".join(parts), changed


def _replacement_new_segments(old_visible_text: str, new_visible_text: str) -> List[str]:
    old_words = str(old_visible_text or "").split()
    new_words = str(new_visible_text or "").split()
    matcher = SequenceMatcher(a=old_words, b=new_words)

    segments: List[str] = []
    seen = set()
    for opcode, i1, i2, j1, j2 in matcher.get_opcodes():
        if opcode not in {"insert", "replace"}:
            continue
        phrase = " ".join(new_words[j1:j2]).strip()
        key = phrase.lower()
        if len(phrase) < 2 or key in seen:
            continue
        seen.add(key)
        segments.append(phrase)
    return segments


def _best_block_match(html: str, primary_text: str, secondary_text: str = ""):
    block_pattern = re.compile(
        r"<(p|li|td|th|blockquote|h1|h2|h3|h4|h5|h6)\b([^>]*)>(.*?)</\1>",
        flags=re.IGNORECASE | re.DOTALL,
    )

    primary = _normalize_text(primary_text)
    secondary = _normalize_text(secondary_text)
    best_match = None
    best_score = 0.0

    for match in block_pattern.finditer(html):
        attrs = match.group(2) or ""
        if "data-dac='hl'" in attrs or 'data-dac="hl"' in attrs:
            continue
        inner = match.group(3) or ""
        block_text = _normalize_text(unescape(_strip_tags(inner)))
        if not block_text:
            continue

        scores = []
        if primary:
            scores.append(1.0 if primary in block_text else SequenceMatcher(a=primary, b=block_text).ratio())
        if secondary:
            scores.append(1.0 if secondary in block_text else SequenceMatcher(a=secondary, b=block_text).ratio())
        score = max(scores or [0.0])
        if score > best_score:
            best_score = score
            best_match = match

    return best_match, best_score


def try_highlight_text_block(storage_html: str, visible_text: str, kind: str) -> Tuple[str, bool]:
    """Highlight only the matching inline phrase/words inside the best block."""
    html = str(storage_html or "")
    if not _normalize_text(visible_text):
        return html, False

    match, score = _best_block_match(html, visible_text)
    if not match or score < 0.55:
        return html, False

    tag = match.group(1)
    attrs = match.group(2) or ""
    inner = match.group(3) or ""

    updated_inner, changed = _apply_phrase_highlight(inner, visible_text, kind)
    if not changed:
        updated_inner, changed = _apply_word_highlights(inner, str(visible_text or "").split(), kind)
    if not changed:
        return html, False

    replacement = f"<{tag}{attrs}>{updated_inner}</{tag}>"
    html = html[:match.start()] + replacement + html[match.end():]
    return html, True

    return html, False


def try_highlight_replaced_text_block(storage_html: str, old_visible_text: str, new_visible_text: str) -> Tuple[str, bool]:
    """Highlight only the new/updated inline segments inside the best matching block."""
    html = str(storage_html or "")
    if not _normalize_text(old_visible_text) and not _normalize_text(new_visible_text):
        return html, False

    best_match, best_score = _best_block_match(html, new_visible_text, old_visible_text)
    if not best_match or best_score < 0.60:
        return html, False

    tag = best_match.group(1)
    inner = best_match.group(3) or ""

    highlighted_inner = inner
    changed = False
    for segment in _replacement_new_segments(old_visible_text, new_visible_text):
        highlighted_inner, segment_changed = _apply_phrase_highlight(highlighted_inner, segment, "replaced")
        changed = changed or segment_changed

    if not changed:
        fallback_words = _replacement_new_segments(old_visible_text, new_visible_text)
        highlighted_inner, changed = _apply_word_highlights(highlighted_inner, fallback_words, "replaced")

    if not changed:
        return html, False

    replacement = f"<{tag}{best_match.group(2) or ''}>{highlighted_inner}</{tag}>"
    html = html[:best_match.start()] + replacement + html[best_match.end():]
    return html, True
