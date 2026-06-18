import argparse
import base64
from collections import Counter
import difflib
import gzip
import html
import json
import mimetypes
import os
import re
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

from highlight_scenarios import (
    cleanup_style_token_patterns,
    heading_style,
    image_tag_style,
    image_wrapper_style,
    inline_span_style,
    table_row_style,
    table_wrapper_style,
)
from table_image_highlighter import (
    apply_direct_storage_html_highlights as _table_image_apply_direct_storage_html_highlights,
    collect_storage_image_changes as _table_image_collect_storage_image_changes,
    collect_storage_table_changes as _table_image_collect_storage_table_changes,
    disambiguate_table_with_context as _table_image_disambiguate_table_with_context,
    extract_image_candidates as _table_image_extract_image_candidates,
    image_change_key as _table_image_image_change_key,
    parse_table_cells as _table_image_parse_table_cells,
    table_change_key as _table_image_table_change_key,
    try_highlight_ac_image as _table_image_try_highlight_ac_image,
    try_highlight_any_ac_image as _table_image_try_highlight_any_ac_image,
    try_highlight_img as _table_image_try_highlight_img,
    try_highlight_table_block as _table_image_try_highlight_table_block,
    try_highlight_table_cell_diff as _table_image_try_highlight_table_cell_diff,
    try_highlight_table_row as _table_image_try_highlight_table_row,
)
_FULL_PAGE_AUTO_SENTINEL = "__AUTO_FULL_PAGE__"
_ANCHOR_REGION_AUTO_SENTINEL = "__AUTO_ANCHOR_REGION__"
_HEADING_PATH_SEPARATOR = " > "
_DEFAULT_MANAGED_ANCHOR_START = "docautomation_start"
_DEFAULT_MANAGED_ANCHOR_END = "docautomation_end"

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

def get_python_executable() -> str:
    """Return the path to the current Python executable."""
    return sys.executable

build_diff: Any = None
build_publish_marker: Any = None
content_hash: Any = None
convert_storage_to_markdown: Any = None
get_page_marker: Any = None
parse_marker_value: Any = None
upsert_page_marker: Any = None
try_highlight_text_block: Any = None
try_highlight_replaced_text_block: Any = None

try:
    from safe_block_highlighter import (  # type: ignore[reportMissingImports]
        try_highlight_text_block as _default_try_highlight_text_block,
        try_highlight_replaced_text_block as _default_try_highlight_replaced_text_block,
    )
    try_highlight_text_block = _default_try_highlight_text_block
    try_highlight_replaced_text_block = _default_try_highlight_replaced_text_block
except ImportError:
    pass

# Import HTML report generator (alongside this script)
try:
    from html_report_generator import generate_html_report  # type: ignore[reportMissingImports]
except ImportError:
    generate_html_report = None


def _compress_text(text: str) -> str:
    """Gzip + base64 encode text so large content fits in Confluence property limits."""
    compressed = gzip.compress(text.encode("utf-8"), compresslevel=9)
    return "gz:" + base64.b64encode(compressed).decode("ascii")


def _decompress_text(value: str) -> str:
    """Decompress a gzip + base64 encoded string. Returns original if not compressed."""
    if not isinstance(value, str) or not value.startswith("gz:"):
        return value
    try:
        raw = base64.b64decode(value[3:])
        return gzip.decompress(raw).decode("utf-8")
    except Exception:
        return value


def _html_to_plain_text(value: str) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def _json_size_bytes(value: Any) -> int:
    try:
        return len(json.dumps(value, ensure_ascii=False).encode("utf-8"))
    except Exception:
        return 10**9


def _pick_marker_payload_by_size(
    full_marker: Dict[str, Any],
    compact_marker: Dict[str, Any],
    bare_marker: Dict[str, Any],
    max_bytes: int = 32000,
) -> Dict[str, Any]:
    """Pick the richest marker payload that fits Confluence content-property value limits."""
    if _json_size_bytes(full_marker) <= max_bytes:
        return full_marker
    if _json_size_bytes(compact_marker) <= max_bytes:
        return compact_marker
    return bare_marker


_DIFF_REFLECT_START = "<!-- DOC_AS_CODE_DIFF_REFLECTION_START -->"
_DIFF_REFLECT_END = "<!-- DOC_AS_CODE_DIFF_REFLECTION_END -->"
_HIGHLIGHT_CLEANUP_START = "<!-- DOC_AS_CODE_HIGHLIGHT_CLEANUP_START -->"
_HIGHLIGHT_CLEANUP_END = "<!-- DOC_AS_CODE_HIGHLIGHT_CLEANUP_END -->"



_INLINE_HIGHLIGHT_ATTR = 'data-dac="hl"'
_TEMP_DELETED_WARNING_TEXT = "Deleted from this page (temporary indicator, won't be saved):"


def _strip_inline_highlights(storage_html: str) -> str:
    """Remove any inline highlight spans injected by a previous reflect-on-page run.
    Unwraps <span data-dac="hl" ...>TEXT</span> → TEXT so the page is clean before re-compare."""
    html = str(storage_html or "")
    html = re.sub(
        re.escape(_HIGHLIGHT_CLEANUP_START) + r".*?" + re.escape(_HIGHLIGHT_CLEANUP_END),
        "",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    # Unwrap all spans that carry our marker attribute
    pattern = re.compile(
        r'<span\b[^>]*data-dac=["\']hl["\'][^>]*>(.*?)</span>',
        flags=re.DOTALL | re.IGNORECASE,
    )
    # Repeat until no more matches (handles nested edge cases)
    prev = None
    while prev != html:
        prev = html
        html = pattern.sub(r'\1', html)

    # Unwrap any temporary wrapper blocks created for media/tag-level highlighting.
    # Example: <div data-dac='hl' ...><ac:image>...</ac:image></div> -> <ac:image>...</ac:image>
    div_hl_pattern = re.compile(
        r'<div\b[^>]*data-dac=["\']hl["\'][^>]*>(.*?)</div>',
        flags=re.DOTALL | re.IGNORECASE,
    )
    prev = None
    while prev != html:
        prev = html
        html = div_hl_pattern.sub(r'\1', html)

    # Remove temporary deleted-indicator blocks that were injected only for preview.
    # These should never become part of baseline compare text.
    warning_text = "Deleted from this page (temporary indicator, won't be saved):"
    while True:
        warning_index = html.find(warning_text)
        if warning_index == -1:
            break
        start_index = html.rfind("<div", 0, warning_index)
        if start_index == -1:
            break

        depth = 0
        end_index = -1
        tag_pattern = re.compile(r"</?div\\b[^>]*>", flags=re.IGNORECASE)
        for match in tag_pattern.finditer(html, start_index):
            token = match.group(0).lower()
            if token.startswith("<div"):
                depth += 1
            elif token.startswith("</div"):
                depth -= 1
                if depth == 0:
                    end_index = match.end()
                    break
        if end_index == -1:
            break
        html = (html[:start_index] + html[end_index:]).strip()

    # Remove marker attribute while preserving structure/content.
    html = re.sub(r"\sdata-dac=(['\"])hl\1", "", html, flags=re.IGNORECASE)

    # Remove only temporary highlight style fragments, preserving original styles when present.
    def _strip_temp_style_fragments(match: re.Match) -> str:
        quote = match.group(1)
        style = str(match.group(2) or "")
        cleaned = style
        for token_pattern in cleanup_style_token_patterns():
            cleaned = re.sub(token_pattern, "", cleaned, flags=re.IGNORECASE)

        cleaned = re.sub(r"\s*;\s*", ";", cleaned).strip(" ;")
        if not cleaned:
            return ""
        return f" style={quote}{cleaned}{quote}"

    html = re.sub(r"\sstyle=(['\"])(.*?)\1", _strip_temp_style_fragments, html, flags=re.IGNORECASE | re.DOTALL)
    return html


def _add_project_to_path(project_root: str) -> None:
    if project_root not in sys.path:
        sys.path.insert(0, project_root)


def _summary_for_pair(previous_text: str, current_text: str, diff_lines: List[str]) -> Dict[str, Any]:
    previous_lines = len(previous_text.splitlines())
    current_lines = len(current_text.splitlines())

    lines_added = 0
    lines_removed = 0
    for line in diff_lines:
        if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
            continue
        if line.startswith("+"):
            lines_added += 1
        elif line.startswith("-"):
            lines_removed += 1

    return {
        "lines_previous": previous_lines,
        "lines_current": current_lines,
        "lines_added": lines_added,
        "lines_removed": lines_removed,
        "net_change": lines_added - lines_removed,
        "has_changes": bool(diff_lines),
    }


def _human_readable_diff(diff_lines: List[str], limit: int = 40) -> List[Dict[str, str]]:
    def _is_ignored_markup_line(text: str) -> bool:
        stripped = str(text or "").strip()
        if not stripped:
            return True
        if _TEMP_DELETED_WARNING_TEXT.lower() in stripped.lower():
            return True
        if re.match(r"^</?caption\b[^>]*>$", stripped, flags=re.IGNORECASE):
            return True
        # Suppress markdown-image-only churn in preview; image diffs are tracked elsewhere.
        if re.match(r"^!\[[^\]]*\]\([^)]*\)$", stripped):
            return True
        # Suppress heading-only churn in preview; often generated by markdown style conversions.
        if re.match(r"^#{1,6}\s+.+$", stripped):
            return True
        # Suppress standalone title-like heading text churn (e.g., "Access Polices").
        if re.match(r"^[A-Z][A-Za-z0-9'/-]*(?:\s+[A-Z][A-Za-z0-9'/-]*){0,5}$", stripped):
            return True
        return False

    def _humanize_markdown_text(text: str) -> str:
        cleaned = str(text or "")
        cleaned = cleaned.replace("\\n", " ")
        cleaned = re.sub(r"\\", "", cleaned)
        cleaned = re.sub(r"^\s{0,3}#{1,6}\s+", "", cleaned)
        cleaned = re.sub(r"^\s*[-*]\s+", "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    readable: List[Dict[str, str]] = []
    for line in diff_lines:
        if line.startswith("@@"):
            continue
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            text = _humanize_markdown_text(line[1:])
            if text and not _is_ignored_markup_line(text):
                readable.append({"type": "added", "text": text})
            continue
        if line.startswith("-"):
            text = _humanize_markdown_text(line[1:])
            if text and not _is_ignored_markup_line(text):
                readable.append({"type": "deleted", "text": text})
            continue
        if line.startswith(" "):
            text = _humanize_markdown_text(line[1:])
            if text and not _is_ignored_markup_line(text):
                readable.append({"type": "context", "text": text})

        if len(readable) >= limit:
            break

    # Suppress formatting-only churn where the same semantic content appears
    # as one delete + one add due to markdown/render normalization differences.
    # Keep truly changed rows while removing false noisy pairs.
    added_counter = Counter(
        _normalize_compare_text(item.get("text", ""))
        for item in readable
        if item.get("type") == "added" and _normalize_compare_text(item.get("text", ""))
    )
    deleted_counter = Counter(
        _normalize_compare_text(item.get("text", ""))
        for item in readable
        if item.get("type") == "deleted" and _normalize_compare_text(item.get("text", ""))
    )
    cancel_counter = Counter()
    for key in set(added_counter) & set(deleted_counter):
        cancel_counter[key] = min(added_counter[key], deleted_counter[key])

    if not cancel_counter:
        return readable

    filtered: List[Dict[str, str]] = []
    canceled_added = Counter()
    canceled_deleted = Counter()
    for item in readable:
        item_type = str(item.get("type") or "")
        if item_type not in {"added", "deleted"}:
            filtered.append(item)
            continue

        key = _normalize_compare_text(item.get("text", ""))
        if not key or cancel_counter.get(key, 0) <= 0:
            filtered.append(item)
            continue

        if item_type == "added" and canceled_added[key] < cancel_counter[key]:
            canceled_added[key] += 1
            continue
        if item_type == "deleted" and canceled_deleted[key] < cancel_counter[key]:
            canceled_deleted[key] += 1
            continue

        filtered.append(item)

    return filtered


def _print_simple_readable_changes(title: str, changes: Dict[str, Any], limit: int = 12) -> None:
    added = [str(x).strip() for x in (changes.get("added") or []) if str(x).strip()]
    deleted = [str(x).strip() for x in (changes.get("deleted") or []) if str(x).strip()]

    for pair in (changes.get("replaced") or []):
        old_text = str((pair or {}).get("from") or "").strip()
        new_text = str((pair or {}).get("to") or "").strip()
        if new_text:
            added.append(new_text)
        if old_text:
            deleted.append(old_text)

    def _dedupe(lines: List[str]) -> List[str]:
        out: List[str] = []
        seen = set()
        for line in lines:
            raw = str(line or "").strip()
            if re.match(r"^\s*#{1,6}\s+.+$", raw):
                continue
            if re.match(r"^\s*!\[[^\]]*\]\([^)]*\)\s*$", raw):
                continue
            key = _normalize_compare_text(line)
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(line)
        return out

    added = _dedupe(added)
    deleted = _dedupe(deleted)

    print(f"\n=== {title} ===")
    if not added and not deleted:
        print("No meaningful content differences.")
        return

    if added:
        print("Added:")
        for line in added[:limit]:
            print(f"  + {line}")
        if len(added) > limit:
            print(f"  ... and {len(added) - limit} more added lines")

    if deleted:
        print("Deleted:")
        for line in deleted[:limit]:
            print(f"  - {line}")
        if len(deleted) > limit:
            print(f"  ... and {len(deleted) - limit} more deleted lines")


def _build_update_preview_overlay(
    added_lines: List[str],
    deleted_lines: List[str],
    replaced_lines: Optional[List[Dict[str, str]]] = None,
    limit: int = 40,
) -> str:
    # Keep page reflection minimally intrusive: only inline highlights on page.
    # Do not append a large preview block to the page body.
    return ""

    """Build an explicit color-coded preview block for client readability.
    This supplements inline highlights so updated/replaced/deleted lines are always visible."""

    def _clean(lines: List[str]) -> List[str]:
        items: List[str] = []
        for line in lines:
            text = str(line or "").strip()
            if not text:
                continue
            if _TEMP_DELETED_WARNING_TEXT.lower() in text.lower():
                continue
            if re.match(r"^</?caption\b[^>]*>$", text, flags=re.IGNORECASE):
                continue
            items.append(text)
        return items

    added = _clean(added_lines)
    deleted = _clean(deleted_lines)
    replaced = [x for x in (replaced_lines or []) if str((x or {}).get("from") or "").strip() or str((x or {}).get("to") or "").strip()]
    if not added and not deleted and not replaced:
        return ""

    block_parts: List[str] = []
    block_parts.append(_DIFF_REFLECT_START)
    block_parts.append(
        "<div data-dac='reflect-block' style='margin:12px 0;padding:6px 0;border:0;background:transparent;'>"
    )

    if added:
        for line in added[:limit]:
            xhtml = _line_to_safe_reflection_xhtml(line)
            if not xhtml:
                continue
            block_parts.append(
                "<div data-dac='hl' style='background-color:#e3f2fd;color:#0d47a1;border-left:3px solid #1e88e5;padding:4px 6px;margin:2px 0;'>"
                f"{xhtml}</div>"
            )
        if len(added) > limit:
            block_parts.append(f"<div style='color:#546e7a;'>... and {len(added) - limit} more added/updated lines</div>")

    if replaced:
        for pair in replaced[:limit]:
            from_xhtml = _line_to_safe_reflection_xhtml(str((pair or {}).get("from") or ""))
            to_xhtml = _line_to_safe_reflection_xhtml(str((pair or {}).get("to") or ""))
            if from_xhtml:
                block_parts.append(
                    "<div data-dac='hl' style='background-color:#fff8e1;color:#8a6d00;border-left:3px solid #f9a825;padding:4px 6px;margin:2px 0;'>"
                    f"<div style='text-decoration:line-through;text-decoration-thickness:2px;'>{from_xhtml}</div></div>"
                )
            if to_xhtml:
                block_parts.append(
                    "<div data-dac='hl' style='background-color:#fff8e1;color:#8a6d00;border-left:3px solid #f9a825;padding:4px 6px;margin:2px 0;'>"
                    f"{to_xhtml}</div>"
                )
        if len(replaced) > limit:
            block_parts.append(f"<div style='color:#546e7a;'>... and {len(replaced) - limit} more replaced lines</div>")

    if deleted:
        for line in deleted[:limit]:
            xhtml = _line_to_safe_reflection_xhtml(line)
            if not xhtml:
                continue
            block_parts.append(
                "<div data-dac='hl' style='background-color:#ffebee;color:#b71c1c;border-left:3px solid #e53935;padding:4px 6px;margin:2px 0;'>"
                f"<div style='text-decoration:line-through;text-decoration-thickness:2px;'>{xhtml}</div></div>"
            )
        if len(deleted) > limit:
            block_parts.append(f"<div style='color:#546e7a;'>... and {len(deleted) - limit} more deleted lines</div>")

    block_parts.append("</div>")
    block_parts.append(_DIFF_REFLECT_END)
    return "".join(block_parts)


def _build_compare_block(
    before_text: Optional[str],
    after_text: Optional[str],
    title: str,
    context_lines: int,
    mode: str,
) -> Dict[str, Any]:
    if before_text is None or after_text is None:
        return {
            "available": False,
            "summary": None,
            "diff_lines": [],
        }

    diff_lines = build_diff(
        before_text=before_text,
        after_text=after_text,
        title=title,
        context=context_lines,
        mode=mode,
    )
    return {
        "available": True,
        "summary": _summary_for_pair(before_text, after_text, diff_lines),
        "diff_lines": diff_lines,
    }


def _persist_last_reflection_hash(
    client: Any,
    page_id: str,
    marker_key: str,
    marker: Optional[Dict[str, Any]],
    live_hash: str,
) -> bool:
    """Store last reflected live hash so repeated checks don't re-highlight old reviewed edits."""
    if not marker:
        return False
    try:
        updated_marker = dict(marker)
        updated_marker["last_reflection_live_hash"] = str(live_hash)
        updated_marker["last_reflection_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        return bool(upsert_page_marker(client, str(page_id), str(marker_key), updated_marker))
    except Exception:
        return False


def _choose_override(force_override: bool, prompt_override: bool) -> bool:
    if force_override:
        return True
    if not prompt_override:
        return False

    answer = input("⚠️ Direct online edits detected. Override and proceed as allowed? (y/n): ").strip().lower()
    return answer in {"y", "yes"}


def _confirm_override_before_update(
    drift: bool,
    yes_override: bool,
    override_already_confirmed: bool,
) -> bool:
    """
    Ask user to explicitly confirm override when drift is detected.
    This is a safety gate even when --force-scdp-override is used.
    Only skip prompt if --yes-override flag is passed.
    """
    if not drift:
        return True
    if override_already_confirmed:
        return True
    if yes_override:
        return True

    print("\n⚠️⚠️⚠️ OVERRIDE CONFIRMATION REQUIRED ⚠️⚠️⚠️")
    print("Direct manual SCDP edits were detected since last Doc-as-Code publish.")
    print("You are about to OVERWRITE those manual edits with local markdown.")
    answer = input("\nAre you 100% sure you want to continue with this override? (y/n): ").strip().lower()
    return answer in {"y", "yes"}


def _choose_update(yes: bool, quiet_output: bool = False) -> bool:
    if yes:
        return True
    # In quiet mode with piped stdin, avoid printing prompt text so output remains minimal.
    if quiet_output and not sys.stdin.isatty():
        answer = (sys.stdin.readline() or "").strip().lower()
    else:
        answer = input("✅ Compare completed. Update this SCDP page now? (y/n): ").strip().lower()
    return answer in {"y", "yes"}


def _resolve_heading_title(
    sections: List[Dict[str, Any]],
    requested_title: str,
    no_prompt_missing_heading: bool,
) -> Optional[Dict[str, Any]]:
    requested = requested_title.strip().lower()
    exact = next(
        (
            section
            for section in sections
            if str(section.get("path_key") or "").strip().lower() == requested
            or str(section.get("title", "")).strip().lower() == requested
        ),
        None,
    )
    if exact is not None:
        return exact

    if no_prompt_missing_heading:
        return None

    available = [str(section.get("path_key") or section.get("title", "")).strip() for section in sections]
    print("\n⚠️ Requested heading not found in local markdown file.")
    print(f"Requested: {requested_title}")
    print("Available headings:")
    for idx, title in enumerate(available, start=1):
        print(f"  {idx}. {title}")

    entered = input("Enter exact heading title to use (or press Enter to cancel): ").strip()
    if not entered:
        return None

    return next(
        (
            section
            for section in sections
            if str(section.get("path_key") or "").strip().lower() == entered.lower()
            or str(section.get("title", "")).strip().lower() == entered.lower()
        ),
        None,
    )


def _split_heading_path(value: str) -> List[str]:
    return [part.strip() for part in str(value or "").split(_HEADING_PATH_SEPARATOR) if part.strip()]


def _normalize_heading_match_key(value: str) -> str:
    cleaned = html.unescape(str(value or ""))
    # Strip inline-comment-marker tags but preserve their visible text so
    # headings wrapped by preserved comments still resolve to the same section.
    cleaned = re.sub(r"</?ac:inline-comment-marker\b[^>]*>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    # Remove zero-width space characters that may be injected as fallback anchors
    cleaned = cleaned.replace("\u200b", "").replace("&#8203;", "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
    return cleaned


def _relax_heading_match_key(value: str) -> str:
    cleaned = _normalize_heading_match_key(value)
    if not cleaned:
        return cleaned
    # Drop leading numbering and punctuation (for example "1.2 Heading" -> "heading").
    cleaned = re.sub(r"^[\W_]*\d+(?:[\.-]\d+)*[\)\.-:]*\s*", "", cleaned)
    cleaned = re.sub(r"^[\W_]+", "", cleaned)
    return cleaned.strip().lower()


def _find_heading_section_bounds(
    storage_html: str,
    heading_title: str,
    heading_level: Optional[int] = None,
) -> Optional[Dict[str, int]]:
    """Find the body span for a heading section in storage HTML.

    Returns a dict with:
    - heading_start: start index of matching heading tag
    - body_start: first index after heading close tag
    - section_end: next heading start or end of document
    """
    html_text = str(storage_html or "")
    target_path = _split_heading_path(heading_title)
    target = _normalize_heading_match_key(target_path[-1] if target_path else heading_title)
    if not html_text or not target:
        return None

    heading_re = re.compile(r"<(h[1-6])\b[^>]*>(.*?)</\1>", re.IGNORECASE | re.DOTALL)
    matches = list(heading_re.finditer(html_text))
    if not matches:
        return None

    path_stack: List[Tuple[int, str, str]] = []
    candidate_paths: List[List[str]] = []
    relaxed_candidate_paths: List[List[str]] = []
    for match in matches:
        current_level = int(match.group(1)[1:])
        heading_text = _normalize_heading_match_key(match.group(2))
        relaxed_heading_text = _relax_heading_match_key(match.group(2))
        while path_stack and int(path_stack[-1][0]) >= current_level:
            path_stack.pop()
        path_stack.append((current_level, heading_text, relaxed_heading_text))
        candidate_paths.append([item[1] for item in path_stack])
        relaxed_candidate_paths.append([item[2] for item in path_stack])

    normalized_target_path = [_normalize_heading_match_key(part) for part in target_path] if target_path else []

    for idx, match in enumerate(matches):
        current_level = int(match.group(1)[1:])
        if heading_level is not None and current_level != heading_level:
            continue
        heading_text = _normalize_heading_match_key(match.group(2))
        if heading_text != target:
            continue
        if normalized_target_path and candidate_paths[idx] != normalized_target_path:
            continue
        heading_start = match.start()
        body_start = match.end()
        section_end = len(html_text)
        for later_match in matches[idx + 1:]:
            later_level = int(later_match.group(1)[1:])
            if later_level <= current_level:
                section_end = later_match.start()
                break
        if section_end < body_start:
            return None
        return {
            "heading_start": heading_start,
            "body_start": body_start,
            "section_end": section_end,
        }

    relaxed_target = _relax_heading_match_key(target_path[-1] if target_path else heading_title)
    if not relaxed_target or relaxed_target == target:
        return None
    relaxed_target_path = [_relax_heading_match_key(part) for part in target_path] if target_path else []

    relaxed_matches: List[Tuple[int, Any]] = []
    for idx, match in enumerate(matches):
        current_level = int(match.group(1)[1:])
        if heading_level is not None and current_level != heading_level:
            continue
        heading_text = _relax_heading_match_key(match.group(2))
        if heading_text == relaxed_target:
            if relaxed_target_path and relaxed_candidate_paths[idx] != relaxed_target_path:
                continue
            relaxed_matches.append((idx, match))

    if len(relaxed_matches) != 1:
        return None

    idx, match = relaxed_matches[0]
    current_level = int(match.group(1)[1:])
    heading_start = match.start()
    body_start = match.end()
    section_end = len(html_text)
    for later_match in matches[idx + 1:]:
        later_level = int(later_match.group(1)[1:])
        if later_level <= current_level:
            section_end = later_match.start()
            break
    if section_end < body_start:
        return None
    return {
        "heading_start": heading_start,
        "body_start": body_start,
        "section_end": section_end,
    }


def _replace_heading_section_body(
    storage_html: str,
    heading_title: str,
    new_body_html: str,
    heading_level: Optional[int] = None,
) -> Optional[str]:
    bounds = _find_heading_section_bounds(storage_html, heading_title, heading_level=heading_level)
    if bounds is None:
        return None
    body_start = int(bounds["body_start"])
    section_end = int(bounds["section_end"])
    return storage_html[:body_start] + str(new_body_html or "") + storage_html[section_end:]


def _normalize_anchor_macro_name(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(value or ""))).strip().lower()


def _iter_anchor_macro_blocks(storage_html: str) -> List[Dict[str, Any]]:
    html_text = str(storage_html or "")
    paragraph_re = re.compile(
        r"<p\b[^>]*>\s*(<ac:structured-macro\b[^>]*ac:name=(['\"])anchor\2[^>]*>.*?<ac:parameter\b[^>]*>(.*?)</ac:parameter>.*?</ac:structured-macro>)\s*</p>",
        flags=re.IGNORECASE | re.DOTALL,
    )
    raw_re = re.compile(
        r"<ac:structured-macro\b[^>]*ac:name=(['\"])anchor\1[^>]*>.*?<ac:parameter\b[^>]*>(.*?)</ac:parameter>.*?</ac:structured-macro>",
        flags=re.IGNORECASE | re.DOTALL,
    )

    blocks: List[Dict[str, Any]] = []
    for match in paragraph_re.finditer(html_text):
        blocks.append(
            {
                "start": match.start(),
                "end": match.end(),
                "anchor_name": _normalize_anchor_macro_name(_html_to_plain_text(match.group(3))),
            }
        )
    if blocks:
        return blocks

    for match in raw_re.finditer(html_text):
        blocks.append(
            {
                "start": match.start(),
                "end": match.end(),
                "anchor_name": _normalize_anchor_macro_name(_html_to_plain_text(match.group(2))),
            }
        )
    return blocks


def _find_anchor_region_bounds(
    storage_html: str,
    start_anchor_name: str,
    end_anchor_name: str,
) -> Optional[Dict[str, int]]:
    start_name = _normalize_anchor_macro_name(start_anchor_name)
    end_name = _normalize_anchor_macro_name(end_anchor_name)
    if not storage_html or not start_name or not end_name:
        return None

    blocks = _iter_anchor_macro_blocks(storage_html)
    start_block = next((block for block in blocks if block.get("anchor_name") == start_name), None)
    if start_block is None:
        return None

    end_block = next(
        (
            block
            for block in blocks
            if block.get("anchor_name") == end_name and int(block.get("start") or 0) >= int(start_block.get("end") or 0)
        ),
        None,
    )
    if end_block is None:
        return None

    return {
        "heading_start": int(start_block.get("start") or 0),
        "body_start": int(start_block.get("end") or 0),
        "section_end": int(end_block.get("start") or 0),
    }


def _replace_anchor_region_body(
    storage_html: str,
    new_body_html: str,
    start_anchor_name: str,
    end_anchor_name: str,
) -> Optional[str]:
    bounds = _find_anchor_region_bounds(storage_html, start_anchor_name, end_anchor_name)
    if bounds is None:
        return None
    body_start = int(bounds["body_start"])
    section_end = int(bounds["section_end"])
    return storage_html[:body_start] + str(new_body_html or "") + storage_html[section_end:]


def _build_user_page_url(base_url: str, webui_path: str, page_id: str) -> str:
    base = str(base_url or "").rstrip("/")
    base = re.sub(r"/rest/api/?$", "", base, flags=re.IGNORECASE)
    webui = str(webui_path or "").strip()
    if webui and not webui.startswith("/"):
        webui = "/" + webui

    # Keep only user-facing web paths; fall back to canonical view URL otherwise.
    if webui.startswith("/spaces/") or webui.startswith("/pages/"):
        return base + webui
    return f"{base}/pages/viewpage.action?pageId={page_id}"


def _get_page_with_retry(client, page_id: str, attempts: int = 2, delay_seconds: float = 2.0):
    """Small script-level retry wrapper for transient network/auth hiccups."""
    page = None
    for attempt in range(1, attempts + 1):
        page = client.get_page(str(page_id))
        if page:
            return page
        if attempt < attempts and delay_seconds > 0:
            time.sleep(delay_seconds)
    return page


def _strip_existing_diff_reflection_block(storage_html: str) -> str:
    html_text = storage_html or ""
    pattern = re.compile(
        re.escape(_DIFF_REFLECT_START) + r".*?" + re.escape(_DIFF_REFLECT_END),
        flags=re.DOTALL,
    )
    stripped = pattern.sub("", html_text).strip()

    # Remove temporary reflection wrapper blocks, including nested children.
    reflect_start_pattern = re.compile(
        r"<div\b[^>]*data-dac=(['\"])reflect-block\1[^>]*>",
        flags=re.IGNORECASE,
    )
    div_tag_pattern = re.compile(r"</?div\b[^>]*>", flags=re.IGNORECASE)
    while True:
        reflect_match = reflect_start_pattern.search(stripped)
        if not reflect_match:
            break

        start_index = reflect_match.start()
        depth = 0
        end_index = -1
        for div_match in div_tag_pattern.finditer(stripped, start_index):
            token = div_match.group(0).lower()
            if token.startswith("<div"):
                depth += 1
            elif token.startswith("</div"):
                depth -= 1
                if depth == 0:
                    end_index = div_match.end()
                    break

        if end_index == -1:
            break

        stripped = (stripped[:start_index] + stripped[end_index:]).strip()

    # Fallback path: Confluence may sanitize/remove HTML comments, which means
    # marker comments are gone. In that case remove the reflection container
    # by locating the known title text and deleting its wrapping <div> block.
    title_text = "Temporary Compare Reflection"
    while True:
        title_index = stripped.find(title_text)
        if title_index == -1:
            break

        start_index = stripped.rfind("<div", 0, title_index)
        if start_index == -1:
            break

        depth = 0
        scan_index = start_index
        end_index = -1
        tag_pattern = re.compile(r"</?div\b[^>]*>", flags=re.IGNORECASE)
        for match in tag_pattern.finditer(stripped, start_index):
            token = match.group(0).lower()
            if token.startswith("<div"):
                depth += 1
            elif token.startswith("</div"):
                depth -= 1
                if depth == 0:
                    end_index = match.end()
                    break
            scan_index = match.end()

        if end_index == -1:
            break

        stripped = (stripped[:start_index] + stripped[end_index:]).strip()

    # Legacy fallback: older preview runs appended helper sections near the end
    # of the document without stable markers. Remove that appended tail by
    # detecting known helper labels and trimming from the containing <div> onward.
    legacy_labels = [
        "⚠️ Deleted from thiss page (temporary indicator, won't be saved):",
        "⚠️ Deleted from this page (temporary indicator, won't be saved):",
        "Client view: update preview (easy readable)",
        "Added / Updated (Green)",
        "Replaced (Yellow)",
    ]
    legacy_indexes = [idx for idx in (stripped.find(label) for label in legacy_labels) if idx != -1]
    if legacy_indexes:
        legacy_start = min(legacy_indexes)
        wrapper_start = stripped.rfind("<div><div", 0, legacy_start)
        if wrapper_start != -1:
            stripped = stripped[:wrapper_start].rstrip()
        else:
            div_start = stripped.rfind("<div", 0, legacy_start)
            if div_start != -1:
                stripped = stripped[:div_start].rstrip()

    # Additional fallback: Confluence may normalize styles and remove title text
    # while keeping the reflected container at the top of the document.
    # Detect and remove leading reflection container by style signature.
    leading_reflect_pattern = re.compile(
        r'^\s*<div\s+style="[^"]*(?:#bbdefb|rgb\(187,222,251\))[^"]*">',
        flags=re.IGNORECASE,
    )
    div_tag_pattern = re.compile(r"</?div\b[^>]*>", flags=re.IGNORECASE)
    while True:
        match = leading_reflect_pattern.search(stripped)
        if not match:
            break

        start_index = match.start()
        depth = 0
        end_index = -1
        for div_match in div_tag_pattern.finditer(stripped, start_index):
            token = div_match.group(0).lower()
            if token.startswith("<div"):
                depth += 1
            elif token.startswith("</div"):
                depth -= 1
                if depth == 0:
                    end_index = div_match.end()
                    break

        if end_index == -1:
            break

        stripped = (stripped[:start_index] + stripped[end_index:]).strip()

    return stripped


def _render_reflection_line(line: str, style: str) -> str:
    def _humanize_markdown_text(text: str) -> str:
        cleaned = str(text or "")
        cleaned = cleaned.replace("\\n", " ")
        cleaned = re.sub(r"\\", "", cleaned)
        cleaned = re.sub(r"^\s{0,3}#{1,6}\s+", "", cleaned)
        cleaned = re.sub(r"^\s*[-*]\s+", "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    raw_line = str(line or "")
    human_text = _humanize_markdown_text(raw_line[1:] if raw_line[:1] in {"+", "-", " "} else raw_line)
    escaped = (
        human_text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

    # style=server : blue manual server edits
    # style=normal : green additions / red deletions
    # style=override_add : blue additions / red deletions for override preview
    if line.startswith("+"):
        if not escaped:
            return ""
        if style == "server":
            return (
                "<div style='background:#e3f2fd;color:#0d47a1;padding:3px 6px;border-left:3px solid #1e88e5;'>"
                f"✎ {escaped}</div>"
            )
        if style == "override_add":
            return (
                "<div style='background:#e3f2fd;color:#0d47a1;padding:3px 6px;border-left:3px solid #1e88e5;'>"
                f"✎ {escaped}</div>"
            )
        return (
            "<div style='background:#e3f2fd;color:#0d47a1;padding:3px 6px;border-left:3px solid #1e88e5;'>"
            f"Added: {escaped}</div>"
        )
    if line.startswith("-"):
        if not escaped:
            return ""
        if style == "server":
            return (
                "<div style='background:#e3f2fd;color:#0d47a1;padding:3px 6px;border-left:3px solid #1e88e5;'>"
                f"✎ {escaped}</div>"
            )
        return (
            "<div style='background:#ffebee;color:#b71c1c;padding:3px 6px;border-left:3px solid #e53935;'>"
            f"Removed: <span style='text-decoration:line-through;text-decoration-thickness:2px;'>{escaped}</span></div>"
        )
    if line.startswith("@@"):
        return ""
    if not escaped:
        return ""
    return f"<div style='padding:3px 6px;color:#666;'>{escaped}</div>"


def _tokenize_for_word_diff(text: str) -> List[str]:
    return re.findall(r"\S+|\s+", text or "")


def _render_word_level_pair(old_text: str, new_text: str, add_style: str) -> Dict[str, str]:
    old_tokens = _tokenize_for_word_diff(old_text)
    new_tokens = _tokenize_for_word_diff(new_text)
    matcher = difflib.SequenceMatcher(a=old_tokens, b=new_tokens)

    old_parts: List[str] = []
    new_parts: List[str] = []

    if add_style == "override":
        add_span_style = "background:#e3f2fd;color:#0d47a1;padding:0 2px;border-radius:2px;"
    else:
        add_span_style = "background:#e3f2fd;color:#0d47a1;padding:0 2px;border-radius:2px;"

    del_span_style = "background:#ffebee;color:#b71c1c;padding:0 2px;border-radius:2px;text-decoration:line-through;text-decoration-thickness:2px;"

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        old_chunk = "".join(old_tokens[i1:i2])
        new_chunk = "".join(new_tokens[j1:j2])
        old_escaped = (
            old_chunk.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )
        new_escaped = (
            new_chunk.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )

        if tag == "equal":
            old_parts.append(old_escaped)
            new_parts.append(new_escaped)
        else:
            if old_chunk:
                old_parts.append(f"<span style='{del_span_style}'>{old_escaped}</span>")
            if new_chunk:
                new_parts.append(f"<span style='{add_span_style}'>{new_escaped}</span>")

    return {
        "old": "".join(old_parts),
        "new": "".join(new_parts),
    }


def _render_reflection_pair(old_line: str, new_line: str, add_style: str) -> List[str]:
    def _humanize_markdown_text(text: str) -> str:
        cleaned = str(text or "")
        cleaned = cleaned.replace("\\n", " ")
        cleaned = re.sub(r"\\", "", cleaned)
        cleaned = re.sub(r"^\s{0,3}#{1,6}\s+", "", cleaned)
        cleaned = re.sub(r"^\s*[-*]\s+", "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    old_text = old_line[1:] if old_line.startswith("-") else old_line
    new_text = new_line[1:] if new_line.startswith("+") else new_line
    old_text = _humanize_markdown_text(old_text)
    new_text = _humanize_markdown_text(new_text)
    word_level = _render_word_level_pair(old_text, new_text, add_style=add_style)

    if add_style == "override":
        add_container = "background:#e3f2fd;color:#0d47a1;padding:3px 6px;border-left:3px solid #1e88e5;"
        add_prefix = "Updated: "
    else:
        add_container = "background:#e3f2fd;color:#0d47a1;padding:3px 6px;border-left:3px solid #1e88e5;"
        add_prefix = "Added: "

    return [
        (
            "<div style='background:#ffebee;color:#b71c1c;padding:3px 6px;border-left:3px solid #e53935;'>"
            f"Removed: <span style='text-decoration:line-through;text-decoration-thickness:2px;'>{word_level['old']}</span></div>"
        ),
        (
            f"<div style='{add_container}'>{add_prefix}{word_level['new']}</div>"
        ),
    ]


def _append_reflection_lines(body_parts: List[str], lines: List[str], style: str) -> None:
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        next_line = lines[idx + 1] if idx + 1 < len(lines) else None

        if line.startswith("-") and next_line and next_line.startswith("+") and style in {"normal", "override"}:
            body_parts.extend(_render_reflection_pair(line, next_line, add_style=style))
            idx += 2
            continue

        rendered = _render_reflection_line(
            line,
            style="server" if style == "server" else ("normal" if style == "normal" else "override_add"),
        )
        if rendered:
            body_parts.append(rendered)
        idx += 1


def _lines_for_reflection(diff_lines: List[str], changes_only: bool) -> List[str]:
    if not diff_lines:
        return []
    if not changes_only:
        return [line for line in diff_lines if not (line.startswith("+++") or line.startswith("---"))]
    selected: List[str] = []
    for line in diff_lines:
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+") or line.startswith("-"):
            selected.append(line)
    return selected


def _wrap_highlight_html(inner_html: str, style: str) -> str:
    if not inner_html.strip():
        return ""

    if style == "override":
        return (
            "<div style='background:#e3f2fd;color:#0d47a1;border-left:3px solid #1e88e5;padding:2px 8px;margin:2px 0;'>"
            f"{inner_html}</div>"
        )

    if style == "added":
        return (
            "<div style='background:#e3f2fd;color:#0d47a1;border-left:3px solid #1e88e5;padding:2px 8px;margin:2px 0;'>"
            f"{inner_html}</div>"
        )

    if style == "deleted":
        return (
            "<div style='background:#ffebee;color:#b71c1c;border-left:3px solid #e53935;padding:2px 8px;margin:2px 0;'>"
            f"<div style='text-decoration:line-through;text-decoration-thickness:2px;'>{inner_html}</div></div>"
        )

    return inner_html


def _line_to_safe_reflection_xhtml(line_text: str) -> str:
    """Build strict safe XHTML for reflection to avoid Confluence storage parse errors."""
    text = str(line_text or "").strip()
    if not text:
        return ""

    def _escape(value: str) -> str:
        return (
            str(value or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    # TODO: Image highlighting deferred - skip image lines for now
    image_match = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", text)
    if image_match:
        return ""

    heading_match = re.match(r"^(#{1,6})\s+(.+?)\s*$", text)
    if heading_match:
        level = len(heading_match.group(1))
        title = _escape(heading_match.group(2).strip())
        return f"<h{level}>{title}</h{level}>"

    bullet_match = re.match(r"^[-*+]\s+(.+?)\s*$", text)
    if bullet_match:
        item = _escape(bullet_match.group(1).strip())
        return f"<ul><li>{item}</li></ul>"

    ordered_match = re.match(r"^\d+\.\s+(.+?)\s*$", text)
    if ordered_match:
        item = _escape(ordered_match.group(1).strip())
        return f"<ol><li>{item}</li></ol>"

    escaped = _escape(text)
    return f"<p>{escaped}</p>"


def _normalize_compare_text(text: str) -> str:
    cleaned = str(text or "")
    if _TEMP_DELETED_WARNING_TEXT.lower() in cleaned.lower():
        return ""
    cleaned = html.unescape(cleaned)
    # Ignore caption wrapper tags from markdown conversion noise.
    if re.match(r"^\s*</?caption\b[^>]*>\s*$", cleaned, flags=re.IGNORECASE):
        return ""
    # Ignore fenced-code markers (``` / ```yaml / ~~~) which often differ only by language tag.
    if re.match(r"^\s*(?:```|~~~)\s*[^`~]*\s*$", cleaned):
        return ""
    # Ignore setext heading underline markers (--- / ===).
    if re.match(r"^\s*(?:-{3,}|={3,})\s*$", cleaned):
        return ""
    # Unescape markdown escaped characters so comparisons match rendered text.
    cleaned = re.sub(r"\\([\\`*_{}\[\]()#+\-.!|])", r"\1", cleaned)
    # Strip block-level markdown markers
    cleaned = re.sub(r"^\s{0,3}#{1,6}\s+", "", cleaned)
    # Normalize list bullets across markdown converters:
    #   * item / - item / + item / -* item / +- item / -+ item
    cleaned = re.sub(r"^\s*(?:[-*+]\s+|[-*+]{2,}\s*)", "", cleaned)
    cleaned = re.sub(r"^\s*\d+\.\s+", "", cleaned)
    # Strip inline markdown so storage-to-markdown conversion noise is ignored:
    # [link text](url) → link text
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", cleaned)
    # ![alt](path) → alt (ignore path-only churn)
    cleaned = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", cleaned)
    # **bold** / __bold__ → text
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"__([^_]+)__", r"\1", cleaned)
    # *italic* / _italic_ → text (only when markers are not part of words like snake_case)
    cleaned = re.sub(r"(?<!\w)\*([^*\n]+)\*(?!\w)", r"\1", cleaned)
    cleaned = re.sub(r"(?<!\w)_([^_\n]+)_(?!\w)", r"\1", cleaned)
    # `code` → text
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    # Normalise emphasis marker churn from markdown/storage conversions:
    # examples: ACC*ESXI*10G*IPG vs ACC_ESXI_10G_IPG
    cleaned = re.sub(r"[*_]+", " ", cleaned)
    # Normalise whitespace and case
    cleaned = " ".join(cleaned.split()).strip().lower()
    return cleaned


def _normalize_markdown_document_for_semantic_compare(markdown_text: str) -> str:
    lines = (markdown_text or "").splitlines()
    normalized_lines: List[str] = []

    for raw in lines:
        text = str(raw or "").strip()
        if not text:
            continue
        if re.match(r"^\s*#{1,6}\s+", text):
            # Ignore heading wrapper differences (local content often prepends heading).
            continue
        if re.match(r"^\s*(```|~~~)", text):
            continue
        if re.match(r"^[|:\- ]+$", text):
            continue
        if re.match(r"^</?caption\b[^>]*>$", text, flags=re.IGNORECASE):
            continue

        normalized = _normalize_compare_text(text)
        if normalized:
            normalized = normalized.replace("\\", "")
            normalized_lines.append(normalized)

    return "\n".join(normalized_lines)


def _collect_net_changes(previous_markdown: str, current_markdown: str) -> Dict[str, Any]:
    def _is_partial_edit(old_norm: str, new_norm: str) -> bool:
        if not old_norm or not new_norm:
            return False
        old_words = old_norm.split()
        new_words = new_norm.split()
        if not old_words or not new_words:
            return False
        common_count = 0
        for index in range(min(len(old_words), len(new_words))):
            if old_words[index] == new_words[index]:
                common_count += 1
            else:
                break
        return common_count >= 1 and (common_count < len(old_words) or common_count < len(new_words))

    def _word_overlap_ratio(old_norm: str, new_norm: str) -> float:
        old_words = set((old_norm or "").split())
        new_words = set((new_norm or "").split())
        if not old_words or not new_words:
            return 0.0
        shared = old_words & new_words
        return len(shared) / float(min(len(old_words), len(new_words)))

    def _collect_normalized_map(lines: List[str]) -> Dict[str, List[str]]:
        mapped: Dict[str, List[str]] = {}
        for raw in lines:
            norm = _normalize_compare_text(raw)
            if not norm:
                continue
            mapped.setdefault(norm, []).append(raw)
        return mapped

    previous_lines = (previous_markdown or "").splitlines()
    current_lines = (current_markdown or "").splitlines()
    prev_map = _collect_normalized_map(previous_lines)
    curr_map = _collect_normalized_map(current_lines)

    unmatched_deleted: List[Dict[str, str]] = []
    unmatched_added: List[Dict[str, str]] = []

    for norm, old_values in prev_map.items():
        new_values = curr_map.get(norm, [])
        common_count = min(len(old_values), len(new_values))
        for item in old_values[common_count:]:
            unmatched_deleted.append({"raw": item, "norm": norm})

    for norm, new_values in curr_map.items():
        old_values = prev_map.get(norm, [])
        common_count = min(len(old_values), len(new_values))
        for item in new_values[common_count:]:
            unmatched_added.append({"raw": item, "norm": norm})

    replaced_lines: List[Dict[str, str]] = []
    deleted_lines: List[str] = []
    added_lines: List[str] = []

    used_added_indexes: set[int] = set()
    for deleted_item in unmatched_deleted:
        old_norm = deleted_item["norm"]
        best_index = -1
        best_score = 0.0

        for add_index, added_item in enumerate(unmatched_added):
            if add_index in used_added_indexes:
                continue
            new_norm = added_item["norm"]
            similarity = difflib.SequenceMatcher(a=old_norm, b=new_norm).ratio() if (old_norm or new_norm) else 0.0
            overlap = _word_overlap_ratio(old_norm, new_norm)
            partial = _is_partial_edit(old_norm, new_norm)
            score = max(similarity, overlap)
            if partial:
                score = max(score, 0.60)
            if score > best_score:
                best_score = score
                best_index = add_index

        if best_index != -1 and best_score >= 0.45:
            used_added_indexes.add(best_index)
            replaced_lines.append({"from": deleted_item["raw"], "to": unmatched_added[best_index]["raw"]})
        else:
            deleted_lines.append(deleted_item["raw"])

    for add_index, added_item in enumerate(unmatched_added):
        if add_index in used_added_indexes:
            continue
        added_lines.append(added_item["raw"])

    return {
        "added": added_lines,
        "deleted": deleted_lines,
        "replaced": replaced_lines,
    }


def _merge_change_sets(primary: Dict[str, Any], secondary: Dict[str, Any]) -> Dict[str, Any]:
    def _dedupe_lines(lines: List[str]) -> List[str]:
        seen = set()
        output: List[str] = []
        for line in lines:
            key = _normalize_compare_text(str(line or ""))
            if not key:
                continue
            if key in seen:
                continue
            seen.add(key)
            output.append(str(line))
        return output

    merged_added = _dedupe_lines(list(primary.get("added") or []) + list(secondary.get("added") or []))
    merged_deleted = _dedupe_lines(list(primary.get("deleted") or []) + list(secondary.get("deleted") or []))
    merged_replaced = list(primary.get("replaced") or []) + list(secondary.get("replaced") or [])

    return {
        "added": merged_added,
        "deleted": merged_deleted,
        "replaced": merged_replaced,
    }


def _collect_storage_image_changes(previous_storage: str, current_storage: str) -> Dict[str, Any]:
    return _table_image_collect_storage_image_changes(previous_storage, current_storage, _collect_net_changes)


def _apply_direct_storage_html_highlights(
    previous_storage: str,
    current_storage: str,
    table_style: str = "added",
    paragraph_style_kind: str = "added",
) -> str:
    return _table_image_apply_direct_storage_html_highlights(previous_storage, current_storage, table_style, paragraph_style_kind)


def _collect_storage_table_changes(previous_storage: str, current_storage: str) -> Dict[str, Any]:
    return _table_image_collect_storage_table_changes(previous_storage, current_storage, _collect_net_changes, _normalize_compare_text)


def _inject_highlight_cleanup_script() -> str:
    """Inject JavaScript that runs on page load to remove temporary highlight markers.
    This ensures that after page refresh, color highlights disappear but content stays."""
    script = f"""{_HIGHLIGHT_CLEANUP_START}<script type="text/javascript">
(function() {{
    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', cleanupHighlights);
    }} else {{
        cleanupHighlights();
    }}
    function cleanupHighlights() {{
        try {{
            const spans = document.querySelectorAll('span[data-dac="hl"], span[data-dac=\\\'hl\\\']');
            spans.forEach(span => {{
                while (span.firstChild) {{
                    span.parentNode.insertBefore(span.firstChild, span);
                }}
                span.parentNode.removeChild(span);
            }});
            const tagged = document.querySelectorAll('[data-dac="hl"], [data-dac=\\\'hl\\\']');
            tagged.forEach(el => {{
                el.removeAttribute('data-dac');
                if (el.tagName.toLowerCase() === 'div') {{
                    while (el.firstChild) {{
                        el.parentNode.insertBefore(el.firstChild, el);
                    }}
                    el.parentNode.removeChild(el);
                }}
            }});
        }} catch(e) {{}}
    }}
}})();
</script>{_HIGHLIGHT_CLEANUP_END}"""
    return script


def _apply_manual_edit_highlights_to_storage_html(
    storage_html: str,
    added_lines: List[str],
    deleted_lines: List[str],
    replaced_lines: Optional[List[Dict[str, str]]] = None,
    strict_structural_scope: bool = False,
) -> str:
    def _extract_caption_name(line: str) -> Optional[str]:
        text = str(line or "")
        match = re.search(r"<caption\s+name\s*=\s*['\"]([^'\"]+)['\"]\s*>", text, flags=re.IGNORECASE)
        if match:
            return str(match.group(1) or "").strip() or None
        return None

    def _find_caption_window(html: str, caption_name: Optional[str]) -> Optional[tuple[int, int]]:
        if not caption_name:
            return None

        safe_name = re.escape(caption_name)
        start_patterns = [
            re.compile(rf"&lt;caption\s+name\s*=\s*['\"]{safe_name}['\"]\s*&gt;", flags=re.IGNORECASE),
            re.compile(rf"<caption\s+name\s*=\s*['\"]{safe_name}['\"]\s*>", flags=re.IGNORECASE),
        ]
        end_patterns = [
            re.compile(r"&lt;/caption&gt;", flags=re.IGNORECASE),
            re.compile(r"</caption>", flags=re.IGNORECASE),
        ]

        for start_pat in start_patterns:
            start_match = start_pat.search(html)
            if not start_match:
                continue
            start_index = start_match.start()
            after_start = start_match.end()
            end_index = -1
            for end_pat in end_patterns:
                end_match = end_pat.search(html, after_start)
                if end_match:
                    end_index = end_match.end()
                    break
            if end_index != -1:
                return (start_index, end_index)
        return None

    def _window_bounds(window: Optional[tuple[int, int]], total_len: int) -> tuple[int, int]:
        if not window:
            return (0, total_len)
        left = max(0, min(total_len, int(window[0])))
        right = max(left, min(total_len, int(window[1])))
        return (left, right)

    def _replace_visible_text_once(
        html: str,
        escaped_text: str,
        replacement: str,
        prefer_last: bool,
        search_window: Optional[tuple[int, int]] = None,
    ) -> tuple[str, bool]:
        if not escaped_text:
            return html, False

        left, right = _window_bounds(search_window, len(html))
        if left >= right:
            return html, False

        protected = _protected_highlight_ranges(html)
        positions: List[int] = []
        scan_from = left
        while True:
            idx = html.find(escaped_text, scan_from, right)
            if idx == -1:
                break
            end_idx = idx + len(escaped_text)
            if not _range_is_protected(idx, end_idx, protected):
                positions.append(idx)
            scan_from = idx + len(escaped_text)

        def _is_inside_html_tag(pos: int) -> bool:
            """Return True if pos is inside an HTML tag (between < and matching >)."""
            last_lt = html.rfind("<", 0, pos)
            if last_lt == -1:
                return False
            # If there's no closing > between the last < and pos, we're inside a tag
            last_gt = html.find(">", last_lt, pos)
            return last_gt == -1

        # Filter out positions inside HTML tags to prevent injecting spans
        # into tag names or attributes (e.g. <table → <<span>tab</span>le)
        safe_positions = [p for p in positions if not _is_inside_html_tag(p)]

        if not safe_positions:
            return html, False

        # Avoid false positives when the same snippet appears multiple times in the
        # document and there is no scoped window (e.g., caption/table region).
        # In these cases, skipping highlight is safer than marking the wrong location.
        if len(safe_positions) > 1 and not search_window:
            return html, False

        idx = safe_positions[-1] if prefer_last else safe_positions[0]
        end_idx = idx + len(escaped_text)
        return (html[:idx] + replacement + html[end_idx:], True)

    def _fragment_visible_text(text: str) -> List[str]:
        value = " ".join(str(text or "").split()).strip()
        if not value:
            return []

        parts: List[str] = []
        for chunk in re.split(r"(?<=[.!?])\s+|\s*[;:]\s+", value):
            item = chunk.strip()
            if len(item) >= 14:
                parts.append(item)

        words = value.split()
        if len(words) >= 14:
            window = 14
            step = 7
            for index in range(0, max(1, len(words) - window + 1), step):
                segment = " ".join(words[index : index + window]).strip()
                if len(segment) >= 30:
                    parts.append(segment)

        deduped: List[str] = []
        seen = set()
        for part in parts:
            key = _normalize_compare_text(part)
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(part)
        return deduped

    def _extract_image_candidates(line: str) -> List[str]:
        return _table_image_extract_image_candidates(line)

    def _escape_text(value: str) -> str:
        return (
            str(value or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    def _visible_line_text(line: str) -> str:
        text = str(line or "").strip()
        if _TEMP_DELETED_WARNING_TEXT.lower() in text.lower():
            return ""
        if re.match(r"^</?caption\b[^>]*>$", text, flags=re.IGNORECASE):
            return ""
        text = re.sub(r"<[^>]+>", " ", text)
        # Unescape markdown escaped characters (e.g. Legacy\_AEP -> Legacy_AEP)
        text = re.sub(r"\\([\\`*_{}\[\]()#+\-.!|])", r"\1", text)
        text = re.sub(r"^\s{0,3}#{1,6}\s+", "", text)
        text = re.sub(r"^\s*[-*+]\s+", "", text)
        text = re.sub(r"^\s*\d+\.\s+", "", text)
        # Normalize inline markdown to visible rendered text so matching works
        # against storage HTML content (e.g. [text](url) -> text).
        text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
        text = re.sub(r"__([^_]+)__", r"\1", text)
        text = re.sub(r"\*([^*]+)\*", r"\1", text)
        text = re.sub(r"_([^_]+)_", r"\1", text)
        text = re.sub(r"`([^`]+)`", r"\1", text)
        return " ".join(text.split()).strip()

    def _protected_highlight_ranges(html: str) -> List[tuple[int, int]]:
        ranges: List[tuple[int, int]] = []
        # Paired tags carrying data-dac='hl' (span/div/tr/hN/ac:image, etc.)
        for m in re.finditer(r"<([a-zA-Z0-9:_-]+)\b[^>]*data-dac=['\"]hl['\"][^>]*>.*?</\1>", html, flags=re.IGNORECASE | re.DOTALL):
            ranges.append((m.start(), m.end()))
        # Self-closing/void tags carrying data-dac='hl' (e.g., <img .../>)
        for m in re.finditer(r"<[a-zA-Z0-9:_-]+\b[^>]*data-dac=['\"]hl['\"][^>]*?/?>", html, flags=re.IGNORECASE | re.DOTALL):
            ranges.append((m.start(), m.end()))
        return ranges

    def _range_is_protected(start: int, end: int, ranges: List[tuple[int, int]]) -> bool:
        for left, right in ranges:
            if start >= left and end <= right:
                return True
        return False

    def _try_highlight_img(
        line: str,
        html: str,
        style: str,
        search_window: Optional[tuple[int, int]] = None,
        prefer_last: bool = False,
    ) -> str:
        return _table_image_try_highlight_img(
            line,
            html,
            style,
            escape_text=_escape_text,
            window_bounds=_window_bounds,
            debug_skip_once=_debug_skip_once,
            search_window=search_window,
            prefer_last=prefer_last,
        )

    def _disambiguate_table_with_context(
        html: str,
        candidates: List[re.Match[str]],
        context_width: int = 200,
    ) -> Optional[re.Match[str]]:
        return _table_image_disambiguate_table_with_context(html, candidates, context_width)

    def _try_highlight_table_block(
        line: str,
        html: str,
        style: str,
        search_window: Optional[tuple[int, int]] = None,
        prefer_last: bool = False,
    ) -> str:
        scoped_window = _window_bounds(search_window, len(html)) if search_window else None
        return _table_image_try_highlight_table_block(
            line,
            html,
            style,
            escape_text=_escape_text,
            normalize_compare_text=_normalize_compare_text,
            search_window=scoped_window,
            prefer_last=prefer_last,
        )

    def _try_highlight_table_row(
        line: str,
        html: str,
        style: str,
        search_window: Optional[tuple[int, int]] = None,
        prefer_last: bool = False,
    ) -> str:
        scoped_window = _window_bounds(search_window, len(html)) if search_window else None
        return _table_image_try_highlight_table_row(
            line,
            html,
            style,
            normalize_compare_text=_normalize_compare_text,
            search_window=scoped_window,
            prefer_last=prefer_last,
        )

    def _parse_table_cells(line: str) -> List[str]:
        return _table_image_parse_table_cells(line)

    def _try_highlight_table_cell_diff(
        old_line: str,
        new_line: str,
        html: str,
        search_window: Optional[tuple[int, int]] = None,
        prefer_last: bool = False,
    ) -> str:
        scoped_window = _window_bounds(search_window, len(html)) if search_window else None
        return _table_image_try_highlight_table_cell_diff(
            old_line,
            new_line,
            html,
            normalize_compare_text=_normalize_compare_text,
            visible_line_text=_visible_line_text,
            try_highlight_text_block=try_highlight_text_block,
            search_window=scoped_window,
            prefer_last=prefer_last,
        )

    def _try_highlight_heading(line: str, html: str, style: str) -> str:
        """Highlight heading tags robustly even when inline markup differs."""
        hm = re.match(r"^\s*(#{1,6})\s+(.+)", str(line or "").strip())
        if not hm:
            return html
        target_level = len(hm.group(1))
        target_text = _normalize_compare_text(_visible_line_text(line))
        if not target_text:
            return html

        heading_pat = re.compile(r"(<h([1-6])\b[^>]*>)(.*?)(</h\2>)", re.IGNORECASE | re.DOTALL)
        scored: List[tuple[float, int, int, re.Match[str], int]] = []
        for m in heading_pat.finditer(html):
            open_tag = m.group(1)
            if "data-dac='hl'" in open_tag or 'data-dac="hl"' in open_tag:
                continue
            level = int(m.group(2))
            inner = str(m.group(3) or "")
            inner_text = _normalize_compare_text(re.sub(r"<[^>]+>", " ", inner))
            if not inner_text:
                continue
            ratio = difflib.SequenceMatcher(a=target_text, b=inner_text).ratio()
            if target_text in inner_text or inner_text in target_text:
                ratio = max(ratio, 0.96)
            # Prefer exact level, then stronger text similarity, then earlier occurrence
            level_bonus = 1 if level == target_level else 0
            scored.append((ratio, level_bonus, -m.start(), m, level))

        if not scored:
            return html

        scored.sort(reverse=True)
        best_ratio, _, _, best_match, best_level = scored[0]
        if best_ratio < 0.58:
            return html

        open_tag = best_match.group(1)
        bg = heading_style(style)
        if re.search(r"\sstyle=", open_tag, re.IGNORECASE):
            new_open = re.sub(
                r"\sstyle=(['\"])(.*?)\1",
                lambda mm: f" style={mm.group(1)}{mm.group(2)} {bg}{mm.group(1)}",
                open_tag,
                count=1,
                flags=re.IGNORECASE,
            )
            if "data-dac='hl'" not in new_open and 'data-dac="hl"' not in new_open:
                new_open = re.sub(rf"<h{best_level}\b", f"<h{best_level} data-dac='hl'", new_open, count=1, flags=re.IGNORECASE)
        else:
            new_open = re.sub(rf"<h{best_level}\b", f"<h{best_level} data-dac='hl' style='{bg}'", open_tag, count=1, flags=re.IGNORECASE)

        return html[:best_match.start()] + new_open + best_match.group(3) + best_match.group(4) + html[best_match.end():]

    def _try_highlight_any_ac_image(
        html: str,
        style: str,
        search_window: Optional[tuple[int, int]] = None,
        prefer_last: bool = False,
    ) -> str:
        scoped_window = _window_bounds(search_window, len(html)) if search_window else None
        return _table_image_try_highlight_any_ac_image(
            html,
            style,
            debug_skip_once=_debug_skip_once,
            search_window=scoped_window,
            prefer_last=prefer_last,
        )

    def _try_highlight_ac_image(
        line: str,
        html: str,
        style: str,
        search_window: Optional[tuple[int, int]] = None,
        prefer_last: bool = False,
    ) -> str:
        scoped_window = _window_bounds(search_window, len(html)) if search_window else None
        return _table_image_try_highlight_ac_image(
            line,
            html,
            style,
            debug_skip_once=_debug_skip_once,
            search_window=scoped_window,
            prefer_last=prefer_last,
        )

    def _replacement_delta_fragments(old_text: str, new_text: str, use_new: bool) -> List[str]:
        old_visible = _visible_line_text(old_text)
        new_visible = _visible_line_text(new_text)
        old_words = old_visible.split()
        new_words = new_visible.split()
        matcher = difflib.SequenceMatcher(a=old_words, b=new_words)

        fragments: List[str] = []
        for opcode, i1, i2, j1, j2 in matcher.get_opcodes():
            if opcode == "equal":
                continue
            if use_new and opcode in {"insert", "replace"}:
                chunk = " ".join(new_words[j1:j2]).strip()
                if chunk:
                    fragments.append(chunk)
            if (not use_new) and opcode in {"delete", "replace"}:
                chunk = " ".join(old_words[i1:i2]).strip()
                if chunk:
                    fragments.append(chunk)

        deduped: List[str] = []
        seen = set()
        for fragment in fragments:
            key = _normalize_compare_text(fragment)
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(fragment)
        return deduped

    normalized_added_lines: List[str] = list(added_lines or [])
    normalized_deleted_bottom_lines: List[str] = list(deleted_lines or [])
    structural_replaced_lines: List[Dict[str, str]] = []
    for pair in (replaced_lines or []):
        old_line = str((pair or {}).get("from") or "").strip()
        new_line = str((pair or {}).get("to") or "").strip()

        is_structural = bool(
            _extract_image_candidates(old_line)
            or _extract_image_candidates(new_line)
            or ((old_line.startswith("|") and old_line.endswith("|")) or ("\t" in old_line))
            or ((new_line.startswith("|") and new_line.endswith("|")) or ("\t" in new_line))
            or re.match(r"^\s*#{1,6}\s+", old_line)
            or re.match(r"^\s*#{1,6}\s+", new_line)
        )

        if is_structural:
            structural_replaced_lines.append({"from": old_line, "to": new_line})
            continue

        old_fragments = _replacement_delta_fragments(old_line, new_line, use_new=False)
        new_fragments = _replacement_delta_fragments(old_line, new_line, use_new=True)

        if old_fragments:
            normalized_deleted_bottom_lines.extend(old_fragments)
        elif old_line and not new_line:
            normalized_deleted_bottom_lines.append(old_line)

        if new_fragments:
            normalized_added_lines.extend(new_fragments)
        elif new_line and not old_line:
            normalized_added_lines.append(new_line)

    replaced_lines_for_inline: List[Dict[str, str]] = [
        pair
        for pair in (replaced_lines or [])
        if pair not in structural_replaced_lines
    ]

    highlighted_html = str(storage_html or "")
    highlighted_image_keys: set[str] = set()
    highlighted_table_keys: set[str] = set()
    highlighted_caption_names: set[str] = set()  # captions whose full table is already highlighted
    debug_skip_notes: set[str] = set()

    def _try_highlight_full_caption_table(caption_name: str, html: str, style: str) -> str:
        """Find the <table> inside the caption block and highlight the whole thing."""
        cap_window = _find_caption_window(html, caption_name)
        if not cap_window:
            return html
        left, right = cap_window
        table_pat = re.compile(r"<table\b[^>]*>.*?</table>", re.IGNORECASE | re.DOTALL)
        best = None
        for m in table_pat.finditer(html, left, right):
            best = m  # take last match inside window
        if not best:
            return html
        tbl_start = best.start()
        tbl_end = best.end()
        before_check = html[max(0, tbl_start - 50):tbl_start]
        if "data-dac='hl'" in before_check or 'data-dac="hl"' in before_check:
            return html
        wrapper_style = table_wrapper_style(style)
        wrapped = f"<div data-dac='hl' style='{wrapper_style}'>{best.group(0)}</div>"
        return html[:tbl_start] + wrapped + html[tbl_end:]

    def _find_caption_for_row_in_html(tsv_cells: List[str], html: str) -> Optional[str]:
        """Given row cells (pipe or TSV), find which caption in the HTML contains the
        matching table.  Uses word-level fuzzy matching so minor wording changes
        (old vs new cell values for replacements) still resolve correctly.
        Also falls back to a full-HTML scan when caption-window search fails.
        Returns the caption name string, or None if not found.
        """
        if not tsv_cells:
            return None
        cap_name_pat = re.compile(
            r"(?:&lt;|<)caption\s+name\s*=\s*['\"]([^'\"]+)['\"]\s*(?:&gt;|>)",
            re.IGNORECASE,
        )
        td_pat = re.compile(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", re.IGNORECASE | re.DOTALL)
        table_pat = re.compile(r"<table\b[^>]*>.*?</table>", re.IGNORECASE | re.DOTALL)

        # Build two representations: exact normalized cells AND flat word set
        wanted_exact = [_normalize_compare_text(c) for c in tsv_cells if _normalize_compare_text(c)]
        wanted_words: set[str] = set()
        for c in tsv_cells:
            for w in _normalize_compare_text(str(c or "")).split():
                if len(w) >= 3:
                    wanted_words.add(w)

        if not wanted_exact and not wanted_words:
            return None

        def _score_table(tbl_html: str) -> float:
            """Return a [0,1] match score for how well tbl_html matches wanted cells."""
            row_cells_norm: List[str] = []
            for td_m in td_pat.finditer(tbl_html):
                raw = re.sub(r"<[^>]+>", " ", str(td_m.group(1) or ""))
                norm = _normalize_compare_text(" ".join(raw.split()).strip())
                if norm:
                    row_cells_norm.append(norm)
            if not row_cells_norm:
                return 0.0
            # Exact cell hits
            exact_hits = sum(1 for w in wanted_exact if w in row_cells_norm)
            if wanted_exact and exact_hits >= max(1, len(wanted_exact) // 2):
                return 1.0
            # Word-level fallback across all cells concatenated
            all_cell_words: set[str] = set()
            for cell in row_cells_norm:
                all_cell_words.update(cell.split())
            common = wanted_words & all_cell_words
            if not wanted_words:
                return 0.0
            return len(common) / len(wanted_words)

        SCORE_THRESHOLD = 0.28  # tolerate markdown-vs-storage wording drift

        # Phase 1: search only within caption windows (precise)
        best_cap: Optional[str] = None
        best_score = 0.0
        for cap_match in cap_name_pat.finditer(html):
            cap_name = str(cap_match.group(1) or "").strip()
            if not cap_name:
                continue
            cap_window = _find_caption_window(html, cap_name)
            if not cap_window:
                continue
            left, right = cap_window
            for tbl_m in table_pat.finditer(html, left, right):
                score = _score_table(tbl_m.group(0))
                if score > best_score:
                    best_score = score
                    best_cap = cap_name

        if best_cap and best_score >= SCORE_THRESHOLD:
            return best_cap

        # Phase 2: full-HTML scan — if exactly ONE table matches, use its nearest caption
        matching_tables: List[re.Match[str]] = []
        for tbl_m in table_pat.finditer(html):
            if _score_table(tbl_m.group(0)) >= SCORE_THRESHOLD:
                matching_tables.append(tbl_m)

        if len(matching_tables) != 1:
            return None  # ambiguous or not found

        # Find nearest caption before this table
        tbl_start = matching_tables[0].start()
        best_cap = None
        for cap_match in cap_name_pat.finditer(html, 0, tbl_start):
            best_cap = str(cap_match.group(1) or "").strip() or best_cap
        return best_cap or None

    def _debug_skip_once(note: str) -> None:
        text = str(note or "").strip()
        if not text or text in debug_skip_notes:
            return
        debug_skip_notes.add(text)
        print(f"[HIGHLIGHT-SKIP] {text}")

    def _image_change_key(line: str) -> str:
        return _table_image_image_change_key(line)

    def _table_change_key(line: str) -> str:
        return _table_image_table_change_key(line, _normalize_compare_text)
    # Avoid risky cross-tag text replacement that can generate invalid XHTML.
    # Use safe block-level fallback matcher instead.
    enable_fuzzy_text_match = False

    active_caption_name: Optional[str] = None

    def _find_content_context_window(
        surrounding_lines: List[str],
        html: str,
        search_radius: int = 500,
    ) -> Optional[tuple[int, int]]:
        """Create a search window based on surrounding added text (context clues).
        
        When a table/image is added but has multiple candidates in HTML,
        use nearby added lines (heading, bullet points, etc.) to narrow scope.
        """
        # Extract distinctive keywords from surrounding context
        context_keywords: List[str] = []
        for line in surrounding_lines:
            stripped = str(line or "").strip()
            # Skip very short lines, markdown markers, table separators
            if len(stripped) < 10:
                continue
            if re.match(r"^[\-=_~`*|:\s]{3,}$", stripped):
                continue
            if stripped.startswith("|") and stripped.endswith("|"):
                continue
            # Extract first meaningful phrase (before colon or period)
            base = re.split(r"[:.]", stripped)[0].strip()
            if len(base) >= 15:
                context_keywords.append(_normalize_compare_text(base)[:60])

        if not context_keywords:
            return None

        # Search HTML source for these context keywords to find accurate bounds.
        # Using raw HTML search keeps indices valid for later HTML slicing.
        positions: List[int] = []
        for keyword in context_keywords:
            if not keyword:
                continue
            keyword_pattern = re.compile(re.escape(keyword), flags=re.IGNORECASE)
            for match in keyword_pattern.finditer(html):
                positions.append(match.start())
                break

        if positions:
            # Create window around found keywords
            min_pos = min(positions)
            max_pos = max(positions)
            window_start = max(0, min_pos - search_radius)
            window_end = min(len(html), max_pos + search_radius)
            return (window_start, window_end)

        return None

    def _changed_word_fragments(old_text: str, new_text: str, limit: int = 8) -> List[str]:
        old_words = str(old_text or "").split()
        new_words = str(new_text or "").split()
        matcher = difflib.SequenceMatcher(a=old_words, b=new_words)
        ignored_tokens = {
            "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with", "by",
            "is", "are", "was", "were", "be", "as", "at", "from", "that", "this", "it",
        }
        fragments: List[str] = []
        for opcode, i1, i2, j1, j2 in matcher.get_opcodes():
            if opcode == "replace":
                fragments.extend(old_words[i1:i2])
                fragments.extend(new_words[j1:j2])
            elif opcode == "insert":
                fragments.extend(new_words[j1:j2])
            elif opcode == "delete":
                fragments.extend(old_words[i1:i2])

        deduped: List[str] = []
        seen = set()
        for token in fragments:
            text = str(token or "").strip()
            if len(text) < 4:
                continue
            normalized_text = _normalize_compare_text(text)
            if not normalized_text:
                continue
            if normalized_text in ignored_tokens:
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(text)
            if len(deduped) >= max(1, int(limit)):
                break
        return deduped

    def _render_replacement_preview_value(raw_line: str) -> str:
        text = str(raw_line or "").strip()
        if not text:
            return ""

        candidates = _extract_image_candidates(text)
        if candidates:
            image_src = candidates[0]
            image_label = candidates[-1] if candidates else text
            md_image = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", text)
            if md_image:
                image_label = md_image.group(1).strip() or image_label

            safe_src = _escape_text(image_src)
            safe_label = _escape_text(image_label)
            if re.match(r"^https?://", image_src, flags=re.IGNORECASE):
                return (
                    "<div style='font-size:0.9em;font-weight:600;margin-bottom:4px;'>Image</div>"
                    f"<div style='margin:4px 0;'><img src='{safe_src}' alt='{safe_label}' "
                    "style='max-width:220px;max-height:120px;border:1px solid #cfd8dc;border-radius:4px;background:#fff;' /></div>"
                    f"<div style='font-size:0.8em;opacity:0.9;word-break:break-all;'>{safe_src}</div>"
                )
            return (
                "<div style='font-size:0.9em;font-weight:600;margin-bottom:4px;'>Image</div>"
                f"<div><code>{_escape_text(text)}</code></div>"
            )

        stripped = text.strip()
        if (stripped.startswith("|") and stripped.endswith("|")) or ("\t" in stripped):
            if "\t" in stripped and not (stripped.startswith("|") and stripped.endswith("|")):
                cells = [c.strip() for c in stripped.split("\t") if c.strip()]
            else:
                cells = [c.strip() for c in stripped.strip("|").split("|") if c.strip()]
            if cells:
                cells_html = "".join(
                    f"<td style='border:1px solid #b0bec5;padding:4px 8px;background:#fff;'>{_escape_text(cell)}</td>"
                    for cell in cells
                )
                return (
                    "<div style='font-size:0.9em;font-weight:600;margin-bottom:4px;'>Table row</div>"
                    f"<table style='border-collapse:collapse;margin:2px 0;'><tr>{cells_html}</tr></table>"
                )

        visible = _visible_line_text(text) or text
        visible = _escape_text(visible)
        return (
            "<div style='font-size:0.9em;font-weight:600;margin-bottom:4px;'>Paragraph</div>"
            f"<div style='background:#ffffff;border:1px solid #cfd8dc;border-radius:4px;padding:6px 8px;line-height:1.5;'>{visible}</div>"
        )

    # Highlight structural replacements first so images/tables use precise element-level styling.
    for pair in structural_replaced_lines:
        line_to = str((pair or {}).get("to") or "").strip()
        line_from = str((pair or {}).get("from") or "").strip()
        probe_line = line_to or line_from
        if not probe_line:
            continue

        caption_start = _extract_caption_name(probe_line)
        if caption_start:
            active_caption_name = caption_start
            continue
        if re.search(r"</caption>", probe_line, flags=re.IGNORECASE):
            active_caption_name = None
            continue

        caption_window = _find_caption_window(highlighted_html, active_caption_name)

        if _extract_image_candidates(line_to) or _extract_image_candidates(line_from):
            # Only skip if REPLACING (line_from exists) and no scope. New added images (line_to only) should always be highlighted.
            if strict_structural_scope and not caption_window and line_from:
                normalized_deleted_bottom_lines.append(line_from)
                continue
            image_key = _image_change_key(line_to or line_from)
            if image_key and image_key in highlighted_image_keys:
                if line_from:
                    normalized_deleted_bottom_lines.append(line_from)
                continue
            target_line = line_to or line_from
            new_html = _try_highlight_img(target_line, highlighted_html, "replaced", caption_window, True)
            if new_html == highlighted_html:
                new_html = _try_highlight_ac_image(target_line, highlighted_html, "replaced", caption_window, True)
            if new_html != highlighted_html:
                highlighted_html = new_html
                if image_key:
                    highlighted_image_keys.add(image_key)
            if line_from:
                normalized_deleted_bottom_lines.append(line_from)
            continue

        if ((line_from.startswith("|") and line_from.endswith("|")) or ("\t" in line_from)
            or (line_to.startswith("|") and line_to.endswith("|")) or ("\t" in line_to)):
            if line_from:
                normalized_deleted_bottom_lines.append(line_from)
            # For caption-scoped table row: highlight the whole parent table once.
            # Try old row cells first because current HTML still contains old content.
            inferred_cap = active_caption_name
            if not inferred_cap:
                from_cells = _parse_table_cells(line_from) if line_from else []
                to_cells = _parse_table_cells(line_to) if line_to else []
                inferred_cap = (
                    _find_caption_for_row_in_html(from_cells, highlighted_html)
                    or _find_caption_for_row_in_html(to_cells, highlighted_html)
                )
            if inferred_cap:
                if inferred_cap not in highlighted_caption_names:
                    new_html = _try_highlight_full_caption_table(inferred_cap, highlighted_html, "replaced")
                    if new_html != highlighted_html:
                        highlighted_html = new_html
                        highlighted_caption_names.add(inferred_cap)
                continue
            # Only skip if REPLACING (line_from exists) and no scope.
            if strict_structural_scope and not caption_window:
                continue
            table_key = _table_change_key(line_to or line_from)
            if table_key and table_key in highlighted_table_keys:
                continue
            new_html = _try_highlight_table_block(line_to or line_from, highlighted_html, "replaced", caption_window, False)
            if new_html != highlighted_html:
                highlighted_html = new_html
                if table_key:
                    highlighted_table_keys.add(table_key)
            continue

        if re.match(r"^\s*#{1,6}\s+", line_to or line_from):
            new_html = _try_highlight_heading(line_to or line_from, highlighted_html, "replaced")
            if new_html != highlighted_html:
                highlighted_html = new_html
            if line_from:
                normalized_deleted_bottom_lines.append(line_from)
            continue

    # Highlight replacements with word-level precision (avoid full paragraph highlight).
    for pair in (replaced_lines_for_inline or []):
        line_to = str((pair or {}).get("to") or "").strip()
        line_from = str((pair or {}).get("from") or "").strip()
        probe_line = line_to or line_from
        if not probe_line:
            continue

        caption_start = _extract_caption_name(probe_line)
        if caption_start:
            active_caption_name = caption_start
            continue
        if re.search(r"</caption>", probe_line, flags=re.IGNORECASE):
            active_caption_name = None
            continue

        caption_window = _find_caption_window(highlighted_html, active_caption_name)

        # Handle image/table/heading replacements with structural matchers.
        matched = False
        for candidate in [line_to, line_from]:
            if not candidate:
                continue
            stripped_pair_line = candidate.strip()
            if _extract_image_candidates(stripped_pair_line):
                if strict_structural_scope and not caption_window:
                    continue
                new_html = _try_highlight_img(candidate, highlighted_html, "replaced", caption_window, True)
                if new_html == highlighted_html:
                    new_html = _try_highlight_ac_image(candidate, highlighted_html, "replaced", caption_window, True)
                if new_html != highlighted_html:
                    highlighted_html = new_html
                    matched = True
                    break
            elif re.match(r"^\s*#{1,6}\s+", stripped_pair_line):
                new_html = _try_highlight_heading(candidate, highlighted_html, "replaced")
                if new_html != highlighted_html:
                    highlighted_html = new_html
                    matched = True
                    break
            elif (stripped_pair_line.startswith("|") and stripped_pair_line.endswith("|")) or ("\t" in stripped_pair_line):
                if strict_structural_scope and not caption_window:
                    continue
                new_html = _try_highlight_table_cell_diff(line_from, line_to, highlighted_html, caption_window, False)
                if new_html == highlighted_html:
                    new_html = _try_highlight_table_row(candidate, highlighted_html, "replaced", caption_window, False)
                if new_html != highlighted_html:
                    highlighted_html = new_html
                    matched = True
                    break

        if matched:
            continue

        old_visible = _visible_line_text(line_from)
        new_visible = _visible_line_text(line_to)

        # Preferred path: word-level replacement highlighter.
        if try_highlight_replaced_text_block:
            highlighted_html, matched = try_highlight_replaced_text_block(
                highlighted_html,
                old_visible,
                new_visible,
            )
            if matched:
                continue

        # Fallback path: highlight changed words only (not full sentence/paragraph).
        for fragment in _changed_word_fragments(old_visible, new_visible, limit=8):
            escaped_fragment = _escape_text(fragment)
            replacement = f"<span data-dac='hl' style='{inline_span_style('replaced')}'>{escaped_fragment}</span>"
            highlighted_html, matched = _replace_visible_text_once(
                highlighted_html,
                escaped_fragment,
                replacement,
                True,
                caption_window,
            )

    # Highlight added/updated lines in blue in-place
    active_caption_name = None
    for idx, line in enumerate(normalized_added_lines):
        stripped_line = str(line or "").strip()
        caption_start = _extract_caption_name(stripped_line)
        if caption_start:
            active_caption_name = caption_start
            # Caption open line is itself in added_lines → whole table is brand new.
            # Highlight the entire table immediately and skip individual row processing.
            if caption_start not in highlighted_caption_names:
                new_html = _try_highlight_full_caption_table(caption_start, highlighted_html, "added")
                if new_html != highlighted_html:
                    highlighted_html = new_html
                    highlighted_caption_names.add(caption_start)
            continue
        if re.search(r"</caption>", stripped_line, flags=re.IGNORECASE):
            active_caption_name = None
            continue
        # If this row belongs to an already-highlighted caption table, skip it.
        if active_caption_name and active_caption_name in highlighted_caption_names:
            continue
        caption_window = _find_caption_window(highlighted_html, active_caption_name)
        
        # For ambiguous table/image matches, use surrounding context lines as clues
        # Include lines before and after current line to establish context
        context_radius = 3
        context_start = max(0, idx - context_radius)
        context_end = min(len(normalized_added_lines), idx + context_radius + 1)
        surrounding_lines = normalized_added_lines[context_start:context_end]
        
        # Handle images: markdown ![alt](url) and Confluence !file.png! forms.
        # Try HTML <img> first, then Confluence <ac:image> block.
        if _extract_image_candidates(stripped_line):
            image_key = _image_change_key(stripped_line)
            if image_key and image_key in highlighted_image_keys:
                continue
            # For added images, always allow surrounding context disambiguation when no caption.
            search_window = caption_window or _find_content_context_window(surrounding_lines, highlighted_html, 500)
            new_html = _try_highlight_img(line, highlighted_html, "added", search_window, True)
            if new_html == highlighted_html:
                new_html = _try_highlight_ac_image(line, highlighted_html, "added", search_window, True)
            if new_html != highlighted_html and image_key:
                highlighted_image_keys.add(image_key)
            highlighted_html = new_html
            continue
        # Handle generic image placeholder lines from caption exports
        # Only highlight if we're inside a caption (have a defined window) and actual images exist
        if stripped_line.lower() == "image":
            if caption_window:
                highlighted_html = _try_highlight_any_ac_image(highlighted_html, "added", caption_window, True)
            continue
        # Handle table rows: | cell | cell |
        # CRITICAL: Row-level only (avoid full-table highlight on partial row changes)
        if (stripped_line.startswith("|") and stripped_line.endswith("|")) or ("\t" in stripped_line):
            table_key = _table_change_key(stripped_line)
            if table_key and table_key in highlighted_table_keys:
                continue
            # If inside a caption scope and the whole table not yet highlighted, highlight it now.
            if active_caption_name and active_caption_name not in highlighted_caption_names:
                new_html = _try_highlight_full_caption_table(active_caption_name, highlighted_html, "added")
                if new_html != highlighted_html:
                    highlighted_html = new_html
                    highlighted_caption_names.add(active_caption_name)
                continue
            if active_caption_name and active_caption_name in highlighted_caption_names:
                continue
            # No caption scope — try to find which caption this row belongs to in the HTML
            row_cells = _parse_table_cells(stripped_line)
            # For added rows: try both the line itself AND surrounding context lines as candidates
            inferred_caption = _find_caption_for_row_in_html(row_cells, highlighted_html)
            if inferred_caption and inferred_caption not in highlighted_caption_names:
                new_html = _try_highlight_full_caption_table(inferred_caption, highlighted_html, "added")
                if new_html != highlighted_html:
                    highlighted_html = new_html
                    highlighted_caption_names.add(inferred_caption)
                continue
            if inferred_caption and inferred_caption in highlighted_caption_names:
                continue
            # No caption found — use surrounding context to choose likely full table.
            search_window = caption_window or _find_content_context_window(surrounding_lines, highlighted_html, 500)
            new_html = _try_highlight_table_block(line, highlighted_html, "added", search_window, False)
            if new_html != highlighted_html and table_key:
                highlighted_table_keys.add(table_key)
            highlighted_html = new_html
            continue
        # Handle headings: # Title, ## Title, etc. — highlight full <hN> tag
        if re.match(r"^\s*#{1,6}\s+", stripped_line):
            new_html = _try_highlight_heading(line, highlighted_html, "added")
            if new_html != highlighted_html:
                highlighted_html = new_html
                continue
        visible_text = _visible_line_text(line)
        if not visible_text:
            continue
        escaped_text = _escape_text(visible_text)
        replacement = f"<span data-dac='hl' style='{inline_span_style('added')}'>{escaped_text}</span>"
        highlighted_html, matched = _replace_visible_text_once(
            highlighted_html,
            escaped_text,
            replacement,
            True,
            caption_window,
        )

        # Fallback: short/medium phrase highlighting when exact escaped string is split by inline HTML.
        if not matched and try_highlight_text_block:
            words = visible_text.split()
            if 3 <= len(words) <= 14 and len(visible_text) <= 140 and not caption_window:
                for fragment in _fragment_visible_text(visible_text):
                    if len(fragment.split()) > 14 or len(fragment) > 140:
                        continue
                    highlighted_html, matched = try_highlight_text_block(highlighted_html, fragment, "added")
                    if matched:
                        break

    # Deleted (and replaced-old) content is shown only in bottom indicator.
    # Do not paint inline red in document body.
    def _is_deleted_noise_line(raw_line: str) -> bool:
        text = str(raw_line or "").strip()
        if not text:
            return True
        # Markdown/table separator lines like -----, | --- | --- |
        if re.match(r"^[\-=_~`*|:\s]{3,}$", text):
            return True
        if text.lower() in {"...", "…"}:
            return True
        return False

    not_found_deleted: List[str] = []
    for line in normalized_deleted_bottom_lines:
        if _is_deleted_noise_line(line):
            continue
        visible_text = _visible_line_text(line)
        if visible_text and not _is_deleted_noise_line(visible_text):
            not_found_deleted.append(line)

    # Append a visible indicator block for deleted lines not found in the current page HTML.
    # These lines are gone from the page but the user still needs to see them highlighted
    # so they know what content will be removed or was already removed.
    if not_found_deleted:
        rendered_deleted: List[str] = []
        for line in not_found_deleted:
            preview = _render_replacement_preview_value(line)
            if preview:
                rendered_deleted.append(preview)

        if rendered_deleted:
            indicator_parts: List[str] = [
                "<div data-dac='reflect-block' style='margin:10px 0;padding:8px 10px;"
                "background:#fff5f5;border-left:4px solid #e53935;border-radius:3px;'>",
                "<div style='font-weight:600;color:#b71c1c;margin-bottom:6px;font-size:0.95em;'>"
                "Deleted Content</div>",
            ]
            for vt in rendered_deleted:
                indicator_parts.append(
                    "<div data-dac='hl' style='background-color:#ffebee;color:#b71c1c;"
                    "border:1px solid #e53935;"
                    "text-decoration-thickness:2px;padding:6px 8px;margin:4px 0;"
                    f"border-radius:2px;'>{vt}</div>"
                )
            indicator_parts.append("</div>")
            highlighted_html = highlighted_html.rstrip() + "\n" + "".join(indicator_parts)

    return highlighted_html


def _apply_highlights_with_optional_cleanup(
    storage_html: str,
    added_lines: List[str],
    deleted_lines: List[str],
    replaced_lines: Optional[List[Dict[str, str]]] = None,
    auto_cleanup_on_reload: bool = False,
    baseline_storage_html: Optional[str] = None,
    strict_structural_scope: bool = False,
) -> str:
    """Apply highlights and optionally inject cleanup script for auto-removal on page load.
    
    When baseline_storage_html is provided, tables that were added online are matched
    by exact HTML string comparison (position-accurate) before content-based matching.
    This eliminates ambiguity when the same table structure appears multiple times.
    """
    working_html = storage_html

    # Phase 1: Direct HTML matching for tables — bypasses all content guessing.
    # Finds exact added <table> blocks from the diff and wraps them precisely.
    if baseline_storage_html:
        working_html = _apply_direct_storage_html_highlights(
            previous_storage=baseline_storage_html,
            current_storage=working_html,
            table_style="added",
        )

    # Phase 2: Content-based matching for text, images, headings, etc.
    # Already-highlighted tables (from Phase 1) are automatically skipped.
    highlighted = _apply_manual_edit_highlights_to_storage_html(
        storage_html=working_html,
        added_lines=added_lines,
        deleted_lines=deleted_lines,
        replaced_lines=replaced_lines,
        strict_structural_scope=bool(strict_structural_scope or baseline_storage_html),
    )
    if auto_cleanup_on_reload:
        cleanup_script = _inject_highlight_cleanup_script()
        highlighted = highlighted + "\n" + cleanup_script
    return highlighted


def _build_page_copy_preview_payload(
    previous_storage: str,
    previous_markdown: str,
    current_storage: str,
    current_markdown: str,
    baseline_storage: str,
    baseline_markdown: str,
) -> Dict[str, Any]:
    """Build rendered page-copy previews for HTML report output."""
    preview_base_html = _strip_inline_highlights(_strip_existing_diff_reflection_block(previous_storage))

    def _change_counts(changes: Dict[str, Any]) -> Dict[str, int]:
        return {
            "added": len(changes.get("added") or []),
            "deleted": len(changes.get("deleted") or []),
            "replaced": len(changes.get("replaced") or []),
        }

    preview_payload: Dict[str, Any] = {
        "available": True,
        "variants": [],
    }

    update_changes = _collect_net_changes(previous_markdown, current_markdown)
    update_changes = _merge_change_sets(
        update_changes,
        _collect_storage_image_changes(str(previous_storage or ""), str(current_storage or "")),
    )
    update_changes = _merge_change_sets(
        update_changes,
        _collect_storage_table_changes(str(previous_storage or ""), str(current_storage or "")),
    )
    update_preview_html = _apply_highlights_with_optional_cleanup(
        storage_html=preview_base_html,
        added_lines=update_changes.get("added") or [],
        deleted_lines=update_changes.get("deleted") or [],
        replaced_lines=update_changes.get("replaced") or [],
        auto_cleanup_on_reload=False,
    )
    preview_payload["update_preview"] = {
        "title": "Update Preview",
        "description": "Copy of the current live page with local add/delete/replace highlights.",
        "counts": _change_counts(update_changes),
        "html": update_preview_html,
    }
    preview_payload["variants"].append("update_preview")

    baseline_available = bool(
        (isinstance(baseline_storage, str) and baseline_storage.strip())
        or (isinstance(baseline_markdown, str) and baseline_markdown.strip())
    )
    if baseline_available:
        manual_changes = _collect_net_changes(baseline_markdown, previous_markdown)
        manual_changes = _merge_change_sets(
            manual_changes,
            _collect_storage_image_changes(str(baseline_storage or ""), str(previous_storage or "")),
        )
        manual_changes = _merge_change_sets(
            manual_changes,
            _collect_storage_table_changes(str(baseline_storage or ""), str(previous_storage or "")),
        )
        manual_preview_html = _apply_highlights_with_optional_cleanup(
            storage_html=preview_base_html,
            added_lines=manual_changes.get("added") or [],
            deleted_lines=manual_changes.get("deleted") or [],
            replaced_lines=manual_changes.get("replaced") or [],
            auto_cleanup_on_reload=False,
            baseline_storage_html=str(baseline_storage or ""),
            strict_structural_scope=True,
        )
        preview_payload["manual_server_preview"] = {
            "title": "Manual Server Edit Preview",
            "description": "Copy of the current live page with direct online edits since last publish highlighted.",
            "counts": _change_counts(manual_changes),
            "html": manual_preview_html,
        }
        preview_payload["variants"].append("manual_server_preview")

    return preview_payload


def _build_inline_markdown_reflection_html(
    previous_markdown: str,
    current_markdown: str,
    splitter: Any,
    override_preview: bool,
) -> str:
    net_changes = _collect_net_changes(previous_markdown, current_markdown)
    net_added_counter = Counter(_normalize_compare_text(line) for line in net_changes["added"] if _normalize_compare_text(line))
    net_deleted_counter = Counter(_normalize_compare_text(line) for line in net_changes["deleted"] if _normalize_compare_text(line))

    diff_lines = list(difflib.ndiff((previous_markdown or "").splitlines(), (current_markdown or "").splitlines()))

    body_parts: List[str] = []

    def _append_normal(text: str) -> None:
        html = _line_to_safe_reflection_xhtml(text)
        if html.strip():
            body_parts.append(html)

    idx = 0
    while idx < len(diff_lines):
        raw = diff_lines[idx]
        if raw.startswith("? "):
            idx += 1
            continue

        next_raw = diff_lines[idx + 1] if idx + 1 < len(diff_lines) else None

        if raw.startswith("- ") and next_raw and next_raw.startswith("+ "):
            old_text = raw[2:]
            new_text = next_raw[2:]
            old_norm = _normalize_compare_text(old_text)
            new_norm = _normalize_compare_text(new_text)

            if old_norm == new_norm:
                _append_normal(new_text)
                idx += 2
                continue

            old_is_real_delete = bool(old_norm and net_deleted_counter.get(old_norm, 0) > 0)
            new_is_real_add = bool(new_norm and net_added_counter.get(new_norm, 0) > 0)

            if old_norm and old_is_real_delete:
                net_deleted_counter[old_norm] -= 1
            if new_norm and new_is_real_add:
                net_added_counter[new_norm] -= 1

            if not old_is_real_delete and not new_is_real_add:
                _append_normal(new_text)
                idx += 2
                continue
            
            old_html = _line_to_safe_reflection_xhtml(old_text)
            new_html = _line_to_safe_reflection_xhtml(new_text)
            if old_is_real_delete and old_html.strip():
                body_parts.append(_wrap_highlight_html(old_html, "deleted"))
            if new_is_real_add and new_html.strip():
                body_parts.append(_wrap_highlight_html(new_html, "override" if override_preview else "added"))
            idx += 2
            continue

        if raw.startswith("  "):
            _append_normal(raw[2:])
            idx += 1
            continue

        if raw.startswith("+ "):
            add_text = raw[2:]
            add_norm = _normalize_compare_text(add_text)
            if not add_norm or net_added_counter.get(add_norm, 0) <= 0:
                idx += 1
                continue
            net_added_counter[add_norm] -= 1
            add_html = _line_to_safe_reflection_xhtml(add_text)
            if add_html.strip():
                body_parts.append(_wrap_highlight_html(add_html, "override" if override_preview else "added"))
        elif raw.startswith("- "):
            del_text = raw[2:]
            del_norm = _normalize_compare_text(del_text)
            if not del_norm or net_deleted_counter.get(del_norm, 0) <= 0:
                idx += 1
                continue
            net_deleted_counter[del_norm] -= 1
            del_html = _line_to_safe_reflection_xhtml(del_text)
            if del_html.strip():
                body_parts.append(_wrap_highlight_html(del_html, "deleted"))
        idx += 1

    return "\n".join(part for part in body_parts if part and part.strip()).strip()


def _build_diff_reflection_block(
    result: Dict[str, Any],
    reflect_mode: str,
    changes_only: bool,
    override_preview: bool,
) -> str:
    compare = result.get("compare") or {}
    since = result.get("since_last_publish") or {}
    drift = bool(((result.get("guard") or {}).get("drift")))

    if reflect_mode == "storage":
        direct_lines = ((compare.get("storage") or {}).get("diff_lines") or [])
        title = "Storage/HTML Diff"
    else:
        direct_lines = ((compare.get("markdown") or {}).get("diff_lines") or [])
        title = "Markdown Diff"

    body_parts: List[str] = []
    body_parts.append(
        "<div data-dac='reflect-block' style='margin:10px 0;padding:4px 0;border:0;background:transparent;'>"
    )

    baseline_available = bool(since.get("baseline_available"))
    if drift and baseline_available and reflect_mode == "markdown":
        server_lines = _lines_for_reflection(
            (((since.get("server_edits") or {}).get("markdown") or {}).get("diff_lines") or []),
            changes_only,
        )
        local_lines = _lines_for_reflection(
            (((since.get("local_changes") or {}).get("markdown") or {}).get("diff_lines") or []),
            changes_only,
        )

        body_parts.append("<div style='font-weight:600;color:#0d47a1;margin:8px 0 4px;'>SCDP manual edits (Blue)</div>")
        if server_lines:
            _append_reflection_lines(body_parts, server_lines, style="server")
        else:
            body_parts.append("<div style='color:#777;'>No server manual edits lines found.</div>")

        if override_preview:
            body_parts.append("<div style='font-weight:600;color:#0d47a1;margin:10px 0 4px;'>Override preview (Blue/Red)</div>")
        else:
            body_parts.append("<div style='font-weight:600;color:#1e88e5;margin:10px 0 4px;'>Local changes (Blue/Red)</div>")
        if local_lines:
            _append_reflection_lines(body_parts, local_lines, style="override" if override_preview else "normal")
        else:
            body_parts.append("<div style='color:#777;'>No local change lines found.</div>")
    else:
        lines_to_render = _lines_for_reflection(direct_lines, changes_only)
        if lines_to_render:
            _append_reflection_lines(body_parts, lines_to_render, style="override" if override_preview else "normal")
        else:
            body_parts.append("<div style='color:#777;'>No differences to reflect.</div>")

    body_parts.append("</div>")
    return f"{_DIFF_REFLECT_START}{''.join(body_parts)}{_DIFF_REFLECT_END}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Standalone compare + drift guard checker (storage + markdown)"
    )
    parser.add_argument("--project-root", default=r"C:\confluence-api-project", help="Project root for importing existing modules")
    parser.add_argument("--page-id", required=True, help="Confluence page ID to check")
    parser.add_argument("--md-path", required=True, help="Local markdown file path")
    parser.add_argument("--heading-title", default=None, help="Heading title to match (defaults to page title)")
    parser.add_argument("--split-level", type=int, default=1, choices=range(1, 7), help="Heading level split for local markdown")
    parser.add_argument("--anchor-start-name", default=_DEFAULT_MANAGED_ANCHOR_START, help="Confluence Anchor macro name marking the start of the managed document region")
    parser.add_argument("--anchor-end-name", default=_DEFAULT_MANAGED_ANCHOR_END, help="Confluence Anchor macro name marking the end of the managed document region")
    parser.add_argument("--context-lines", type=int, default=3, help="Unified diff context lines")
    parser.add_argument(
        "--compare-mode",
        choices=["markdown", "storage", "both"],
        default="both",
        help="Compare mode: markdown-to-markdown, html-to-html(storage), or both",
    )
    parser.add_argument("--marker-key", default="docAsCode.lastPublishMarker", help="Confluence content-property key for last publish marker")
    parser.add_argument("--force-scdp-override", action="store_true", help="Allow override when drift is detected")
    parser.add_argument("--no-prompt-override", action="store_true", help="Do not ask for override interactively")
    parser.add_argument("--no-prompt-missing-heading", action="store_true", help="Do not ask for alternate heading when requested one is missing")
    parser.add_argument("--allow-full-page-fallback", action="store_true", help="Allow fallback to full-page overwrite when a safe heading-scoped publish is not possible")
    parser.add_argument("--apply", action="store_true", help="Update the same SCDP page after compare if allowed")
    parser.add_argument("--yes", action="store_true", help="Skip final update confirmation prompt")
    parser.add_argument("--yes-override", action="store_true", help="Skip override confirmation prompt (only with --apply and --force-scdp-override)")
    parser.add_argument("--publisher-id", default="doc-as-code", help="Publisher id to store when marker is refreshed")
    parser.add_argument("--show-full-diff", action="store_true", help="Print full unified diffs")
    parser.add_argument("--show-human-preview", action="store_true", help="Print human-readable diff preview in terminal")
    parser.add_argument("--output-json", default=None, help="Optional path to save full result JSON")
    parser.add_argument("--reflect-on-page", action="store_true", help="Temporarily highlight color changes directly in-place on SCDP page")
    parser.add_argument("--reflect-mode", choices=["markdown", "storage"], default="markdown", help="Reflection diff mode for on-page preview")
    parser.add_argument("--reflect-changes-only", action="store_true", help="When reflecting on page, show only changed lines")
    parser.add_argument("--reflect-auto-clear-seconds", type=int, default=20, help="Auto-remove reflection highlights after N seconds (0 = keep until manual clear)")
    parser.add_argument("--reflect-keep-after-refresh", action="store_true", help="Keep highlight colors visible after page refresh (do not inject cleanup-on-reload script)")
    parser.add_argument("--post-update-clear-seconds", type=int, default=30, help="Auto-remove POST-UPDATE highlights after N seconds (default 30s, 0 = keep). Separate from --reflect-auto-clear-seconds to avoid long waits.")
    parser.add_argument("--reflect-persist-manual", action="store_true", help="Keep manual-edit highlights until override/update")
    parser.add_argument("--cleanup-after-clear", action="store_true", help="Clear highlights using cleanup API after auto-clear timeout")
    parser.add_argument("--force-rehighlight", action="store_true", help="Re-apply highlights even if changes were already reviewed")
    parser.add_argument(
        "--reflect-compare-latest-previous",
        action="store_true",
        help="For manual-edit reflection, also compare latest page version vs previous version and merge those changes for highlighting",
    )
    parser.add_argument("--quiet-output", action="store_true", help="Minimal output for user display (just YES/NO + key results)")
    args = parser.parse_args()

    persist_manual_highlights = bool(args.reflect_persist_manual)
    keep_after_refresh = bool(args.reflect_keep_after_refresh)
    effective_reflect_clear_seconds = 0 if persist_manual_highlights else int(args.reflect_auto_clear_seconds)
    effective_post_update_clear_seconds = 0 if persist_manual_highlights else int(getattr(args, "post_update_clear_seconds", 30))

    # Force UTF-8 for stdout/stderr so emoji/unicode print correctly on Windows
    # (covers both direct console and PowerShell pipe scenarios).
    try:
        import io as _io
        if hasattr(sys.stdout, "buffer"):
            sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
        if hasattr(sys.stderr, "buffer"):
            sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass

    if not os.path.exists(args.md_path):
        raise SystemExit(f"File not found: {args.md_path}")

    _add_project_to_path(args.project_root)

    global build_diff, build_publish_marker, content_hash, convert_storage_to_markdown
    global get_page_marker, parse_marker_value, upsert_page_marker, try_highlight_text_block, try_highlight_replaced_text_block
    from confluence_client import ConfluenceClient
    from markdown_h1_splitter import MarkdownH1Splitter
    from safe_block_highlighter import try_highlight_text_block, try_highlight_replaced_text_block
    from version_compare_reflector import build_latest_previous_markdown_changes
    from tools.h1_diff_before_push import (
        build_diff,
        build_publish_marker,
        content_hash,
        convert_storage_to_markdown,
        get_page_marker,
        parse_marker_value,
        upsert_page_marker,
    )

    client = ConfluenceClient()
    splitter = MarkdownH1Splitter()

    page = _get_page_with_retry(client, str(args.page_id), attempts=2, delay_seconds=2.0)
    if not page:
        raise SystemExit(
            f"Unable to fetch page {args.page_id}. Cause may be network timeout, auth issue, or invalid page id. "
            "Please re-run and verify SCDP connectivity/auth."
        )

    page_title = str(page.get("title") or "")
    current_version = int((page.get("version") or {}).get("number") or 0)
    raw_previous_storage = ((page.get("body") or {}).get("storage") or {}).get("value", "")
    previous_storage = _strip_inline_highlights(_strip_existing_diff_reflection_block(raw_previous_storage))
    reflection_present_on_page = previous_storage != (raw_previous_storage or "").strip()

    sections = splitter.parse_sections(args.md_path, split_level=args.split_level)
    full_page_requested = str(args.heading_title or "").strip() == _FULL_PAGE_AUTO_SENTINEL
    anchor_region_requested = str(args.heading_title or "").strip() == _ANCHOR_REGION_AUTO_SENTINEL
    target_title = (args.heading_title or page_title).strip().lower()
    if full_page_requested or anchor_region_requested:
        with open(args.md_path, "r", encoding="utf-8") as _md_file:
            section_markdown_body = _md_file.read()
        section_title = page_title.strip() or "Document"
        current_markdown = section_markdown_body.strip() + ("\n" if section_markdown_body.strip() else "")
    else:
        local_section = _resolve_heading_title(
            sections=sections,
            requested_title=(args.heading_title or page_title),
            no_prompt_missing_heading=bool(args.no_prompt_missing_heading),
        )
        if local_section is None:
            available = [str(section.get("title", "")) for section in sections]
            raise SystemExit(
                f"Heading '{target_title}' not found in {args.md_path}. Available headings: {available}"
            )

        section_title = str(local_section.get("title") or page_title).strip() or page_title
        section_markdown_body = str(local_section.get("markdown") or "")
        current_markdown = section_markdown_body.strip() + ("\n" if section_markdown_body.strip() else "")

    image_src_map: Dict[str, Any] = {}
    try:
        source_dir = os.path.dirname(os.path.abspath(args.md_path))
        section_images = splitter._extract_markdown_images(section_markdown_body)
        uploaded_seen = set()
        page_attachment_names: Optional[List[str]] = None

        def _normalized_name_key(name: str) -> str:
            return re.sub(r"[^a-z0-9]", "", str(name or "").lower())

        def _load_page_attachment_names() -> List[str]:
            nonlocal page_attachment_names
            if page_attachment_names is not None:
                return page_attachment_names
            names: List[str] = []
            try:
                start = 0
                while True:
                    payload = client._request_json(
                        "GET",
                        f"{client.base_url}/content/{args.page_id}/child/attachment",
                        f"list attachments on page {args.page_id}",
                        params={"start": start, "limit": 200},
                    ) or {}
                    results = list(payload.get("results") or [])
                    for item in results:
                        title = str(item.get("title") or "").strip()
                        if title:
                            names.append(title)
                    if len(results) < 200:
                        break
                    start += 200
            except Exception:
                names = []
            page_attachment_names = names
            return names

        for image in section_images:
            target = str((image or {}).get("target") or "").strip()
            if not target or target in uploaded_seen:
                continue
            uploaded_seen.add(target)

            normalized_target = splitter._normalize_markdown_image_target(target)

            def _map_existing_attachment_if_any(target_value: str) -> bool:
                candidate_name = os.path.basename(str(target_value or "").replace("\\", "/").split("?")[0]).strip()
                if not candidate_name:
                    return False
                try:
                    existing = client._get_attachment_by_filename(str(args.page_id), candidate_name)
                except Exception:
                    existing = None
                if not existing:
                    wanted_key = _normalized_name_key(candidate_name)
                    if wanted_key:
                        for attachment_name in _load_page_attachment_names():
                            if _normalized_name_key(attachment_name) == wanted_key:
                                try:
                                    existing = client._get_attachment_by_filename(str(args.page_id), attachment_name)
                                except Exception:
                                    existing = None
                                break
                if not existing:
                    return False
                existing_name = str(existing.get("title") or candidate_name)
                attachment_ref = {"type": "attachment", "filename": existing_name}
                image_src_map[target_value] = attachment_ref
                image_src_map[normalized_target] = attachment_ref
                return True

            def _map_absolute_url_fallback(target_value: str) -> bool:
                candidate_name = os.path.basename(str(target_value or "").replace("\\", "/").split("?")[0]).strip()
                if not candidate_name:
                    return False
                web_base = re.sub(r"/rest/api/?$", "", str(client.base_url).rstrip("/"), flags=re.IGNORECASE)
                fallback_url = f"{web_base}/{candidate_name}"
                image_src_map[target_value] = fallback_url
                image_src_map[normalized_target] = fallback_url
                return True

            if splitter._is_remote_image_target(target):
                lowered = target.lower()
                if lowered.startswith("http://") or lowered.startswith("https://"):
                    file_bytes, remote_content_type, _download_error = splitter._download_remote_image(target)
                    if file_bytes and len(file_bytes) <= splitter.max_image_size_bytes:
                        filename = splitter._filename_from_image_target(target, content_type=remote_content_type)
                        content_type = remote_content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
                        extension = os.path.splitext(filename)[1].lower()
                        if (not extension) or (extension in splitter.supported_image_extensions):
                            upload_result = client.upload_attachment(
                                page_id=str(args.page_id),
                                filename=filename,
                                file_bytes=file_bytes,
                                content_type=content_type,
                            )
                            if upload_result:
                                attachment_ref = {"type": "attachment", "filename": filename}
                                image_src_map[splitter._normalize_markdown_image_target(target)] = attachment_ref
                                image_src_map[target] = attachment_ref
                                continue
                if not _map_existing_attachment_if_any(target):
                    _map_absolute_url_fallback(target)
                continue

            local_path = splitter._resolve_local_image_path(source_dir, target)
            if not local_path:
                if not _map_existing_attachment_if_any(target):
                    _map_absolute_url_fallback(target)
                continue

            is_valid, _reason, _metadata = splitter._validate_local_image_for_upload(local_path)
            if not is_valid:
                if not _map_existing_attachment_if_any(target):
                    _map_absolute_url_fallback(target)
                continue

            try:
                with open(local_path, "rb") as image_file:
                    file_bytes = image_file.read()
            except Exception:
                continue

            filename = os.path.basename(local_path)
            content_type = mimetypes.guess_type(local_path)[0] or "application/octet-stream"
            upload_result = client.upload_attachment(
                page_id=str(args.page_id),
                filename=filename,
                file_bytes=file_bytes,
                content_type=content_type,
            )
            if upload_result:
                attachment_ref = {"type": "attachment", "filename": filename}
                image_src_map[normalized_target] = attachment_ref
                image_src_map[target] = attachment_ref
            else:
                if not _map_existing_attachment_if_any(target):
                    _map_absolute_url_fallback(target)
    except Exception as exc:
        print(f"[WARN] image mapping fallback used after preparation error: {exc}")

    current_storage = splitter.markdown_to_html(section_markdown_body, image_src_map=image_src_map)

    previous_section_storage = previous_storage
    publish_storage = previous_storage
    fallback_full_page_mode = bool(full_page_requested)
    if full_page_requested:
        section_bounds = None
    elif anchor_region_requested:
        section_bounds = _find_anchor_region_bounds(
            previous_storage,
            args.anchor_start_name,
            args.anchor_end_name,
        )
    else:
        section_bounds = _find_heading_section_bounds(
            previous_storage,
            section_title,
            heading_level=args.split_level,
        )
    if section_bounds is not None:
        body_start = int(section_bounds["body_start"])
        section_end = int(section_bounds["section_end"])
        previous_section_storage = previous_storage[body_start:section_end]
        if anchor_region_requested:
            replaced = _replace_anchor_region_body(
                previous_storage,
                current_storage,
                args.anchor_start_name,
                args.anchor_end_name,
            )
        else:
            replaced = _replace_heading_section_body(
                previous_storage,
                section_title,
                current_storage,
                heading_level=args.split_level,
            )
        if replaced is not None:
            publish_storage = replaced
    else:
        # Some Confluence pages render headings through macros/div wrappers instead
        # of native h1..h6 tags. Only switch to full-page mode when explicitly allowed.
        fallback_full_page_mode = bool(args.allow_full_page_fallback)
        if not full_page_requested:
            with open(args.md_path, "r", encoding="utf-8") as _md_file:
                full_markdown_body = _md_file.read()
            current_markdown = full_markdown_body.strip() + ("\n" if full_markdown_body.strip() else "")
            current_storage = splitter.markdown_to_html(full_markdown_body)
        previous_section_storage = previous_storage
        publish_storage = current_storage

    previous_markdown = convert_storage_to_markdown(previous_section_storage)
    reflection_base_html = previous_storage
    defer_manual_preview_clear = False

    storage_diff = build_diff(
        before_text=previous_section_storage,
        after_text=current_storage,
        title=section_title,
        context=int(args.context_lines),
        mode="storage",
    )
    markdown_diff = build_diff(
        before_text=previous_markdown,
        after_text=current_markdown,
        title=section_title,
        context=int(args.context_lines),
        mode="markdown",
    )

    marker_obj = get_page_marker(client, str(args.page_id), str(args.marker_key))
    marker = parse_marker_value(marker_obj)
    last_hash = str(marker.get("published_content_hash")) if marker and marker.get("published_content_hash") else None
    last_reflection_live_hash = str(marker.get("last_reflection_live_hash")) if marker and marker.get("last_reflection_live_hash") else None
    live_hash = content_hash(previous_storage)
    baseline_storage = None
    baseline_markdown = None
    if marker:
        baseline_storage = marker.get("published_content_storage_html")
        _raw_baseline_md = marker.get("published_content_markdown")
        baseline_markdown = _decompress_text(_raw_baseline_md) if _raw_baseline_md else None
        if baseline_markdown is None and isinstance(baseline_storage, str) and baseline_storage.strip():
            try:
                baseline_markdown = convert_storage_to_markdown(str(baseline_storage))
            except Exception:
                baseline_markdown = None

    if not last_hash:
        guard_status = "no_marker"
        safe_to_publish = True
        drift = False
    else:
        drift = last_hash != live_hash
        guard_status = "drift" if drift else "clean"
        safe_to_publish = not drift

    override_allowed = False
    # Only ask override confirmation when an update can actually happen.
    if drift and bool(args.apply):
        override_allowed = _choose_override(
            force_override=bool(args.force_scdp_override),
            prompt_override=not bool(args.no_prompt_override),
        )

    decision = {
        "can_publish_without_override": safe_to_publish,
        "override_required": bool(drift),
        "override_allowed": bool(override_allowed),
        "final_allowed": bool(safe_to_publish or override_allowed),
    }

    storage_summary = _summary_for_pair(previous_section_storage, current_storage, storage_diff)
    markdown_summary = _summary_for_pair(previous_markdown, current_markdown, markdown_diff)
    semantic_markdown_equal = (
        _normalize_markdown_document_for_semantic_compare(previous_markdown)
        == _normalize_markdown_document_for_semantic_compare(current_markdown)
    )
    local_knows_changes = {
        "storage_mode_has_changes": bool(storage_summary["has_changes"]),
        "markdown_mode_has_changes": bool(markdown_summary["has_changes"]),
        "local_matches_live_storage": not bool(storage_summary["has_changes"]),
        "local_matches_live_markdown": not bool(markdown_summary["has_changes"]),
        "semantic_markdown_equal": bool(semantic_markdown_equal),
        "section_found_in_page": bool(section_bounds is not None),
        "fallback_full_page_mode": bool(fallback_full_page_mode),
    }
    baseline_available = bool(
        (isinstance(baseline_storage, str) and baseline_storage.strip())
        or (isinstance(baseline_markdown, str) and baseline_markdown.strip())
    )
    since_last_publish = {
        "baseline_available": baseline_available,
        "message": (
            "Exact 3-way colors available because last published content snapshot exists."
            if baseline_available
            else "Exact server-edit vs local-delete split is unavailable until a new publish stores baseline content snapshot."
        ),
        "server_edits": {
            "markdown": _build_compare_block(
                baseline_markdown,
                previous_markdown,
                section_title,
                int(args.context_lines),
                "markdown",
            ),
            "storage": _build_compare_block(
                baseline_storage,
                previous_storage,
                section_title,
                int(args.context_lines),
                "storage",
            ),
        },
        "local_changes": {
            "markdown": _build_compare_block(
                baseline_markdown,
                current_markdown,
                section_title,
                int(args.context_lines),
                "markdown",
            ),
            "storage": _build_compare_block(
                baseline_storage,
                current_storage,
                section_title,
                int(args.context_lines),
                "storage",
            ),
        },
    }

    # Build friendly URL from _links.webui (e.g. /spaces/PT2/pages/381463513/Access+Polices)
    _webui = str((page.get("_links") or {}).get("webui") or "")
    _base = str(client.base_url).rstrip("/")
    page_url = _build_user_page_url(_base, _webui, str(args.page_id))

    result: Dict[str, Any] = {
        "mode": "compare+guard",
        "page_id": str(args.page_id),
        "page_title": page_title,
        "page_version": current_version,
        "page_url": page_url,
        "heading_matched": section_title,
        "heading_found_in_live_storage": bool(section_bounds is not None),
        "fallback_full_page_mode": bool(fallback_full_page_mode),
        "guard": {
            "status": guard_status,
            "safe_to_publish": safe_to_publish,
            "drift": drift,
            "marker_key": str(args.marker_key),
            "last_published_hash": last_hash,
            "current_live_hash": live_hash,
            "last_published_version": marker.get("published_page_version") if marker else None,
            "last_published_at": marker.get("published_at") if marker else None,
            "last_published_by": marker.get("published_by") if marker else None,
        },
        "decision": decision,
        "compare": {
            "storage": {
                "summary": storage_summary,
                "diff_lines": storage_diff,
                "human_readable_preview": _human_readable_diff(storage_diff),
            },
            "markdown": {
                "summary": markdown_summary,
                "diff_lines": markdown_diff,
                "human_readable_preview": _human_readable_diff(markdown_diff),
            },
        },
        "local_knows_changes": local_knows_changes,
        "since_last_publish": since_last_publish,
    }

    quick_summary = {
        "guard_status": result["guard"]["status"],
        "safe_to_publish": result["guard"]["safe_to_publish"],
        "override_allowed": result["decision"]["override_allowed"],
        "final_allowed": result["decision"]["final_allowed"],
        "storage_summary": result["compare"]["storage"]["summary"],
        "markdown_summary": result["compare"]["markdown"]["summary"],
        "local_knows_changes": result["local_knows_changes"],
    }

    page_url = result["page_url"]

    if not args.quiet_output:
        print("\n=== QUICK SUMMARY ===")
        print(json.dumps(quick_summary, indent=2))
        print(f"\n🔗 View page on SCDP: {page_url}")
        if reflection_present_on_page:
            print("ℹ️ Existing temporary reflection block detected on page and ignored for compare/guard logic.")

        print("\n=== FLOW STATUS ===")
        print("1) Compare first: ✅ done")
        print(f"2) Detect manual online edits: {'⚠️ drift detected' if drift else '✅ clean'}")
        print("3) Ask before overwriting: ✅ enforced in apply mode")
        print("4) Cancel if user not fine: ✅ available (answer 'n')")
        print("5) Update only if approved: ✅ enforced")
        print("6) Store fresh marker after successful update: ✅ enforced")

        readable_page_vs_local = _collect_net_changes(previous_markdown, current_markdown)
        _print_simple_readable_changes(
            title="HUMAN READABLE DIFFERENCE (Current page vs Local markdown)",
            changes=readable_page_vs_local,
            limit=12,
        )

        if drift and baseline_markdown and baseline_markdown.strip():
            readable_manual = _collect_net_changes(baseline_markdown, previous_markdown)
            _print_simple_readable_changes(
                title="MANUAL ONLINE EDITS (Last published baseline vs Current page)",
                changes=readable_manual,
                limit=12,
            )

        markdown_preview = ((result.get("compare") or {}).get("markdown") or {}).get("human_readable_preview") or []
        if args.show_human_preview and markdown_preview:
            print("\n=== HUMAN READABLE DIFF PREVIEW (markdown) ===")
            for item in markdown_preview[:25]:
                item_type = item.get("type")
                text = str(item.get("text") or "")
                if item_type == "location":
                    print(f"  [where] {text}")
                elif item_type == "added":
                    print(f"  [+ add] {text}")
                elif item_type == "deleted":
                    print(f"  [- del] {text}")

    if args.reflect_on_page:
        base_html = reflection_base_html
        reflected_body = None
        reflection_mode = "none"
        update_preview_overlay = ""
        # When applying (--apply), show UPDATE PREVIEW: what the local file will push to the page.
        # When checking only (no --apply) and drift detected, show MANUAL EDIT highlights: what changed online.
        reflect_update_preview = bool((not args.apply) or (args.apply and decision.get("final_allowed")))
        if args.apply and semantic_markdown_equal:
            reflect_update_preview = False

        # Determine what to compare and highlight
        # Priority:
        #   1. In apply mode + drift, show MANUAL EDIT highlights first (what changed online since last publish)
        #   2. In apply mode without drift, show UPDATE PREVIEW (what local markdown will push)
        #   3. In check-only mode + drift, show MANUAL EDIT highlights
        if args.apply and semantic_markdown_equal:
            reflected_body = None
        elif args.apply and drift and baseline_markdown and baseline_markdown.strip():
            # Apply mode with drift: make manual online edits highly visible before user decides override/cancel.
            manual_changes = _collect_net_changes(baseline_markdown, previous_markdown)
            manual_storage_image_changes = _collect_storage_image_changes(
                str(baseline_storage or ""),
                str(previous_storage or ""),
            )
            manual_changes = _merge_change_sets(manual_changes, manual_storage_image_changes)
            manual_storage_table_changes = _collect_storage_table_changes(
                str(baseline_storage or ""),
                str(previous_storage or ""),
            )
            manual_changes = _merge_change_sets(manual_changes, manual_storage_table_changes)
            if bool(args.reflect_compare_latest_previous):
                version_changes_payload = build_latest_previous_markdown_changes(
                    client=client,
                    page_id=str(args.page_id),
                    convert_storage_to_markdown=convert_storage_to_markdown,
                    collect_net_changes=_collect_net_changes,
                )
                if version_changes_payload.get("available"):
                    manual_changes = _merge_change_sets(
                        manual_changes,
                        dict(version_changes_payload.get("changes") or {}),
                    )
                    print(
                        "   [INFO] Merged latest-vs-previous version diff "
                        f"(v{int(version_changes_payload.get('previous_version') or 0)} -> v{int(version_changes_payload.get('latest_version') or 0)}) for manual highlight coverage."
                    )
            reflected_body = _apply_highlights_with_optional_cleanup(
                storage_html=base_html,
                added_lines=manual_changes["added"],
                deleted_lines=manual_changes["deleted"],
                replaced_lines=manual_changes.get("replaced") or [],
                auto_cleanup_on_reload=not keep_after_refresh,
                baseline_storage_html=str(baseline_storage or ""),
                strict_structural_scope=True,
            )
            reflection_label = "Manual edits detected (last published → current SCDP)"
            reflection_colors = "Green=added online, Red strike=deleted online, Blue=formatting/updated online"
            reflection_mode = "manual"
        elif args.apply and reflect_update_preview:
            # Update preview: live page vs updated local content
            update_changes = _collect_net_changes(previous_markdown, current_markdown)
            update_storage_image_changes = _collect_storage_image_changes(
                str(previous_storage or ""),
                str(current_storage or ""),
            )
            update_changes = _merge_change_sets(update_changes, update_storage_image_changes)
            update_storage_table_changes = _collect_storage_table_changes(
                str(previous_storage or ""),
                str(current_storage or ""),
            )
            update_changes = _merge_change_sets(update_changes, update_storage_table_changes)
            reflected_body = _apply_highlights_with_optional_cleanup(
                storage_html=base_html,
                added_lines=update_changes["added"],
                deleted_lines=update_changes["deleted"],
                replaced_lines=update_changes.get("replaced") or [],
                auto_cleanup_on_reload=not keep_after_refresh,
            )
            update_preview_overlay = _build_update_preview_overlay(
                added_lines=update_changes["added"],
                deleted_lines=update_changes["deleted"],
                replaced_lines=update_changes.get("replaced") or [],
                limit=40,
            )
            if update_preview_overlay:
                reflected_body = (reflected_body or base_html) + "\n" + update_preview_overlay
            reflection_label = "Update preview (current page → local markdown)"
            reflection_colors = "Green=will be added, Red strike=will be deleted, Blue=will be formatting/updated"
            reflection_mode = "update"
        elif (not args.apply) and drift and baseline_markdown and baseline_markdown.strip():
            # Check-only mode with drift: show manual edit highlights (what changed online since last publish)
            same_as_last_review = bool(
                (not bool(args.reflect_persist_manual))
                and (not bool(args.force_rehighlight))
                and last_reflection_live_hash
                and last_reflection_live_hash == live_hash
            )
            if same_as_last_review:
                if reflection_present_on_page:
                    cleared_existing = client.update_page(str(args.page_id), base_html)
                    if cleared_existing:
                        cleared_ver = int((cleared_existing.get("version") or {}).get("number") or current_version)
                        print(f"\n🧹 Cleared previous temporary highlights (version {cleared_ver}).")
                print("ℹ️ No new manual online edits since your last review — skipping old highlights.")
                reflected_body = None
            else:
                # Manual edit review: baseline (last published) vs live (current SCDP edits)
                manual_changes = _collect_net_changes(baseline_markdown, previous_markdown)
                manual_storage_image_changes = _collect_storage_image_changes(
                    str(baseline_storage or ""),
                    str(previous_storage or ""),
                )
                manual_changes = _merge_change_sets(manual_changes, manual_storage_image_changes)
                manual_storage_table_changes = _collect_storage_table_changes(
                    str(baseline_storage or ""),
                    str(previous_storage or ""),
                )
                manual_changes = _merge_change_sets(manual_changes, manual_storage_table_changes)
                if bool(args.reflect_compare_latest_previous):
                    version_changes_payload = build_latest_previous_markdown_changes(
                        client=client,
                        page_id=str(args.page_id),
                        convert_storage_to_markdown=convert_storage_to_markdown,
                        collect_net_changes=_collect_net_changes,
                    )
                    if version_changes_payload.get("available"):
                        manual_changes = _merge_change_sets(
                            manual_changes,
                            dict(version_changes_payload.get("changes") or {}),
                        )
                        print(
                            "   [INFO] Merged latest-vs-previous version diff "
                            f"(v{int(version_changes_payload.get('previous_version') or 0)} -> v{int(version_changes_payload.get('latest_version') or 0)}) for manual highlight coverage."
                        )
                reflected_body = _apply_highlights_with_optional_cleanup(
                    storage_html=base_html,
                    added_lines=manual_changes["added"],
                    deleted_lines=manual_changes["deleted"],
                    replaced_lines=manual_changes.get("replaced") or [],
                    auto_cleanup_on_reload=not keep_after_refresh,
                    baseline_storage_html=str(baseline_storage or ""),
                    strict_structural_scope=True,
                )
                reflection_label = "Manual edits detected (last published → current SCDP)"
                reflection_colors = "Green=added online, Red strike=deleted online, Blue=formatting/updated online"
                reflection_mode = "manual"
        else:
            reflected_body = None

        if not reflected_body or not reflected_body.strip() or reflected_body == base_html:
            print("\nℹ️  No real content changes found — nothing to highlight.")
        else:
            marker_count = len(re.findall(r"data-dac=['\"]hl['\"]", reflected_body, flags=re.IGNORECASE))
            reflected_page = client.update_page(str(args.page_id), reflected_body)
            if reflected_page:
                reflected_ver = int((reflected_page.get("version") or {}).get("number") or current_version)
                print(f"\n🎨 Highlights applied in-place on page (version {reflected_ver}).")
                print(f"   {reflection_label}")
                print(f"   {reflection_colors}")
                print(f"   Highlight markers injected: {marker_count}")
                if drift and reflection_mode == "manual" and not bool(args.reflect_persist_manual):
                    persisted = _persist_last_reflection_hash(
                        client=client,
                        page_id=str(args.page_id),
                        marker_key=str(args.marker_key),
                        marker=marker,
                        live_hash=live_hash,
                    )
                    if persisted:
                        print("   ✅ Saved review checkpoint (old edits won't re-highlight on next check unless page changes).")
                elif drift and reflection_mode == "manual" and bool(args.reflect_persist_manual):
                    print("   📌 Manual review remains re-checkable until override/update.")
            else:
                print("\n⚠️ Could not apply highlights to SCDP page.")

            # Keep manual-edit highlights only when explicitly requested.
            # Default behavior: highlight colors auto-clear based on --reflect-auto-clear-seconds.
            keep_until_override = bool(
                drift
                and reflection_mode == "manual"
                and bool(args.reflect_persist_manual)
            )
            if (args.apply and drift and reflection_mode == "manual" and not keep_until_override):
                # In apply+manual-drift flow, keep colors visible through the user decision prompt.
                # Clear later only if update is canceled/rejected.
                defer_manual_preview_clear = True
                print("   📌 Highlights kept for decision step (will clear if update is canceled).")
            elif keep_until_override:
                print("   📌 Highlights kept on page until override/update (manual edits detected).")
            elif effective_reflect_clear_seconds > 0:
                time.sleep(effective_reflect_clear_seconds)
                cleared_page = client.update_page(str(args.page_id), base_html)
                if cleared_page:
                    cleared_ver = int((cleared_page.get("version") or {}).get("number") or 0)
                    print(f"   🧹 Highlights cleared (version {cleared_ver}).")
                    
                    # Run cleanup script if requested
                    if args.cleanup_after_clear:
                        try:
                            cleanup_script = os.path.join(os.path.dirname(__file__), "highlight_cleanup.py")
                            # Get credentials from client instead of args
                            base_url = client.base_url
                            # Extract API token or username from client
                            api_token = client.access_token or ""
                            username = client.username or ""
                            
                            cleanup_cmd = [
                                get_python_executable(),
                                cleanup_script,
                                str(args.page_id),
                                "--base-url", base_url,
                                "--username", username,
                                "--api-token", api_token,
                            ]
                            if args.project_root:
                                cleanup_cmd.extend(["--project-root", args.project_root])
                            
                            result = subprocess.run(cleanup_cmd, capture_output=True, text=True, timeout=30)
                            if result.returncode == 0:
                                print("   ✨ Cleanup completed successfully.")
                            else:
                                print(f"   ⚠️ Cleanup script exited with code {result.returncode}.")
                                if result.stderr:
                                    print(f"      Error: {result.stderr[:200]}")
                        except Exception as e:
                            print(f"   ⚠️ Cleanup script error: {e}")
                else:
                    print("   ⚠️ Auto-clear attempted but failed.")
            else:
                print("   📌 Highlights kept on page (auto-clear disabled by --reflect-auto-clear-seconds 0).")

    if args.show_full_diff:
        print("\n=== STORAGE DIFF ===")
        print("\n".join(storage_diff) if storage_diff else "(no storage diff)")
        print("\n=== MARKDOWN DIFF ===")
        print("\n".join(markdown_diff) if markdown_diff else "(no markdown diff)")

    if args.output_json:
        with open(args.output_json, "w", encoding="utf-8") as file_obj:
            json.dump(result, file_obj, indent=2)
        print(f"\nSaved full result JSON: {args.output_json}")
        
        # Auto-generate HTML report alongside JSON
        if generate_html_report:
            html_output = args.output_json.replace(".json", ".html")
            try:
                generate_html_report(result, html_output)
            except Exception as e:
                print(f"⚠️ Warning: Could not generate HTML report: {e}")

    if args.apply:
        def _clear_deferred_manual_preview(immediate: bool = False) -> None:
            if not defer_manual_preview_clear:
                return
            if not immediate and effective_reflect_clear_seconds <= 0:
                return
            if not immediate:
                time.sleep(effective_reflect_clear_seconds)
            cleared_page = client.update_page(str(args.page_id), reflection_base_html)
            if cleared_page:
                cleared_ver = int((cleared_page.get("version") or {}).get("number") or 0)
                print(f"   🧹 Deferred highlights cleared (version {cleared_ver}).")
                if args.cleanup_after_clear:
                    try:
                        cleanup_script = os.path.join(os.path.dirname(__file__), "highlight_cleanup.py")
                        cleanup_cmd = [
                            get_python_executable(),
                            cleanup_script,
                            str(args.page_id),
                            "--base-url", client.base_url,
                            "--username", (client.username or ""),
                            "--api-token", (client.access_token or ""),
                        ]
                        if args.project_root:
                            cleanup_cmd.extend(["--project-root", args.project_root])
                        result_cleanup = subprocess.run(cleanup_cmd, capture_output=True, text=True, timeout=30)
                        if result_cleanup.returncode == 0:
                            print("   ✨ Deferred cleanup completed successfully.")
                    except Exception as e:
                        print(f"   ⚠️ Deferred cleanup script error: {e}")

        # Strict identical-content gate: if live page markdown and local markdown are
        # semantically equal, skip update even when formatter/storage noise exists.
        if semantic_markdown_equal:
            print("\nNo meaningful document changes found (Doc-as-Code and live SCDP are identical). Skipping page update.")
            _clear_deferred_manual_preview()
            return

        compare_mode = str(args.compare_mode)
        if compare_mode == "markdown":
            has_changes_for_apply = bool(markdown_summary["has_changes"])
            apply_mode_text = "markdown"
        elif compare_mode == "storage":
            has_changes_for_apply = bool(storage_summary["has_changes"])
            apply_mode_text = "storage"
        else:
            has_changes_for_apply = bool(markdown_summary["has_changes"] or storage_summary["has_changes"])
            apply_mode_text = "both"

        if not has_changes_for_apply:
            print(f"\nNo {apply_mode_text} changes found. Skipping page update.")
            _clear_deferred_manual_preview()
            return

        if section_bounds is None and not fallback_full_page_mode:
            if anchor_region_requested:
                print(
                    "\n⛔ Update blocked: managed anchor region was not found in live page storage. "
                    "Refusing full-page overwrite for safety. Rerun with --allow-full-page-fallback only if you intend to replace the whole page."
                )
            else:
                print(
                    "\n⛔ Update blocked: target heading section was not found in live page storage. "
                    "Refusing full-page overwrite for safety. Rerun with --allow-full-page-fallback only if you intend to replace the whole page."
                )
            _clear_deferred_manual_preview()
            return

        if fallback_full_page_mode:
            if full_page_requested:
                print("\n⚠️ Auto heading resolution detected deleted or renamed headings; using guarded full-page mode.")
            elif anchor_region_requested:
                print(
                    "\n⚠️ Managed anchor region was not found in live storage; using guarded full-page fallback mode."
                )
            else:
                print(
                    "\n⚠️ Heading section not found in live storage tags; using guarded full-page fallback mode."
                )

        if not decision["final_allowed"]:
            print("\n⛔ Update blocked: direct online edits detected and override not allowed.")
            _clear_deferred_manual_preview()
            return

        if not _choose_update(bool(args.yes), quiet_output=bool(args.quiet_output)):
            if args.quiet_output:
                print("NO")
            else:
                print("\nUpdate canceled by user.")
            _clear_deferred_manual_preview()
            return

        # SAFETY GATE: Explicitly ask for override confirmation when drift is detected,
        # even if --force-scdp-override was used. Only skip if --yes-override is passed.
        override_already_confirmed = bool(drift and override_allowed and not bool(args.force_scdp_override))
        if not _confirm_override_before_update(
            drift=bool(drift),
            yes_override=bool(args.yes_override),
            override_already_confirmed=override_already_confirmed,
        ):
            print("\n⛔ Override confirmation rejected. Update canceled.")
            _clear_deferred_manual_preview()
            return

        updated_page, action = client.create_or_update_page(
            title=page_title,
            content=publish_storage,
            existing_page=page,
            fast_update=True,
            allow_space_fallback=False,
        )
        if not updated_page:
            raise SystemExit("Failed to update page in SCDP.")

        updated_page_id = str(updated_page.get("id") or args.page_id)
        stored_page = _get_page_with_retry(client, updated_page_id, attempts=2, delay_seconds=1.5) or updated_page
        stored_html = ((stored_page.get("body") or {}).get("storage") or {}).get("value", current_storage)
        stored_version = ((stored_page.get("version") or {}).get("number"))
        # Keep marker hash/storage on the same normalized basis used by drift check.
        # Drift check hashes previous_storage after stripping temporary reflection/highlight artifacts.
        canonical_stored_html = _strip_inline_highlights(_strip_existing_diff_reflection_block(stored_html))

        # Ensure temporary preview colors never persist after a real update.
        # If any highlight artifact remains, immediately save a cleaned page body.
        if canonical_stored_html != stored_html:
            cleaned_page = client.update_page(updated_page_id, canonical_stored_html)
            if cleaned_page:
                stored_page = _get_page_with_retry(client, updated_page_id, attempts=2, delay_seconds=1.0) or cleaned_page
                stored_html = ((stored_page.get("body") or {}).get("storage") or {}).get("value", canonical_stored_html)
                stored_version = ((stored_page.get("version") or {}).get("number"))
                canonical_stored_html = _strip_inline_highlights(_strip_existing_diff_reflection_block(stored_html))
                print("🧹 Cleared temporary highlight styles from saved page content.")

        marker_value = build_publish_marker(page_title, canonical_stored_html, stored_version)
        marker_value["published_by"] = str(args.publisher_id)
        marker_value["published_content_storage_html"] = canonical_stored_html
        section_markdown_map: Dict[str, str] = {}
        existing_section_markdown_map = marker.get("published_section_markdown_by_heading") if isinstance(marker, dict) else None
        if isinstance(existing_section_markdown_map, dict):
            for title, raw_value in existing_section_markdown_map.items():
                title_key = str(title or "").strip()
                if title_key:
                    section_markdown_map[title_key] = str(raw_value or "")
        section_markdown_map[str(section_title)] = _compress_text(current_markdown)
        marker_value["published_section_markdown_by_heading"] = section_markdown_map
        try:
            md_snapshot = convert_storage_to_markdown(canonical_stored_html)
            marker_value["published_content_markdown"] = _compress_text(md_snapshot)
        except Exception:
            marker_value["published_content_markdown"] = _compress_text(current_markdown)
        # Build a minimal fallback marker.
        bare_marker = build_publish_marker(page_title, canonical_stored_html, stored_version)
        bare_marker["published_by"] = str(args.publisher_id)

        # Single size-safe write first. If it still fails for server-side reasons,
        # last-resort retry with the bare marker.
        compact_marker = build_publish_marker(page_title, canonical_stored_html, stored_version)
        compact_marker["published_by"] = str(args.publisher_id)
        compact_marker["published_section_markdown_by_heading"] = section_markdown_map
        try:
            compact_md = marker_value.get("published_content_markdown") or _compress_text(current_markdown)
            compact_marker["published_content_markdown"] = compact_md
        except Exception:
            pass

        selected_marker = _pick_marker_payload_by_size(
            full_marker=marker_value,
            compact_marker=compact_marker,
            bare_marker=bare_marker,
            max_bytes=32000,
        )

        marker_ok = upsert_page_marker(client, updated_page_id, str(args.marker_key), selected_marker)
        if not marker_ok and selected_marker is not bare_marker:
            marker_ok = upsert_page_marker(client, updated_page_id, str(args.marker_key), bare_marker)

        if not args.quiet_output:
            print("\n=== UPDATE RESULT ===")
        _updated_webui = str((stored_page.get("_links") or {}).get("webui") or "")
        _live_base = str(client.base_url).rstrip("/")
        live_url = _build_user_page_url(_live_base, _updated_webui, updated_page_id)
        
        update_result = {
            "status": "updated" if action in {"updated", "unchanged"} else action,
            "page_id": updated_page_id,
            "page_version": int((stored_page.get("version") or {}).get("number") or 0),
            "marker_updated": bool(marker_ok),
            "publisher_id": str(args.publisher_id),
            "page_url": live_url,
        }
        
        if args.quiet_output:
            print("YES")
            print(f"Version: {update_result['page_version']}")
            print(f"Marker: {'✅ Updated' if marker_ok else '⚠️ Partial'}")
        else:
            print(json.dumps(update_result, indent=2))
            print(f"\n🔗 Verify your update on SCDP: {live_url}")

        # POST-OVERRIDE HIGHLIGHT: Show what was added/removed by this update
        # so the client can visually verify the changes on the live page.
        if args.reflect_on_page:
            post_changes = _collect_net_changes(previous_markdown, current_markdown)
            post_added = post_changes.get("added") or []
            post_deleted = post_changes.get("deleted") or []
            post_replaced = post_changes.get("replaced") or []
            if post_added or post_deleted or post_replaced:
                post_highlighted = _apply_manual_edit_highlights_to_storage_html(
                    storage_html=canonical_stored_html,
                    added_lines=post_added,
                    deleted_lines=post_deleted,
                    replaced_lines=post_replaced,
                )
                post_marker_count = len(re.findall(r"data-dac=['\"]hl['\"]", post_highlighted, flags=re.IGNORECASE))
                post_reflected = client.update_page(updated_page_id, post_highlighted)
                if post_reflected:
                    post_ver = int((post_reflected.get("version") or {}).get("number") or 0)
                    print(f"\n🎨 Post-update highlights applied (version {post_ver}).")
                    print("   Green=added by this update, Blue=formatting/updated by this update, Red strike=removed by this update")
                    print(f"   Highlight markers injected: {post_marker_count}")
                    # Use dedicated post-update timer (default 30s) to avoid blocking
                    # for the full --reflect-auto-clear-seconds duration after update.
                    clear_secs = effective_post_update_clear_seconds
                    if clear_secs > 0:
                        print(f"   ⏳ Clearing post-update highlights in {clear_secs}s...")
                        time.sleep(clear_secs)
                        post_cleared = client.update_page(updated_page_id, canonical_stored_html)
                        if post_cleared:
                            cleared_ver = int((post_cleared.get("version") or {}).get("number") or 0)
                            print(f"   🧹 Post-update highlights cleared (version {cleared_ver}).")
                        if args.cleanup_after_clear:
                            try:
                                cleanup_script = os.path.join(os.path.dirname(__file__), "highlight_cleanup.py")
                                base_url = client.base_url
                                api_token = client.access_token or ""
                                username = client.username or ""
                                cleanup_cmd = [
                                    get_python_executable(),
                                    cleanup_script,
                                    updated_page_id,
                                    "--base-url", base_url,
                                    "--username", username,
                                    "--api-token", api_token,
                                ]
                                if args.project_root:
                                    cleanup_cmd.extend(["--project-root", args.project_root])
                                result_cleanup = subprocess.run(cleanup_cmd, capture_output=True, text=True, timeout=30)
                                if result_cleanup.returncode == 0:
                                    print("   ✨ Post-update cleanup completed.")
                            except Exception:
                                pass
                    else:
                        print("   📌 Post-update highlights kept on page (auto-clear disabled).")
            else:
                print("\nℹ️  No net content changes to highlight after update.")


if __name__ == "__main__":
    main()
