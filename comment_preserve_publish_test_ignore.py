import argparse
import base64
import datetime as dt
import gzip
import html
import json
import os
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

import requests

DEFAULT_EXPAND = "children.comment,children.comment.body.storage,children.comment.history,children.comment.version"
STORAGE_EXPAND = "body.storage,version,title"
_INLINE_MARKER_RE = re.compile(
    r'<ac:inline-comment-marker\s+ac:ref=(["\'])([^"\']+)\1>(.*?)</ac:inline-comment-marker>',
    re.DOTALL | re.IGNORECASE,
)
_CONTEXT_WINDOW = 80
_MIN_CONTEXT_SCORE = 12
_MIN_CONTEXT_FRAGMENT = 8
_FALLBACK_SEARCH_WINDOW = 120
_MAX_FALLBACK_ANCHOR_CHARS = 220
_MAX_FALLBACK_ANCHOR_NEWLINES = 3
_DELETED_COMMENT_ICON_HTML = "&#128172;"


def _bundled_clone_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "standalone_clone"))


def _load_config_module(project_root: Optional[str]) -> Any:
    if not project_root:
        return None
    try:
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        import config  # type: ignore[reportMissingImports]

        return config
    except Exception:
        return None


def _html_to_plain_text(value: str) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>\s*<p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<li[^>]*>", "- ", text, flags=re.IGNORECASE)
    text = re.sub(r"</li>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    lines = [line.rstrip() for line in text.splitlines()]
    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _auth_strategies(args: argparse.Namespace, config_module: Any) -> List[Tuple[Optional[Tuple[str, str]], Dict[str, str], str]]:
    bearer = args.access_token or getattr(config_module, "ACCESS_TOKEN", "")
    username = args.username or getattr(config_module, "USERNAME", "")
    password = args.token or getattr(config_module, "PASSWORD", "")
    session_cookie = args.session_cookie or getattr(config_module, "SESSION_COOKIE", "")

    strategies: List[Tuple[Optional[Tuple[str, str]], Dict[str, str], str]] = []
    if bearer:
        strategies.append((None, {"Authorization": f"Bearer {bearer}", "Accept": "application/json"}, "bearer"))
    if username and password:
        strategies.append(((username, password), {"Accept": "application/json"}, "basic"))
    if session_cookie:
        strategies.append((None, {"Cookie": session_cookie, "Accept": "application/json"}, "cookie"))
    return strategies


def _fetch_page_comments(base_url: str, page_id: str, auth: Optional[Tuple[str, str]], headers: Dict[str, str]) -> Dict[str, Any]:
    url = f"{base_url.rstrip('/')}/rest/api/content/{page_id}"
    response = requests.get(url, params={"expand": DEFAULT_EXPAND}, auth=auth, headers=headers, timeout=60)
    response.raise_for_status()
    return response.json()


def _extract_comments(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    comments = (((payload.get("children") or {}).get("comment") or {}).get("results") or [])
    output: List[Dict[str, Any]] = []
    for item in comments:
        body_storage = (((item.get("body") or {}).get("storage") or {}).get("value") or "").strip()
        output.append(
            {
                "id": str(item.get("id") or ""),
                "title": item.get("title"),
                "status": item.get("status"),
                "version": ((item.get("version") or {}).get("number")),
                "author": (((item.get("history") or {}).get("createdBy") or {}).get("displayName")),
                "created": ((item.get("history") or {}).get("createdDate")),
                "body_plain": _html_to_plain_text(body_storage),
            }
        )
    return output


def _active_only(comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return only open/active comments (status == 'current'). Resolved ones are intentionally closed and do not need preservation."""
    return [c for c in comments if str(c.get("status") or "").lower() == "current"]


def _separate_by_status(comments: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Separate comments into active (current) and resolved groups."""
    active = [c for c in comments if str(c.get("status") or "").lower() == "current"]
    resolved = [c for c in comments if str(c.get("status") or "").lower() != "current"]
    return active, resolved


def _fetch_comments_with_fallback_auth(args: argparse.Namespace, config_module: Any) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Fetch comments and return (auth_method, all_comments, active_comments)."""
    last_error: Optional[Exception] = None
    for auth, headers, auth_name in _auth_strategies(args, config_module):
        try:
            payload = _fetch_page_comments(args.base_url, args.page_id, auth=auth, headers=headers)
            all_comments = _extract_comments(payload)
            active_comments = _active_only(all_comments)
            return auth_name, all_comments, active_comments
        except Exception as exc:
            last_error = exc

    if last_error:
        raise last_error
    raise RuntimeError("No auth strategy available. Pass --access-token or --username/--token or --session-cookie.")


def _fetch_inline_properties_with_fallback_auth(
    args: argparse.Namespace,
    config_module: Any,
    open_comment_ids: set,
) -> List[Dict[str, str]]:
    """Fetch markerRef/originalSelection for active inline comments.

    This is used only as a fallback when inline marker tags are missing from
    storage HTML but comments still exist in Confluence.
    """
    last_error: Optional[Exception] = None
    for auth, headers, _ in _auth_strategies(args, config_module):
        try:
            url = f"{args.base_url.rstrip('/')}/rest/api/content/{args.page_id}/child/comment"
            resp = requests.get(
                url,
                params={"expand": "extensions.inlineProperties", "limit": 500, "depth": "root"},
                auth=auth,
                headers=headers,
                timeout=60,
            )
            resp.raise_for_status()
            results = (resp.json().get("results") or [])

            output: List[Dict[str, str]] = []
            for item in results:
                comment_id = str(item.get("id") or "").strip()
                if not comment_id or (open_comment_ids and comment_id not in open_comment_ids):
                    continue

                status = str(item.get("status") or "").lower()
                if status and status != "current":
                    continue

                inline_props = ((item.get("extensions") or {}).get("inlineProperties") or {})
                marker_ref = str(inline_props.get("markerRef") or "").strip()
                original_selection = str(inline_props.get("originalSelection") or "").strip()
                if not marker_ref or not original_selection:
                    continue

                output.append(
                    {
                        "comment_id": comment_id,
                        "ref": marker_ref,
                        "anchor_html": original_selection,
                    }
                )
            return output
        except Exception as exc:
            last_error = exc

    if last_error:
        raise last_error
    return []


def _supplement_markers_from_inline_properties(
    storage_html: str,
    section_span: Tuple[int, int],
    existing_markers: List[Dict[str, Any]],
    inline_props: List[Dict[str, str]],
    owned_refs: Optional[set] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """Top-up marker list using inlineProperties when marker tags are missing.

    Only recover anchors that are unique on the page. Inline properties do not
    carry heading ownership, so ambiguous anchors can drift into the wrong
    section during later publishes.
    """
    scope_start, scope_end = section_span
    scope_start = max(0, min(scope_start, len(storage_html)))
    scope_end = max(scope_start, min(scope_end, len(storage_html)))
    search_space = storage_html[scope_start:scope_end]
    if not search_space:
        return existing_markers, 0

    markers = list(existing_markers)
    existing_refs = {str(m.get("ref") or "") for m in markers}
    used_abs_starts = {
        int(m.get("start", -1))
        for m in markers
        if int(m.get("start", -1)) >= 0
    }
    anchor_cursor: Dict[str, int] = {}
    supplemented = 0

    for p in inline_props:
        ref = str(p.get("ref") or "")
        anchor = str(p.get("anchor_html") or "")
        if not ref or not anchor or ref in existing_refs:
            continue

        occurrences = _find_all_occurrences(search_space, anchor)
        if not occurrences:
            continue
        if owned_refs is not None:
            if ref not in owned_refs or len(occurrences) != 1:
                continue
        else:
            page_occurrences = _find_all_occurrences(storage_html, anchor)
            if len(occurrences) != 1 or len(page_occurrences) != 1:
                continue

        start_from = anchor_cursor.get(anchor, 0)
        selected_rel: Optional[int] = None
        selected_idx: Optional[int] = None

        for idx in range(start_from, len(occurrences)):
            rel = occurrences[idx]
            abs_start = scope_start + rel
            if abs_start not in used_abs_starts:
                selected_rel = rel
                selected_idx = idx
                break

        if selected_rel is None:
            for idx, rel in enumerate(occurrences):
                abs_start = scope_start + rel
                if abs_start not in used_abs_starts:
                    selected_rel = rel
                    selected_idx = idx
                    break

        if selected_rel is None:
            continue

        anchor_cursor[anchor] = (selected_idx + 1) if selected_idx is not None else 0
        abs_start = scope_start + selected_rel
        abs_end = abs_start + len(anchor)
        left_context = storage_html[max(0, abs_start - _CONTEXT_WINDOW):abs_start]
        right_context = storage_html[abs_end:min(len(storage_html), abs_end + _CONTEXT_WINDOW)]

        markers.append(
            {
                "ref": ref,
                "anchor_html": anchor,
                "full_tag": "",
                "left_context": left_context,
                "right_context": right_context,
                "start": abs_start,
                "end": abs_end,
            }
        )
        existing_refs.add(ref)
        used_abs_starts.add(abs_start)
        supplemented += 1

    return markers, supplemented


def _iter_json_string_values(value: Any) -> List[str]:
    values: List[str] = []
    stack: List[Any] = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, str):
            values.append(current)
            continue
        if isinstance(current, dict):
            stack.extend(current.values())
            continue
        if isinstance(current, list):
            stack.extend(current)
    return values


def _marker_visible_anchor_text(anchor_html: str) -> str:
    plain = _html_to_plain_text(anchor_html or "").replace("\u200b", "").strip()
    if plain == html.unescape(_DELETED_COMMENT_ICON_HTML):
        return ""
    return plain


def _marker_anchor_quality(marker: Dict[str, Any]) -> Tuple[int, int, int]:
    anchor_html = str(marker.get("anchor_html") or "")
    visible_text = _marker_visible_anchor_text(anchor_html)
    heading_depth = len(marker.get("heading_path") or [])
    return (
        1 if visible_text and "<ac:inline-comment-marker" not in anchor_html.lower() else 0,
        heading_depth,
        len(visible_text),
    )


def _history_file_sort_key(path: str) -> str:
    name = os.path.basename(path)
    parts = name.split("_", 2)
    if len(parts) >= 2:
        return parts[1]
    return name


def _collect_historical_marker_candidates(
    output_dir: str,
    page_id: str,
    refs: set,
) -> Dict[str, List[Dict[str, Any]]]:
    candidates: Dict[str, List[Dict[str, Any]]] = {ref: [] for ref in refs if ref}
    if not refs or not output_dir or not os.path.isdir(output_dir):
        return candidates

    prefix = f"{page_id}_"
    history_files = [
        os.path.join(output_dir, name)
        for name in os.listdir(output_dir)
        if name.startswith(prefix) and name.endswith("_compare_guard.json")
    ]
    history_files.sort(key=_history_file_sort_key, reverse=True)

    for path in history_files:
        try:
            payload = _load_json(path)
            string_values = _iter_json_string_values(payload)
        except Exception:
            continue

        for string_value in string_values:
            if "<ac:inline-comment-marker" not in string_value:
                continue
            if not any(ref in string_value for ref in refs):
                continue

            for marker in _extract_inline_markers(string_value):
                ref = str(marker.get("ref") or "")
                if ref not in refs:
                    continue
                candidate = dict(marker)
                candidate["history_file"] = path
                candidate["history_sort_key"] = _history_file_sort_key(path)
                candidate["heading_path"] = _heading_path_at_index(string_value, int(candidate.get("start", -1)))
                candidates.setdefault(ref, []).append(candidate)

    return candidates


def _enrich_markers_from_history(
    output_dir: str,
    page_id: str,
    heading_title: str,
    markers: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], int]:
    if not markers:
        return markers, 0

    target_heading = _normalize_heading_text(heading_title)
    refs = {str(marker.get("ref") or "") for marker in markers if marker.get("ref")}
    history_candidates = _collect_historical_marker_candidates(output_dir, page_id, refs)
    updated_markers: List[Dict[str, Any]] = []
    enriched_count = 0

    for marker in markers:
        ref = str(marker.get("ref") or "")
        updated = dict(marker)
        current_heading_path = updated.get("heading_path") or []
        current_in_target_heading = any(
            str(item.get("normalized_text") or "") == target_heading for item in current_heading_path
        )

        candidates = history_candidates.get(ref) or []
        if not candidates:
            updated_markers.append(updated)
            continue

        best_candidate, best_in_target_heading = _select_best_history_candidate(candidates, target_heading)
        current_quality = _marker_anchor_quality(updated)
        candidate_quality = _marker_anchor_quality(best_candidate)

        should_apply = False
        if best_in_target_heading and not current_in_target_heading:
            should_apply = True
        elif candidate_quality > current_quality:
            should_apply = True
        elif best_in_target_heading and candidate_quality == current_quality:
            should_apply = True

        if should_apply:
            updated["anchor_html"] = best_candidate.get("anchor_html") or updated.get("anchor_html")
            updated["left_context"] = best_candidate.get("left_context") or updated.get("left_context")
            updated["right_context"] = best_candidate.get("right_context") or updated.get("right_context")
            if best_candidate.get("heading_path"):
                updated["heading_path"] = best_candidate.get("heading_path")
            updated["history_file"] = best_candidate.get("history_file")
            enriched_count += 1

        updated_markers.append(updated)

    return updated_markers, enriched_count


def _select_best_history_candidate(
    candidates: List[Dict[str, Any]],
    target_heading: str,
) -> Tuple[Dict[str, Any], bool]:
    ranked_candidates: List[Tuple[Tuple[int, int, int, str], Dict[str, Any]]] = []
    for candidate in candidates:
        candidate_path = candidate.get("heading_path") or []
        candidate_in_target_heading = any(
            str(item.get("normalized_text") or "") == target_heading for item in candidate_path
        )
        ranked_candidates.append(
            (
                (
                    1 if candidate_in_target_heading else 0,
                    *_marker_anchor_quality(candidate),
                    str(candidate.get("history_sort_key") or ""),
                ),
                candidate,
            )
        )

    ranked_candidates.sort(key=lambda item: item[0], reverse=True)
    return ranked_candidates[0][1], bool(ranked_candidates[0][0][0])


def _supplement_markers_from_history(
    output_dir: str,
    page_id: str,
    heading_title: str,
    section_span: Tuple[int, int],
    existing_markers: List[Dict[str, Any]],
    inline_props: List[Dict[str, str]],
) -> Tuple[List[Dict[str, Any]], int]:
    target_heading = _normalize_heading_text(heading_title)
    existing_refs = {str(marker.get("ref") or "") for marker in existing_markers if marker.get("ref")}
    refs = {
        str(item.get("ref") or "")
        for item in inline_props
        if str(item.get("ref") or "") and str(item.get("ref") or "") not in existing_refs
    }
    if not refs:
        return existing_markers, 0

    history_candidates = _collect_historical_marker_candidates(output_dir, page_id, refs)
    section_start = int(section_span[0])
    supplemented = 0
    markers = list(existing_markers)

    inline_props_by_ref = {
        str(item.get("ref") or ""): item
        for item in inline_props
        if str(item.get("ref") or "")
    }

    for ref in sorted(refs):
        candidates = history_candidates.get(ref) or []
        if not candidates:
            continue

        best_candidate, best_in_target_heading = _select_best_history_candidate(candidates, target_heading)
        if not best_in_target_heading:
            continue
        inline_prop = inline_props_by_ref.get(ref) or {}
        anchor_html = str(best_candidate.get("anchor_html") or inline_prop.get("anchor_html") or "").strip()
        if not anchor_html:
            continue

        candidate_start = int(best_candidate.get("start", -1))
        absolute_start = section_start + max(0, candidate_start)
        markers.append(
            {
                "ref": ref,
                "anchor_html": anchor_html,
                "full_tag": "",
                "left_context": str(best_candidate.get("left_context") or ""),
                "right_context": str(best_candidate.get("right_context") or ""),
                "start": absolute_start,
                "end": absolute_start + len(anchor_html),
                "heading_path": best_candidate.get("heading_path") or [],
                "history_file": best_candidate.get("history_file"),
            }
        )
        supplemented += 1

    return markers, supplemented


# ---------------------------------------------------------------------------
# Inline comment anchor preservation helpers
# ---------------------------------------------------------------------------

def _fetch_page_storage_with_auth(args: argparse.Namespace, config_module: Any) -> Dict[str, Any]:
    """Fetch the current page body.storage, version and title using fallback auth."""
    last_error: Optional[Exception] = None
    for auth, headers, _ in _auth_strategies(args, config_module):
        try:
            url = f"{args.base_url.rstrip('/')}/rest/api/content/{args.page_id}"
            resp = requests.get(url, params={"expand": STORAGE_EXPAND}, auth=auth, headers=headers, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            return {
                "storage_html": ((data.get("body") or {}).get("storage") or {}).get("value") or "",
                "version": int(((data.get("version") or {}).get("number") or 0)),
                "title": str(data.get("title") or ""),
                "auth": auth,
                "headers": headers,
            }
        except Exception as exc:
            last_error = exc
    if last_error:
        raise last_error
    return {"storage_html": "", "version": 0, "title": "", "auth": None, "headers": {}}


def _parse_marker_value(marker_obj: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not marker_obj:
        return None

    value = marker_obj.get("value")
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except Exception:
            return None
        if isinstance(parsed, dict):
            return parsed
    return None


def _decompress_marker_text(value: str) -> str:
    if not isinstance(value, str) or not value.startswith("gz:"):
        return value
    try:
        raw = base64.b64decode(value[3:])
        return gzip.decompress(raw).decode("utf-8")
    except Exception:
        return value


def _fetch_publish_marker_with_auth(
    args: argparse.Namespace,
    config_module: Any,
    marker_key: str = "docAsCode.lastPublishMarker",
) -> Optional[Dict[str, Any]]:
    last_error: Optional[Exception] = None
    for auth, headers, _ in _auth_strategies(args, config_module):
        try:
            url = f"{args.base_url.rstrip('/')}/rest/api/content/{args.page_id}/property/{marker_key}"
            resp = requests.get(url, auth=auth, headers=headers, timeout=60, allow_redirects=False)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return _parse_marker_value(resp.json())
        except Exception as exc:
            last_error = exc
    if last_error:
        raise last_error
    return None


def _extract_inline_markers(storage_html: str) -> List[Dict[str, Any]]:
    """Return list of inline comment markers found in storage HTML.
    Each entry: {ref, anchor_html, full_tag}"""
    markers: List[Dict[str, Any]] = []
    if not storage_html:
        return markers

    token_re = re.compile(
        r"<ac:inline-comment-marker\b[^>]*ac:ref=([\"'])([^\"']+)\1[^>]*>|</ac:inline-comment-marker>",
        re.IGNORECASE,
    )
    stack: List[Dict[str, Any]] = []
    seen_ranges: set = set()

    for token in token_re.finditer(storage_html):
        token_text = token.group(0)
        if token_text.startswith("</"):
            if not stack:
                continue

            opened = stack.pop()
            start = int(opened["start"])
            open_end = int(opened["open_end"])
            end = token.end()
            marker_key = (start, end)
            if marker_key in seen_ranges:
                continue
            seen_ranges.add(marker_key)

            left_context = storage_html[max(0, start - _CONTEXT_WINDOW):start]
            right_context = storage_html[end:min(len(storage_html), end + _CONTEXT_WINDOW)]
            markers.append(
                {
                    "ref": str(opened["ref"]),
                    "anchor_html": storage_html[open_end:token.start()],
                    "full_tag": storage_html[start:end],
                    "left_context": left_context,
                    "right_context": right_context,
                    "start": start,
                    "end": end,
                }
            )
            continue

        stack.append(
            {
                "ref": token.group(2),
                "start": token.start(),
                "open_end": token.end(),
            }
        )

    markers.sort(key=lambda item: (int(item.get("start", -1)), -int(item.get("end", -1))))

    return markers


def _strip_inline_markers_by_ref(
    storage_html: str,
    refs_to_strip: set,
    section_span: Optional[Tuple[int, int]] = None,
) -> Tuple[str, int]:
    if not storage_html or not refs_to_strip:
        return storage_html, 0

    markers = _extract_inline_markers(storage_html)
    if section_span is not None:
        start, end = section_span
        markers = [m for m in markers if m.get("start", -1) >= start and m.get("end", -1) <= end]

    to_remove = [m for m in markers if m.get("ref") in refs_to_strip]
    if not to_remove:
        return storage_html, 0

    updated = storage_html
    for m in sorted(to_remove, key=lambda item: item.get("start", 0), reverse=True):
        start = int(m.get("start", -1))
        end = int(m.get("end", -1))
        if start < 0 or end < 0 or end < start:
            continue
        anchor_html = str(m.get("anchor_html") or "")
        updated = updated[:start] + anchor_html + updated[end:]

    return updated, len(to_remove)


def _normalize_heading_text(value: str, relax: bool = False) -> str:
    plain = _html_to_plain_text(value or "")
    plain = plain.replace("\u200b", "")
    plain = re.sub(r"\s+", " ", plain).strip().lower()
    if relax:
        # Allow loose matches when headings are numbered or prefixed with punctuation.
        plain = re.sub(r"^[\W_]*\d+(?:[\.-]\d+)*[\)\.-:]*\s*", "", plain)
        plain = re.sub(r"^[\W_]+", "", plain)
    return plain


def _find_heading_section_span(
    storage_html: str,
    heading_title: str,
    heading_level: Optional[int] = None,
) -> Optional[Tuple[int, int]]:
    """Return [start, end) span for a heading block matching heading_title."""
    if not storage_html or not heading_title:
        return None

    target = _normalize_heading_text(heading_title)
    if not target:
        return None

    heading_re = re.compile(r"<(h[1-6])\b[^>]*>(.*?)</\1>", re.IGNORECASE | re.DOTALL)
    matches = list(heading_re.finditer(storage_html))
    if not matches:
        return None

    for idx, match in enumerate(matches):
        current_level = int(match.group(1)[1:])
        if heading_level is not None and current_level != heading_level:
            continue
        heading_text = _normalize_heading_text(match.group(2))
        if heading_text != target:
            continue
        section_start = match.start()
        section_end = len(storage_html)
        for later_match in matches[idx + 1:]:
            later_level = int(later_match.group(1)[1:])
            if later_level <= current_level:
                section_end = later_match.start()
                break
        if section_end <= section_start:
            return None
        return (section_start, section_end)

    relaxed_target = _normalize_heading_text(heading_title, relax=True)
    if not relaxed_target or relaxed_target == target:
        return None

    relaxed_matches: List[Tuple[int, Any]] = []
    for idx, match in enumerate(matches):
        current_level = int(match.group(1)[1:])
        if heading_level is not None and current_level != heading_level:
            continue
        heading_text = _normalize_heading_text(match.group(2), relax=True)
        if heading_text == relaxed_target:
            relaxed_matches.append((idx, match))

    if len(relaxed_matches) != 1:
        return None

    idx, match = relaxed_matches[0]
    current_level = int(match.group(1)[1:])
    section_start = match.start()
    section_end = len(storage_html)
    for later_match in matches[idx + 1:]:
        later_level = int(later_match.group(1)[1:])
        if later_level <= current_level:
            section_end = later_match.start()
            break
    if section_end <= section_start:
        return None
    return (section_start, section_end)

    return None


def _find_surviving_section_span_from_markers(
    storage_html: str,
    markers: List[Dict[str, Any]],
) -> Optional[Tuple[int, int]]:
    if not storage_html or not markers:
        return None

    normalized_paths: List[List[str]] = []
    for marker in markers:
        path = [
            str(item.get("normalized_text") or "").strip()
            for item in (marker.get("heading_path") or [])
            if str(item.get("normalized_text") or "").strip()
        ]
        if path:
            normalized_paths.append(path)

    if not normalized_paths:
        return None

    common_path = list(normalized_paths[0])
    for path in normalized_paths[1:]:
        shared_depth = 0
        max_depth = min(len(common_path), len(path))
        while shared_depth < max_depth and common_path[shared_depth] == path[shared_depth]:
            shared_depth += 1
        common_path = common_path[:shared_depth]
        if not common_path:
            return None

    candidates = _iter_heading_candidates(storage_html)
    if not candidates:
        return None

    current_path: List[Dict[str, Any]] = []
    best_candidate: Optional[Dict[str, Any]] = None
    best_depth = 0
    best_index: Optional[int] = None

    for index, candidate in enumerate(candidates):
        while current_path and int(current_path[-1]["level"]) >= int(candidate["level"]):
            current_path.pop()
        current_path.append(candidate)

        current_normalized = [str(item.get("normalized_text") or "") for item in current_path]
        max_depth = min(len(current_normalized), len(common_path))
        matched_depth = 0
        for depth in range(1, max_depth + 1):
            if current_normalized[:depth] == common_path[:depth]:
                matched_depth = depth
            else:
                break

        if matched_depth > best_depth:
            best_depth = matched_depth
            best_candidate = current_path[matched_depth - 1]
            best_index = index

    if best_candidate is None or best_index is None:
        return None

    section_start = int(best_candidate["start"])
    section_level = int(best_candidate["level"])
    section_end = len(storage_html)
    for later_candidate in candidates[best_index + 1:]:
        if int(later_candidate["level"]) <= section_level:
            section_end = int(later_candidate["start"])
            break

    if section_end <= section_start:
        return None
    return (section_start, section_end)


def _parse_markdown_sections(md_path: str, split_level: int = 1) -> List[Dict[str, str]]:
    if split_level < 1 or split_level > 6:
        raise ValueError("split_level must be between 1 and 6")

    with open(md_path, "r", encoding="utf-8") as handle:
        lines = handle.read().splitlines()

    sections: List[Dict[str, str]] = []
    current_title: Optional[str] = None
    current_lines: List[str] = []
    preface: List[str] = []
    in_fenced_code = False
    heading_pattern = re.compile(r"^(#{1,6})\s+(.+?)\s*$")

    for line in lines:
        if re.match(r"^\s*(```|~~~)", line):
            in_fenced_code = not in_fenced_code
            if current_title is not None:
                current_lines.append(line)
            else:
                preface.append(line)
            continue

        if not in_fenced_code:
            heading_match = heading_pattern.match(line)
            if heading_match:
                heading_depth = len(heading_match.group(1))
                if heading_depth != split_level:
                    if current_title is not None:
                        current_lines.append(line)
                    else:
                        preface.append(line)
                    continue

                if current_title is not None:
                    sections.append({"title": current_title, "markdown": "\n".join(current_lines).strip()})

                current_title = heading_match.group(2).strip() or f"Section {len(sections) + 1}"
                current_lines = []
                continue

        if current_title is not None:
            current_lines.append(line)
        else:
            preface.append(line)

    if current_title is not None:
        sections.append({"title": current_title, "markdown": "\n".join(current_lines).strip()})

    if preface and sections:
        sections[0]["markdown"] = ("\n".join(preface).strip() + "\n\n" + sections[0]["markdown"]).strip()

    if not sections:
        sections.append(
            {"title": os.path.splitext(os.path.basename(md_path))[0] or "Document", "markdown": "\n".join(preface).strip()}
        )

    return sections


def _markdown_to_plain_text(value: str) -> str:
    text = (value or "").replace("\r\n", "\n")
    text = re.sub(r"!\[([^\]]*)\]\([^\)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s{0,3}>\s?", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s{0,3}(?:[-+*]|\d+\.)\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-:| ]+\s*$", "", text, flags=re.MULTILINE)
    text = text.replace("|", " ")
    text = re.sub(r"[`*_~]", "", text)
    return _html_to_plain_text(text)


def _normalize_section_body_for_autodetect(value: str, *, is_html: bool) -> str:
    text = value or ""
    if is_html:
        text = re.sub(r"^\s*<h[1-6]\b[^>]*>.*?</h[1-6]>\s*", "", text, count=1, flags=re.IGNORECASE | re.DOTALL)
        plain = _html_to_plain_text(text)
    else:
        plain = _markdown_to_plain_text(text)
    plain = plain.replace("\u200b", "")
    return re.sub(r"\s+", " ", plain).strip().lower()


def _resolve_changed_heading_titles_against_markdown(
    md_path: str,
    baseline_markdown: str,
    split_level: int,
) -> List[str]:
    sections = _parse_markdown_sections(md_path, split_level=split_level)
    baseline_sections = _parse_markdown_sections_from_text(baseline_markdown, split_level=split_level)
    baseline_by_title = {
        str(section.get("title") or "").strip(): section
        for section in baseline_sections
        if str(section.get("title") or "").strip()
    }
    changed_titles: List[str] = []
    local_titles = {
        str(section.get("title") or "").strip()
        for section in sections
        if str(section.get("title") or "").strip()
    }

    for section in sections:
        title = str(section.get("title") or "").strip()
        if not title:
            continue
        baseline_section = baseline_by_title.get(title)
        if baseline_section is None:
            changed_titles.append(title)
            continue

        baseline_normalized = _normalize_section_body_for_autodetect(
            str(baseline_section.get("markdown") or ""),
            is_html=False,
        )
        local_normalized = _normalize_section_body_for_autodetect(str(section.get("markdown") or ""), is_html=False)
        if baseline_normalized != local_normalized:
            changed_titles.append(title)

    for baseline_section in baseline_sections:
        title = str(baseline_section.get("title") or "").strip()
        if title and title not in local_titles:
            changed_titles.append(title)

    return changed_titles


def _resolve_changed_heading_titles_against_section_map(
    md_path: str,
    baseline_sections_by_title: Dict[str, str],
    split_level: int,
) -> List[str]:
    sections = _parse_markdown_sections(md_path, split_level=split_level)
    changed_titles: List[str] = []
    local_titles = {
        str(section.get("title") or "").strip()
        for section in sections
        if str(section.get("title") or "").strip()
    }

    for section in sections:
        title = str(section.get("title") or "").strip()
        if not title:
            continue
        baseline_markdown = baseline_sections_by_title.get(title)
        if baseline_markdown is None:
            changed_titles.append(title)
            continue

        baseline_normalized = _normalize_section_body_for_autodetect(str(baseline_markdown), is_html=False)
        local_normalized = _normalize_section_body_for_autodetect(str(section.get("markdown") or ""), is_html=False)
        if baseline_normalized != local_normalized:
            changed_titles.append(title)

    for title in baseline_sections_by_title.keys():
        normalized_title = str(title or "").strip()
        if normalized_title and normalized_title not in local_titles:
            changed_titles.append(normalized_title)

    return changed_titles


def _extract_storage_heading_titles(storage_html: str, split_level: int) -> List[str]:
    if not storage_html:
        return []

    target_tag = f"h{int(split_level)}"
    heading_re = re.compile(r"<(h[1-6])\b[^>]*>(.*?)</\1>", re.IGNORECASE | re.DOTALL)
    titles: List[str] = []
    for match in heading_re.finditer(storage_html):
        if str(match.group(1) or "").lower() != target_tag:
            continue
        title = _html_to_plain_text(match.group(2)).strip()
        if title:
            titles.append(title)
    return titles


def _parse_markdown_sections_from_text(markdown_text: str, split_level: int = 1) -> List[Dict[str, str]]:
    heading_pattern = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
    sections: List[Dict[str, str]] = []
    preface: List[str] = []
    current_title: Optional[str] = None
    current_lines: List[str] = []
    in_fenced_code = False

    for raw_line in (markdown_text or "").replace("\r\n", "\n").split("\n"):
        line = raw_line.rstrip("\r")

        if re.match(r"^\s*```", line):
            in_fenced_code = not in_fenced_code
            if current_title is not None:
                current_lines.append(line)
            else:
                preface.append(line)
            continue

        if not in_fenced_code:
            heading_match = heading_pattern.match(line)
            if heading_match:
                heading_depth = len(heading_match.group(1))
                if heading_depth != split_level:
                    if current_title is not None:
                        current_lines.append(line)
                    else:
                        preface.append(line)
                    continue

                if current_title is not None:
                    sections.append({"title": current_title, "markdown": "\n".join(current_lines).strip()})

                current_title = heading_match.group(2).strip() or f"Section {len(sections) + 1}"
                current_lines = []
                continue

        if current_title is not None:
            current_lines.append(line)
        else:
            preface.append(line)

    if current_title is not None:
        sections.append({"title": current_title, "markdown": "\n".join(current_lines).strip()})

    if preface and sections:
        sections[0]["markdown"] = ("\n".join(preface).strip() + "\n\n" + sections[0]["markdown"]).strip()

    if not sections:
        sections.append({"title": "Document", "markdown": "\n".join(preface).strip()})

    return sections


def _auto_heading_baseline_path(output_dir: str, page_id: str) -> str:
    return os.path.join(output_dir, f"{page_id}_auto_heading_baseline.json")


def _comment_ref_heading_baseline_path(output_dir: str, page_id: str) -> str:
    return os.path.join(output_dir, f"{page_id}_comment_ref_heading_baseline.json")


def _load_comment_ref_heading_baseline(output_dir: str, page_id: str) -> Dict[str, Any]:
    baseline_path = _comment_ref_heading_baseline_path(output_dir, page_id)
    if not os.path.exists(baseline_path):
        return {"refs": {}}
    try:
        payload = _load_json(baseline_path)
    except Exception:
        return {"refs": {}}
    if str(payload.get("page_id") or "") != str(page_id):
        return {"refs": {}}
    refs = payload.get("refs") or {}
    if not isinstance(refs, dict):
        refs = {}
    payload["refs"] = refs
    return payload


def _save_comment_ref_heading_baseline(output_dir: str, page_id: str, payload: Dict[str, Any]) -> None:
    baseline_path = _comment_ref_heading_baseline_path(output_dir, page_id)
    payload = dict(payload)
    payload["schemaVersion"] = "1.0"
    payload["updatedAt"] = dt.datetime.now(dt.UTC).isoformat()
    payload["page_id"] = str(page_id)
    refs = payload.get("refs") or {}
    payload["refs"] = refs if isinstance(refs, dict) else {}
    _save_json(baseline_path, payload)


def _record_comment_ref_heading_ownership(
    output_dir: str,
    page_id: str,
    heading_title: str,
    markers: List[Dict[str, Any]],
) -> None:
    refs_to_record = [str(marker.get("ref") or "") for marker in markers if str(marker.get("ref") or "")]
    if not refs_to_record:
        return

    normalized_heading = _normalize_heading_text(heading_title)
    payload = _load_comment_ref_heading_baseline(output_dir, page_id)
    refs = dict(payload.get("refs") or {})

    for marker in markers:
        ref = str(marker.get("ref") or "")
        if not ref:
            continue
        heading_path = [
            str(item.get("normalized_text") or "").strip()
            for item in (marker.get("heading_path") or [])
            if str(item.get("normalized_text") or "").strip()
        ]
        refs[ref] = {
            "heading_title": str(heading_title),
            "normalized_heading_title": normalized_heading,
            "heading_path": heading_path,
            "updatedAt": dt.datetime.now(dt.UTC).isoformat(),
        }

    payload["refs"] = refs
    _save_comment_ref_heading_baseline(output_dir, page_id, payload)


def _resolve_owned_comment_refs_for_heading(output_dir: str, page_id: str, heading_title: str) -> set:
    payload = _load_comment_ref_heading_baseline(output_dir, page_id)
    refs = payload.get("refs") or {}
    target_heading = _normalize_heading_text(heading_title)
    owned_refs = set()

    for ref, entry in refs.items():
        if not isinstance(entry, dict):
            continue
        normalized_heading = str(entry.get("normalized_heading_title") or "").strip()
        heading_path = [str(item or "").strip() for item in (entry.get("heading_path") or []) if str(item or "").strip()]
        if normalized_heading == target_heading or target_heading in heading_path:
            owned_refs.add(str(ref))

    return owned_refs


def _load_auto_heading_baseline(
    output_dir: str,
    page_id: str,
    md_path: str,
    split_level: int,
) -> Optional[Dict[str, Any]]:
    baseline_path = _auto_heading_baseline_path(output_dir, page_id)
    if not os.path.exists(baseline_path):
        return None
    try:
        payload = _load_json(baseline_path)
    except Exception:
        return None
    if str(payload.get("page_id") or "") != str(page_id):
        return None
    if int(payload.get("split_level") or 0) != int(split_level):
        return None

    saved_md_path = os.path.abspath(str(payload.get("md_path") or ""))
    requested_md_path = os.path.abspath(md_path)
    if saved_md_path != requested_md_path:
        try:
            requested_titles = [
                str(section.get("title") or "").strip()
                for section in _parse_markdown_sections(md_path, split_level=split_level)
                if str(section.get("title") or "").strip()
            ]
        except Exception:
            return None

        saved_headings = payload.get("headings") or {}
        if not isinstance(saved_headings, dict):
            return None
        saved_titles = [str(title or "").strip() for title in saved_headings.keys() if str(title or "").strip()]
        if requested_titles != saved_titles:
            return None

    return payload


def _save_auto_heading_baseline(
    output_dir: str,
    page_id: str,
    md_path: str,
    split_level: int,
    headings: Dict[str, str],
) -> None:
    baseline_path = _auto_heading_baseline_path(output_dir, page_id)
    payload = {
        "schemaVersion": "1.0",
        "savedAt": dt.datetime.now(dt.UTC).isoformat(),
        "page_id": str(page_id),
        "md_path": os.path.abspath(md_path),
        "split_level": int(split_level),
        "headings": headings,
    }
    _save_json(baseline_path, payload)


def _build_markdown_section_map(md_path: str, split_level: int) -> Dict[str, str]:
    section_map: Dict[str, str] = {}
    for section in _parse_markdown_sections(md_path, split_level=split_level):
        title = str(section.get("title") or "").strip()
        if not title:
            continue
        section_map[title] = str(section.get("markdown") or "")
    return section_map


def _resolve_changed_heading_titles(
    md_path: str,
    storage_html: str,
    split_level: int,
    baseline_markdown: Optional[str] = None,
    baseline_sections_by_title: Optional[Dict[str, str]] = None,
) -> List[str]:
    if baseline_sections_by_title:
        return _resolve_changed_heading_titles_against_section_map(md_path, baseline_sections_by_title, split_level)
    if baseline_markdown and baseline_markdown.strip():
        return _resolve_changed_heading_titles_against_markdown(md_path, baseline_markdown, split_level)

    sections = _parse_markdown_sections(md_path, split_level=split_level)
    changed_titles: List[str] = []
    local_titles = {
        str(section.get("title") or "").strip()
        for section in sections
        if str(section.get("title") or "").strip()
    }

    for section in sections:
        title = str(section.get("title") or "").strip()
        if not title:
            continue
        live_span = _find_heading_section_span(storage_html, title, heading_level=split_level)
        if live_span is None:
            changed_titles.append(title)
            continue

        live_section_html = storage_html[live_span[0]:live_span[1]]
        live_normalized = _normalize_section_body_for_autodetect(live_section_html, is_html=True)
        local_normalized = _normalize_section_body_for_autodetect(str(section.get("markdown") or ""), is_html=False)
        if live_normalized != local_normalized:
            changed_titles.append(title)

    for title in _extract_storage_heading_titles(storage_html, split_level):
        normalized_title = str(title or "").strip()
        if normalized_title and normalized_title not in local_titles:
            changed_titles.append(normalized_title)

    return changed_titles


def _resolve_auto_heading_title(md_path: str, storage_html: str, split_level: int) -> str:
    changed_titles = _resolve_changed_heading_titles(md_path, storage_html, split_level)

    if len(changed_titles) == 1:
        return changed_titles[0]

    if not changed_titles:
        raise SystemExit(
            "Unable to auto-resolve a changed heading because no split-level section differs from the current page. "
            "Pass --heading-title explicitly."
        )

    raise SystemExit(
        "Unable to auto-resolve a changed heading because multiple split-level sections differ from the current page: "
        f"{changed_titles}. Pass --heading-title explicitly."
    )


def _build_self_command_for_heading(args: argparse.Namespace, heading_title: str) -> List[str]:
    command = [
        args.python_executable,
        os.path.abspath(__file__),
        "--project-root",
        args.project_root,
        "--base-url",
        args.base_url,
        "--page-id",
        args.page_id,
        "--md-path",
        args.md_path,
        "--heading-title",
        heading_title,
        "--compare-mode",
        args.compare_mode,
        "--split-level",
        str(args.split_level),
        "--reflect-mode",
        args.reflect_mode,
        "--reflect-auto-clear-seconds",
        str(args.reflect_auto_clear_seconds),
        "--guard-script",
        args.guard_script,
        "--python-executable",
        args.python_executable,
        "--output-dir",
        args.output_dir,
    ]

    optional_pairs = [
        ("--username", args.username),
        ("--token", args.token),
        ("--access-token", args.access_token),
        ("--session-cookie", args.session_cookie),
    ]
    for flag, value in optional_pairs:
        if value:
            command.extend([flag, value])

    boolean_flags = [
        ("--apply", args.apply),
        ("--yes", args.yes),
        ("--force-scdp-override", args.force_scdp_override),
        ("--yes-override", args.yes_override),
        ("--no-prompt-override", args.no_prompt_override),
        ("--no-prompt-missing-heading", args.no_prompt_missing_heading),
        ("--require-visible-inline-markers", args.require_visible_inline_markers),
        ("--reflect-on-page", args.reflect_on_page),
        ("--reflect-keep-after-refresh", args.reflect_keep_after_refresh),
        ("--reflect-persist-manual", args.reflect_persist_manual),
        ("--reflect-compare-latest-previous", args.reflect_compare_latest_previous),
    ]
    for flag, enabled in boolean_flags:
        if enabled:
            command.append(flag)

    return command


def _run_multi_heading_publish(args: argparse.Namespace, changed_titles: List[str]) -> int:
    print("[source] Requested heading title: auto")
    print(f"[source] Auto-resolved changed headings: {changed_titles}")

    for index, heading_title in enumerate(changed_titles, start=1):
        print(f"\n=== AUTO MULTI-SECTION RUN {index}/{len(changed_titles)}: {heading_title} ===")
        command = _build_self_command_for_heading(args, heading_title)
        process = subprocess.run(command, text=True, capture_output=True, encoding="utf-8", errors="replace")

        if process.stdout:
            _write_text_safe(sys.stdout, process.stdout.rstrip())
        if process.stderr:
            _write_text_safe(sys.stderr, process.stderr.rstrip())

        if process.returncode != 0:
            raise SystemExit(
                f"Auto multi-section publish stopped on heading '{heading_title}' with exit code {process.returncode}."
            )

    print(f"\n[source] Auto multi-section publish completed for {len(changed_titles)} headings.")
    return 0


def _iter_heading_candidates(text: str) -> List[Dict[str, Any]]:
    heading_re = re.compile(r"<(h[1-6])\b[^>]*>(.*?)</\1>", re.IGNORECASE | re.DOTALL)
    candidates: List[Dict[str, Any]] = []
    for match in heading_re.finditer(text):
        normalized_text = _normalize_heading_text(match.group(2))
        if not normalized_text:
            continue
        candidates.append(
            {
                "level": int(match.group(1)[1:]),
                "start": match.start(),
                "end": match.end(),
                "content_start": match.start(2),
                "content_end": match.end(2),
                "text": _html_to_plain_text(match.group(2)).strip(),
                "normalized_text": normalized_text,
            }
        )
    return candidates


def _heading_path_at_index(text: str, index: int) -> List[Dict[str, Any]]:
    path: List[Dict[str, Any]] = []
    for candidate in _iter_heading_candidates(text):
        if int(candidate["start"]) > index:
            break
        while path and int(path[-1]["level"]) >= int(candidate["level"]):
            path.pop()
        path.append(
            {
                "level": int(candidate["level"]),
                "text": str(candidate["text"]),
                "normalized_text": str(candidate["normalized_text"]),
            }
        )
    return path


def _annotate_markers_with_heading_path(
    section_html: str,
    section_start: int,
    markers: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    annotated: List[Dict[str, Any]] = []
    for marker in markers:
        updated = dict(marker)
        start = int(updated.get("start", -1))
        if start >= section_start:
            updated["heading_path"] = _heading_path_at_index(section_html, start - section_start)
        annotated.append(updated)
    return annotated


def _pick_heading_anchor_candidate(
    text: str,
    preferred_index: Optional[int] = None,
) -> Optional[Tuple[int, int, int, int]]:
    if not text:
        return None
    heading_re = re.compile(r"<(h[1-6])\b[^>]*>(.*?)</\1>", re.IGNORECASE | re.DOTALL)
    strong_re = re.compile(r"<p\b[^>]*>\s*(?:<strong>|<b>)(.*?)</(?:strong|b)>\s*</p>", re.IGNORECASE | re.DOTALL)
    strong_para_re = re.compile(
        r"<p\b[^>]*>\s*(?:<span\b[^>]*>\s*)*(?:<strong>|<b>)\s*(.*?)\s*</(?:strong|b)>\s*(?:</span>\s*)*</p>",
        re.IGNORECASE | re.DOTALL,
    )
    macro_title_re = re.compile(
        r"<ac:parameter\b[^>]*ac:name=\"(?:title|atlassian-macro-title)\"[^>]*>(.*?)</ac:parameter>",
        re.IGNORECASE | re.DOTALL,
    )
    strong_para_re = re.compile(
        r"<p\b[^>]*>\s*(?:<span\b[^>]*>\s*)*(?:<strong>|<b>)\s*(.*?)\s*</(?:strong|b)>\s*(?:</span>\s*)*</p>",
        re.IGNORECASE | re.DOTALL,
    )
    macro_title_re = re.compile(
        r"<ac:parameter\b[^>]*ac:name=\"(?:title|atlassian-macro-title)\"[^>]*>(.*?)</ac:parameter>",
        re.IGNORECASE | re.DOTALL,
    )

    candidates: List[Tuple[int, int, int, int]] = []
    for m in heading_re.finditer(text):
        candidates.append((m.start(), m.end(), m.start(2), m.end(2)))
    for m in strong_re.finditer(text):
        candidates.append((m.start(), m.end(), m.start(1), m.end(1)))
    for m in strong_para_re.finditer(text):
        candidates.append((m.start(), m.end(), m.start(1), m.end(1)))
    for m in macro_title_re.finditer(text):
        candidates.append((m.start(), m.end(), m.start(1), m.end(1)))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0])
    chosen = candidates[0]
    if preferred_index is not None:
        prior = [c for c in candidates if c[0] <= preferred_index]
        if prior:
            chosen = prior[-1]

    return chosen


def _pick_heading_anchor_span(text: str, preferred_index: Optional[int] = None) -> Optional[Tuple[int, int]]:
    chosen = _pick_heading_anchor_candidate(text, preferred_index)
    if chosen is None:
        return None
    span = _normalize_fallback_span(text, (chosen[2], chosen[3]))
    if span[1] <= span[0]:
        return None
    return span


def _pick_heading_insertion_point(text: str, preferred_index: Optional[int] = None) -> Optional[int]:
    chosen = _pick_heading_anchor_candidate(text, preferred_index)
    if chosen is None:
        return None
    return chosen[1]


def _filter_markers_by_span(markers: List[Dict[str, Any]], span: Tuple[int, int]) -> List[Dict[str, Any]]:
    start, end = span
    filtered: List[Dict[str, Any]] = []
    for marker in markers:
        marker_start = int(marker.get("start", -1))
        marker_end = int(marker.get("end", -1))
        if marker_start < 0 or marker_end < 0:
            continue
        if marker_start >= start and marker_end <= end:
            filtered.append(marker)
    return filtered


def _find_all_occurrences(text: str, needle: str) -> List[int]:
    if not needle:
        return []
    positions: List[int] = []
    cursor = text.find(needle)
    while cursor != -1:
        positions.append(cursor)
        cursor = text.find(needle, cursor + 1)
    return positions


def _common_suffix_len(left: str, right: str) -> int:
    max_len = min(len(left), len(right))
    matched = 0
    for i in range(1, max_len + 1):
        if left[-i] != right[-i]:
            break
        matched += 1
    return matched


def _common_prefix_len(left: str, right: str) -> int:
    max_len = min(len(left), len(right))
    matched = 0
    for i in range(max_len):
        if left[i] != right[i]:
            break
        matched += 1
    return matched


def _pick_best_occurrence_by_context(
    text: str,
    anchor: str,
    occurrences: List[int],
    left_context: str,
    right_context: str,
    preferred_index: Optional[int] = None,
) -> Optional[int]:
    if not occurrences:
        return None

    scored: List[Tuple[int, int, int]] = []
    for index in occurrences:
        before = text[:index]
        after = text[index + len(anchor):]
        score = _common_suffix_len(left_context, before) + _common_prefix_len(right_context, after)
        distance = abs(index - preferred_index) if preferred_index is not None else 0
        scored.append((score, -distance, index))

    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    best_score, _best_distance_score, best_index = scored[0]
    if len(occurrences) == 1:
        # A unique surviving occurrence is not always the original anchor.
        # When the original text was deleted and the same text still exists
        # elsewhere, weak-context auto-selection makes the comment drift.
        if preferred_index is None:
            return best_index
        max_dist = max(len(anchor) * 3, 120)
        if best_score >= _MIN_CONTEXT_SCORE or abs(best_index - preferred_index) <= max_dist:
            return best_index
        return None

        return best_index

    if best_score < _MIN_CONTEXT_SCORE:
        if preferred_index is not None:
            nearest = min(occurrences, key=lambda idx: abs(idx - preferred_index))
            max_dist = max(len(anchor) * 3, 120)
            if abs(nearest - preferred_index) <= max_dist:
                return nearest
        return None
    if len(scored) > 1 and scored[1][0] == best_score:
        if preferred_index is not None:
            candidates = [idx for score, _dist, idx in scored if score == best_score]
            distances = sorted((abs(idx - preferred_index), idx) for idx in candidates)
            if len(distances) > 1 and distances[0][0] == distances[1][0]:
                return None
            max_dist = max(len(anchor) * 3, 120)
            if distances[0][0] <= max_dist:
                return distances[0][1]
        return None
    return best_index


def _score_occurrence_context(
    text: str,
    anchor: str,
    occurrence_index: int,
    left_context: str,
    right_context: str,
) -> int:
    before = text[:occurrence_index]
    after = text[occurrence_index + len(anchor):]
    return _common_suffix_len(left_context, before) + _common_prefix_len(right_context, after)


def _find_best_context_fragment(text: str, context: str, from_left: bool, start_at: int = 0) -> Tuple[Optional[int], int]:
    if not context:
        return None, 0

    max_len = min(len(context), _CONTEXT_WINDOW)
    min_len = max(1, min(_MIN_CONTEXT_FRAGMENT, max_len))
    for length in range(max_len, min_len - 1, -1):
        snippet = context[-length:] if from_left else context[:length]
        pos = text.find(snippet, start_at)
        if pos != -1:
            return pos, length
    return None, 0


def _find_best_context_fragment_near_preferred(
    text: str,
    context: str,
    from_left: bool,
    preferred_index: Optional[int],
    start_at: int = 0,
) -> Tuple[Optional[int], int]:
    if preferred_index is None:
        return _find_best_context_fragment(text, context, from_left=from_left, start_at=start_at)
    if not context:
        return None, 0

    max_len = min(len(context), _CONTEXT_WINDOW)
    min_len = max(1, min(_MIN_CONTEXT_FRAGMENT, max_len))
    for length in range(max_len, min_len - 1, -1):
        snippet = context[-length:] if from_left else context[:length]
        positions = _find_all_occurrences(text[start_at:], snippet)
        if not positions:
            continue

        actual_positions = [start_at + pos for pos in positions]

        def _distance(pos: int) -> Tuple[int, int, int]:
            anchor_edge = pos + length if from_left else pos
            right_bias = 0 if anchor_edge >= preferred_index else 1
            return (abs(anchor_edge - preferred_index), right_bias, pos)

        return min(actual_positions, key=_distance), length
    return None, 0


def _find_contextual_span(text: str, left_context: str, right_context: str) -> Tuple[Optional[int], Optional[int], int]:
    left_pos, left_len = _find_best_context_fragment(text, left_context, from_left=True)
    search_start = (left_pos + left_len) if left_pos is not None else 0
    right_pos, right_len = _find_best_context_fragment(text, right_context, from_left=False, start_at=search_start)

    start = left_pos + left_len if left_pos is not None else right_pos
    end = right_pos if right_pos is not None else start
    score = left_len + right_len

    if start is None:
        return None, None, 0
    if end is not None and end < start:
        end = start
    return start, end, score


def _pick_edited_context_span(
    text: str,
    left_context: str,
    right_context: str,
    preferred_index: Optional[int] = None,
) -> Optional[Tuple[int, int]]:
    """Pick a safe anchor span using surrounding context when anchor text changed."""
    left_pos, left_len = _find_best_context_fragment_near_preferred(
        text,
        left_context,
        from_left=True,
        preferred_index=preferred_index,
    )
    search_start = (left_pos + left_len) if left_pos is not None else 0
    right_pos, right_len = _find_best_context_fragment_near_preferred(
        text,
        right_context,
        from_left=False,
        preferred_index=preferred_index,
        start_at=search_start,
    )
    score = left_len + right_len

    if max(left_len, right_len) < _MIN_CONTEXT_FRAGMENT:
        return None

    start = left_pos + left_len if left_pos is not None else right_pos
    if start is None:
        return None
    end = right_pos if right_pos is not None else start
    if end < start:
        end = start

    if end <= start:
        token_span = _pick_nearest_text_token_span(text, start)
        return token_span

    normalized = _normalize_fallback_span(text, (start, end))
    if normalized[1] <= normalized[0]:
        return None
    return normalized


def _is_safe_anchor_text(candidate: str) -> bool:
    """Allow only compact plain-text anchors for fallback insertion."""
    if not candidate or not candidate.strip():
        return False
    if len(candidate) > _MAX_FALLBACK_ANCHOR_CHARS:
        return False
    if candidate.count("\n") > _MAX_FALLBACK_ANCHOR_NEWLINES:
        return False
    if "<" in candidate or ">" in candidate:
        return False
    return True


def _normalize_fallback_span(text: str, span: Tuple[int, int]) -> Tuple[int, int]:
    """Shrink broad spans to a safe text token; otherwise fall back to point insertion."""
    start, end = span
    if end <= start:
        return (start, start)

    candidate = text[start:end]
    if _is_safe_anchor_text(candidate):
        return (start, end)

    # Try narrower plain-text tokens inside a broader candidate block.
    for token_start, token_end in _collect_text_spans(text, start, end):
        token = text[token_start:token_end]
        if _is_safe_anchor_text(token):
            return (token_start, token_end)

    return (start, start)


def _collect_text_spans(text: str, start: int, end: int) -> List[Tuple[int, int]]:
    spans: List[Tuple[int, int]] = []
    in_tag = False
    token_start: Optional[int] = None

    for index in range(start, end):
        ch = text[index]
        if in_tag:
            if ch == ">":
                in_tag = False
            continue
        if ch == "<":
            if token_start is not None:
                spans.append((token_start, index))
                token_start = None
            in_tag = True
            continue
        if ch.isspace():
            if token_start is not None:
                spans.append((token_start, index))
                token_start = None
            continue
        if token_start is None:
            token_start = index

    if token_start is not None:
        spans.append((token_start, end))
    return spans


def _pick_nearest_text_token_span(text: str, index: int, window: int = _FALLBACK_SEARCH_WINDOW) -> Optional[Tuple[int, int]]:
    """Return the nearest visible token around an insertion point.

    This avoids preserving comments on an empty/deleted location by anchoring
    them to nearby surviving text when exact anchor text no longer exists.
    """
    if not text:
        return None

    search_start = max(0, index - max(1, window))
    search_end = min(len(text), index + max(1, window))
    spans = _collect_text_spans(text, search_start, search_end)
    if not spans:
        return None

    def _distance(span: Tuple[int, int]) -> Tuple[int, int]:
        s, e = span
        mid = (s + e) // 2
        # Tie-break toward right-side text so comments move forward with edits.
        right_bias = 0 if mid >= index else 1
        return (abs(mid - index), right_bias)

    best = min(spans, key=_distance)
    token = text[best[0]:best[1]]
    if not _is_safe_anchor_text(token):
        return None
    return best


def _normalize_insertion_point_outside_tag(text: str, index: int) -> int:
    """Move insertion point outside HTML tags to avoid malformed storage markup."""
    pos = max(0, min(index, len(text)))
    if not text:
        return 0

    left_lt = text.rfind("<", 0, pos)
    left_gt = text.rfind(">", 0, pos)
    if left_lt != -1 and left_lt > left_gt:
        right_gt = text.find(">", pos)
        if right_gt != -1:
            return min(len(text), right_gt + 1)
    return pos


def _is_index_inside_tag(text: str, index: int) -> bool:
    if not text:
        return False
    pos = max(0, min(index, len(text)))
    in_tag = False
    for current in text[:pos]:
        if current == "<":
            in_tag = True
        elif current == ">":
            in_tag = False
    return in_tag


def _is_safe_wrap_span(text: str, start: int, end: int) -> bool:
    if end <= start:
        return False
    if _is_index_inside_tag(text, start) or _is_index_inside_tag(text, max(start, end - 1)):
        return False
    candidate = text[start:end]
    if not _is_safe_anchor_text(candidate):
        return False
    return True


def _find_deleted_icon_insertion_point(
    text: str,
    preferred_index: int,
    left_context: str,
    right_context: str,
) -> int:
    """Find the best insertion point for a deleted-content icon.

    Strategy:
    1. Use left_context to locate the preceding block and insert AFTER its
       last text token — so the icon appears at the end of the surviving
       paragraph before the deleted line, never inside a heading.
    2. Fall back to preferred_index but skip forward past any heading element.
    3. Final fallback: raw preferred_index moved outside a tag.
    """
    # --- Strategy 1: insert after last token of the preceding block ----------
    left_pos, left_len = _find_best_context_fragment(text, left_context, from_left=True)
    if left_pos is not None:
        context_end = left_pos + left_len
        block = _find_enclosing_block_span(text, context_end)
        if block is not None:
            spans = _collect_text_spans(text, block[0], block[1])
            if spans:
                return spans[-1][1]  # right after last text token in the block

    # --- Strategy 2: preferred_index, skip over any heading element ----------
    pos = _normalize_insertion_point_outside_tag(text, preferred_index)
    # Check if we landed inside heading content by looking back for an unclosed
    # heading open-tag.  If found, jump to after the heading close-tag.
    look_back = text[max(0, pos - 300):pos]
    heading_back = re.search(r'<(h[1-6])\b[^>]*>[^<]*$', look_back, re.IGNORECASE)
    if heading_back:
        level = heading_back.group(1)
        close_m = re.search(rf'</{level}>', text[pos:], re.IGNORECASE)
        if close_m:
            pos = pos + close_m.end()
    return pos


def _find_enclosing_block_span(text: str, index: int) -> Optional[Tuple[int, int]]:
    # Exclude headings from fallback spans to avoid injecting hidden markers into titles.
    block_open_re = re.compile(r'<(p|li|td|th|div|blockquote)[^>]*>', re.IGNORECASE)
    block_close_re = re.compile(r'</(p|li|td|th|div|blockquote)[^>]*>', re.IGNORECASE)

    search_back_start = max(0, index - (3 * _FALLBACK_SEARCH_WINDOW))
    opens = list(block_open_re.finditer(text, search_back_start, index + 1))
    if not opens:
        return None

    content_start = opens[-1].end()
    close_m = block_close_re.search(text, index)
    if not close_m:
        return None

    content_end = close_m.start()
    if content_end <= content_start:
        return None

    candidate = text[content_start:content_end]
    if not candidate.strip():
        return None

    if re.search(r'<(p|li|td|th|div|blockquote)\b', candidate, re.IGNORECASE):
        return None

    return (content_start, content_end)


def _find_nearest_table_cell_span(text: str, index: int) -> Optional[Tuple[int, int]]:
    cell_open_re = re.compile(r'<(td|th)[^>]*>', re.IGNORECASE)
    cell_close_re = re.compile(r'</(td|th)[^>]*>', re.IGNORECASE)

    nearest: Optional[Tuple[int, int, int]] = None
    search_start = max(0, index - (3 * _FALLBACK_SEARCH_WINDOW))
    search_end = min(len(text), index + (3 * _FALLBACK_SEARCH_WINDOW))

    for open_m in cell_open_re.finditer(text, search_start, search_end):
        content_start = open_m.end()
        close_m = cell_close_re.search(text, content_start)
        if not close_m:
            continue
        content_end = close_m.start()
        if content_end <= content_start:
            continue
        candidate = text[content_start:content_end]
        if not candidate.strip() or "<" in candidate:
            continue
        distance = min(abs(index - content_start), abs(index - content_end))
        if nearest is None or distance < nearest[0]:
            nearest = (distance, content_start, content_end)

    if nearest is None:
        return None
    return (nearest[1], nearest[2])


def _find_enclosing_table_row_span(text: str, index: int) -> Optional[Tuple[int, int]]:
    row_open_re = re.compile(r'<tr\b[^>]*>', re.IGNORECASE)
    row_close_re = re.compile(r'</tr\s*>', re.IGNORECASE)

    search_back_start = max(0, index - (4 * _FALLBACK_SEARCH_WINDOW))
    open_matches = list(row_open_re.finditer(text, search_back_start, index + 1))
    if not open_matches:
        return None

    row_start = open_matches[-1].start()
    row_open_end = open_matches[-1].end()
    close_match = row_close_re.search(text, row_open_end)
    if close_match is None or close_match.start() < index:
        return None
    return (row_start, close_match.end())


def _table_row_context_matches(
    text: str,
    occurrence_index: int,
    left_context: str,
    right_context: str,
) -> bool:
    row_span = _find_enclosing_table_row_span(text, occurrence_index)
    if row_span is None:
        return True

    row_text = _html_to_plain_text(text[row_span[0]:row_span[1]])
    left_plain = _html_to_plain_text(left_context)
    right_plain = _html_to_plain_text(right_context)

    left_pos, left_len = _find_best_context_fragment(row_text, left_plain, from_left=True)
    right_search_start = (left_pos + left_len) if left_pos is not None else 0
    _right_pos, right_len = _find_best_context_fragment(
        row_text,
        right_plain,
        from_left=False,
        start_at=right_search_start,
    )

    min_row_context = 4
    if any(ch.isalnum() for ch in left_plain):
        return left_len >= min_row_context
    return max(left_len, right_len) >= min_row_context


def _pick_fallback_anchor_span(text: str, left_context: str, right_context: str) -> Optional[Tuple[int, int]]:
    start, end, score = _find_contextual_span(text, left_context, right_context)
    if start is None or score < _MIN_CONTEXT_FRAGMENT:
        right_pos, _ = _find_best_context_fragment(text, right_context, from_left=False)
        if right_pos is not None:
            return (right_pos, right_pos)

        left_pos, left_len = _find_best_context_fragment(text, left_context, from_left=True)
        if left_pos is not None:
            insertion_point = left_pos + left_len
            block_span = _find_enclosing_block_span(text, insertion_point)
            if block_span is not None:
                return _normalize_fallback_span(text, block_span)
            return (insertion_point, insertion_point)

        return None

    preferred_end = end if end is not None else start

    if preferred_end > start:
        candidate = text[start:preferred_end]
        if _is_safe_anchor_text(candidate):
            return (start, preferred_end)
        table_span = _find_nearest_table_cell_span(text, start)
        if table_span is not None:
            return _normalize_fallback_span(text, table_span)
        return (start, start)

    block_span = _find_enclosing_block_span(text, start)
    if block_span is not None:
        return _normalize_fallback_span(text, block_span)

    table_span = _find_nearest_table_cell_span(text, start)
    if table_span is not None:
        return _normalize_fallback_span(text, table_span)

    return (start, start)


def _is_inside_heading(text: str, pos: int) -> bool:
    """Return True if *pos* falls inside an <h1>–<h6> tag span."""
    for m in re.finditer(r"<h[1-6]\b[^>]*>.*?</h[1-6]>", text, re.IGNORECASE | re.DOTALL):
        if m.start() <= pos < m.end():
            return True
    return False


def _skip_past_heading(text: str, pos: int) -> int:
    """If *pos* is inside a heading, advance it to just after that heading's closing tag."""
    for m in re.finditer(r"<h[1-6]\b[^>]*>.*?</h[1-6]>", text, re.IGNORECASE | re.DOTALL):
        if m.start() <= pos < m.end():
            return m.end()
    return pos


def _is_short_label_anchor(anchor: str) -> bool:
    plain = _html_to_plain_text(str(anchor or "")).strip()
    if not plain:
        return False
    if plain[-1:] in ".?!:;":
        return False
    tokens = [token for token in re.split(r"\s+", plain) if token]
    has_numeric_token = any(any(ch.isdigit() for ch in token) for token in tokens)
    return len(tokens) <= 3 and len(plain) <= 24 and has_numeric_token


def _pick_last_resort_anchor_span(text: str, left_context: str, right_context: str) -> Optional[Tuple[int, int]]:
    """Return a deterministic insertion point when normal fallback resolution fails.

    This avoids skipping an active comment marker entirely when anchor text was
    removed during edits. We prefer contextual insertion, then first visible text,
    then position 0 as the final fallback.
    Never places a marker inside a heading tag.
    """
    right_pos, _ = _find_best_context_fragment(text, right_context, from_left=False)
    if right_pos is not None:
        safe = _skip_past_heading(text, right_pos)
        return (safe, safe)

    left_pos, left_len = _find_best_context_fragment(text, left_context, from_left=True)
    if left_pos is not None:
        safe = _skip_past_heading(text, left_pos + left_len)
        return (safe, safe)

    heading_ranges = [(m.start(), m.end()) for m in re.finditer(r"<h[1-6]\b[^>]*>.*?</h[1-6]>", text, re.I | re.S)]
    for span_start, _span_end in _collect_text_spans(text, 0, len(text)):
        if not any(hs <= span_start < he for hs, he in heading_ranges):
            return (span_start, span_start)

    if text is not None:
        return (0, 0)
    return None


def _should_route_deleted_anchor_to_heading(anchor: str, span_text: str, context_score: int = 0) -> bool:
    anchor_text = str(anchor or "").strip()
    candidate_text = str(span_text or "").strip()
    if not anchor_text or not candidate_text:
        return False

    # If a multi-word/sentence anchor disappeared and the best contextual
    # fallback collapses to a short surviving token, treat it as a deletion and
    # pin it to the nearest heading instead of drifting onto sibling content.
    if _is_short_label_anchor(anchor_text):
        return False

    anchor_tokens = [token for token in re.split(r"\s+", anchor_text) if token]
    candidate_tokens = [token for token in re.split(r"\s+", candidate_text) if token]
    if len(anchor_tokens) == 1:
        anchor_token = anchor_tokens[0]
        candidate_token = candidate_tokens[0] if len(candidate_tokens) == 1 else ""
        if (
            candidate_token
            and anchor_token.lower() != candidate_token.lower()
            and not any(ch.isdigit() for ch in (anchor_token + candidate_token))
            and len(anchor_token) >= 5
            and context_score < _MIN_CONTEXT_SCORE
        ):
            return True
        return False

    if " " not in anchor_text:
        return False
    return len(candidate_text) < max(_MIN_CONTEXT_FRAGMENT, len(anchor_text) // 2)


def _preview_text(value: str, limit: int = 80) -> str:
    text = _html_to_plain_text(str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _build_comment_marker_map(
    comments: List[Dict[str, Any]],
    inline_props: List[Dict[str, str]],
    marker_details_by_ref: Optional[Dict[str, Dict[str, Any]]] = None,
    visible_refs: Optional[set] = None,
) -> List[Dict[str, Any]]:
    comments_by_id = {str(comment.get("id") or ""): comment for comment in comments if str(comment.get("id") or "")}
    details_by_ref = marker_details_by_ref or {}
    visible = visible_refs or set()
    entries: List[Dict[str, Any]] = []

    for item in inline_props:
        comment_id = str(item.get("comment_id") or "")
        ref = str(item.get("ref") or "")
        if not comment_id or not ref:
            continue
        comment = comments_by_id.get(comment_id, {})
        detail = details_by_ref.get(ref, {})
        entries.append(
            {
                "comment_id": comment_id,
                "comment_body_preview": _preview_text(str(comment.get("body_plain") or ""), limit=120),
                "ref": ref,
                "original_selection_preview": _preview_text(str(item.get("anchor_html") or "")),
                "visible_in_section": ref in visible if visible else False,
                "visible_anchor_text_preview": str(detail.get("after_anchor_text_preview") or ""),
                "classification": str(detail.get("classification") or ""),
            }
        )

    entries.sort(key=lambda entry: (entry.get("comment_id") or "", entry.get("ref") or ""))
    return entries


def _resolve_deleted_heading_preference(
    text: str,
    preferred_index: Optional[int],
    left_context: str,
) -> Optional[int]:
    left_pos, left_len = _find_best_context_fragment(text, left_context, from_left=True)
    if left_pos is not None:
        return left_pos + left_len
    return preferred_index


def _pick_deleted_heading_anchor_span(
    text: str,
    left_context: str,
    preferred_index: Optional[int],
    heading_path: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Tuple[int, int]]:
    if heading_path:
        heading_span = _pick_heading_span_from_path(text, heading_path)
        if heading_span is not None:
            return heading_span

    context_lower = str(left_context or "").lower()
    if context_lower:
        heading_re = re.compile(r"<(h[1-6])\b[^>]*>(.*?)</\1>", re.IGNORECASE | re.DOTALL)
        context_matches: List[Tuple[int, int, int]] = []
        for match in heading_re.finditer(text):
            heading_text = _html_to_plain_text(match.group(2)).strip().lower()
            if heading_text and heading_text in context_lower:
                context_matches.append((match.start(), match.start(2), match.end(2)))
        if context_matches:
            chosen = context_matches[-1]
            if chosen[2] > chosen[1]:
                return (chosen[1], chosen[2])

    heading_preference = _resolve_deleted_heading_preference(text, preferred_index, left_context)
    chosen = _pick_heading_anchor_candidate(text, heading_preference)
    if chosen is None:
        return None
    if chosen[3] <= chosen[2]:
        return None
    return (chosen[2], chosen[3])


def _pick_deleted_heading_insertion_point(
    text: str,
    left_context: str,
    preferred_index: Optional[int],
    heading_path: Optional[List[Dict[str, Any]]] = None,
) -> Optional[int]:
    if heading_path:
        heading_candidate = _pick_heading_candidate_from_path(text, heading_path)
        if heading_candidate is not None:
            return int(heading_candidate["end"])

    context_lower = str(left_context or "").lower()
    if context_lower:
        heading_re = re.compile(r"<(h[1-6])\b[^>]*>(.*?)</\1>", re.IGNORECASE | re.DOTALL)
        context_matches: List[Tuple[int, int]] = []
        for match in heading_re.finditer(text):
            heading_text = _html_to_plain_text(match.group(2)).strip().lower()
            if heading_text and heading_text in context_lower:
                context_matches.append((match.start(), match.end()))
        if context_matches:
            return context_matches[-1][1]

    heading_preference = _resolve_deleted_heading_preference(text, preferred_index, left_context)
    return _pick_heading_insertion_point(text, heading_preference)


def _pick_heading_span_matching_anchor(
    text: str,
    anchor: str,
    preferred_index: Optional[int],
) -> Optional[Tuple[int, int]]:
    anchor_text = _html_to_plain_text(str(anchor or "")).strip().lower()
    if not anchor_text:
        return None

    heading_re = re.compile(r"<(h[1-6])\b[^>]*>(.*?)</\1>", re.IGNORECASE | re.DOTALL)
    candidates: List[Tuple[int, int, int]] = []
    for match in heading_re.finditer(text):
        heading_text = _html_to_plain_text(match.group(2)).strip().lower()
        if heading_text and anchor_text in heading_text:
            candidates.append((match.start(), match.start(2), match.end(2)))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0])
    chosen = candidates[0]
    if preferred_index is not None:
        prior = [candidate for candidate in candidates if candidate[0] <= preferred_index]
        if prior:
            chosen = prior[-1]
    return (chosen[1], chosen[2])


def _pick_heading_span_near_right_context(
    text: str,
    right_context: str,
    heading_path: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Tuple[int, int]]:
    right_pos, right_len = _find_best_context_fragment(text, right_context, from_left=False)
    if right_pos is None or right_len < _MIN_CONTEXT_FRAGMENT:
        return None

    target_path = [
        str(item.get("normalized_text") or "").strip()
        for item in (heading_path or [])
        if str(item.get("normalized_text") or "").strip()
    ]

    best_candidate: Optional[Dict[str, Any]] = None
    best_score: Optional[Tuple[int, int, int, int]] = None
    for candidate in _iter_heading_candidates(text):
        candidate_start = int(candidate["start"])
        if candidate_start >= right_pos:
            break

        actual_path = [
            str(item.get("normalized_text") or "")
            for item in _heading_path_at_index(text, candidate_start)
            if str(item.get("normalized_text") or "")
        ]
        shared_depth = 0
        max_depth = min(len(actual_path), len(target_path))
        while shared_depth < max_depth and actual_path[shared_depth] == target_path[shared_depth]:
            shared_depth += 1

        score = (
            shared_depth,
            len(actual_path),
            int(candidate.get("level") or 0),
            candidate_start,
        )
        if best_score is None or score > best_score:
            best_score = score
            best_candidate = candidate

    if best_candidate is None:
        return None
    return (int(best_candidate["content_start"]), int(best_candidate["content_end"]))


def _pick_heading_span_from_path(
    text: str,
    heading_path: List[Dict[str, Any]],
) -> Optional[Tuple[int, int]]:
    best_candidate = _pick_heading_candidate_from_path(text, heading_path)
    if best_candidate is None:
        return None
    return (int(best_candidate["content_start"]), int(best_candidate["content_end"]))


def _pick_heading_candidate_from_path(
    text: str,
    heading_path: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    target_path = [
        str(item.get("normalized_text") or "").strip()
        for item in heading_path
        if str(item.get("normalized_text") or "").strip()
    ]
    if not target_path:
        return None

    current_path: List[Dict[str, Any]] = []
    best_candidate: Optional[Dict[str, Any]] = None
    best_depth = 0

    for candidate in _iter_heading_candidates(text):
        while current_path and int(current_path[-1]["level"]) >= int(candidate["level"]):
            current_path.pop()
        current_path.append(candidate)

        current_normalized = [str(item.get("normalized_text") or "") for item in current_path]
        max_depth = min(len(current_normalized), len(target_path))
        matched_depth = 0
        for depth in range(1, max_depth + 1):
            if current_normalized[:depth] == target_path[:depth]:
                matched_depth = depth
            else:
                break

        if matched_depth >= best_depth and matched_depth > 0:
            best_depth = matched_depth
            best_candidate = current_path[matched_depth - 1]

    return best_candidate


def _occurrence_matches_heading_path(
    text: str,
    occurrence_index: int,
    heading_path: Optional[List[Dict[str, Any]]],
) -> bool:
    if not heading_path:
        return True

    expected = [
        str(item.get("normalized_text") or "")
        for item in heading_path
        if str(item.get("normalized_text") or "")
    ]
    if not expected:
        return True

    actual = [
        str(item.get("normalized_text") or "")
        for item in _heading_path_at_index(text, occurrence_index)
        if str(item.get("normalized_text") or "")
    ]
    if not actual:
        return False
    return actual == expected


def _normalize_anchor_for_matching(anchor: str) -> Tuple[str, bool]:
    raw_anchor = str(anchor or "")
    if "<ac:inline-comment-marker" in raw_anchor.lower():
        visible_anchor = _html_to_plain_text(raw_anchor).strip()
        if visible_anchor:
            return visible_anchor, True
    return raw_anchor, False


def _inject_inline_markers(
    storage_html: str,
    markers: List[Dict[str, Any]],
    open_ref_ids: set,  # kept for signature compat but not used for filtering
    section_span: Optional[Tuple[int, int]] = None,
) -> tuple:
    """Re-wrap anchor text with inline-comment-marker tags where text still exists in new storage.
    All markers from old storage are eligible — Confluence already removes markers for resolved
    comments from storage HTML, so anything found in old storage is for an active comment.
    Returns (updated_html, reanchored_count, skipped_count, deleted_anchor_icon_count)."""
    result = storage_html
    scope_start = 0
    scope_end = len(result)
    if section_span is not None:
        raw_start, raw_end = section_span
        scope_start = max(0, min(raw_start, len(result)))
        scope_end = max(scope_start, min(raw_end, len(result)))

    reanchored = 0
    skipped = 0
    deleted_anchor_icon_count = 0
    old_scope_start = 0
    accumulated_injection_delta = 0
    if section_span is not None:
        old_scope_start = int(section_span[0])

    def _commit_injection(span_start_abs: int, span_end_abs: int, wrapped: str) -> None:
        nonlocal result, scope_end, reanchored, accumulated_injection_delta
        replaced_len = span_end_abs - span_start_abs
        result = result[:span_start_abs] + wrapped + result[span_end_abs:]
        delta = len(wrapped) - replaced_len
        scope_end += delta
        accumulated_injection_delta += delta
        reanchored += 1

    def _wrap_deleted_heading(
        ref: str,
        left_context: str,
        preferred_index: Optional[int],
        heading_path: Optional[List[Dict[str, Any]]],
    ) -> bool:
        nonlocal deleted_anchor_icon_count
        heading_span_rel = _pick_deleted_heading_anchor_span(
            search_space,
            left_context,
            preferred_index,
            heading_path=heading_path,
        )
        if heading_span_rel is None:
            return False
        span_start_rel, span_end_rel = heading_span_rel
        span_start_abs = scope_start + span_start_rel
        span_end_abs = scope_start + span_end_rel
        fallback_anchor = search_space[span_start_rel:span_end_rel]
        target_heading_text = _normalize_heading_text(str((heading_path or [{}])[-1].get("text") or ""))
        selected_heading_text = _normalize_heading_text(fallback_anchor)
        if target_heading_text and selected_heading_text and selected_heading_text != target_heading_text:
            insert_rel = _pick_deleted_heading_insertion_point(
                search_space,
                left_context,
                preferred_index,
                heading_path=heading_path,
            )
            if insert_rel is None:
                return False
            insert_rel = _normalize_insertion_point_outside_tag(search_space, insert_rel)
            insert_abs = scope_start + insert_rel
            wrapped = f'<ac:inline-comment-marker ac:ref="{ref}">{_DELETED_COMMENT_ICON_HTML}</ac:inline-comment-marker>'
            _commit_injection(insert_abs, insert_abs, wrapped)
            deleted_anchor_icon_count += 1
            return True
        wrapped = f'<ac:inline-comment-marker ac:ref="{ref}">{fallback_anchor}</ac:inline-comment-marker>'
        _commit_injection(span_start_abs, span_end_abs, wrapped)
        return True

    for m in markers:
        ref = m["ref"]
        anchor = m["anchor_html"]
        left_context = m.get("left_context", "")
        right_context = m.get("right_context", "")
        heading_path = m.get("heading_path") or []
        old_start = int(m.get("start", -1))
        preferred_index: Optional[int] = None
        if old_start >= 0:
            preferred_index = max(0, old_start - old_scope_start + accumulated_injection_delta)
        anchor, anchor_was_nested_marker = _normalize_anchor_for_matching(anchor)
        if not anchor or not anchor.strip():
            skipped += 1
            continue
        search_space = result[scope_start:scope_end]
        if not search_space:
            skipped += 1
            continue
        # Only treat a marker as already preserved when it already exists inside
        # the active search scope. A copy elsewhere on the page should not block
        # forwarding this comment to the nearest heading in the target section.
        if f'ac:ref="{ref}"' in search_space or f"ac:ref='{ref}'" in search_space:
            reanchored += 1
            continue
        if preferred_index is not None:
            preferred_index = max(0, min(preferred_index, len(search_space) - 1))

        if section_span is not None and preferred_index is not None and anchor_was_nested_marker:
            heading_span_rel = _pick_heading_span_matching_anchor(
                search_space,
                anchor,
                preferred_index,
            )
            if heading_span_rel is None:
                heading_span_rel = _pick_heading_span_near_right_context(
                    search_space,
                    right_context,
                    heading_path=heading_path,
                )
            if heading_span_rel is not None:
                span_start_rel, span_end_rel = heading_span_rel
                span_start_abs = scope_start + span_start_rel
                span_end_abs = scope_start + span_end_rel
                fallback_anchor = search_space[span_start_rel:span_end_rel]
                wrapped = f'<ac:inline-comment-marker ac:ref="{ref}">{fallback_anchor}</ac:inline-comment-marker>'
                _commit_injection(span_start_abs, span_end_abs, wrapped)
                continue
            if _wrap_deleted_heading(ref, left_context, preferred_index, heading_path):
                continue

        occurrences = _find_all_occurrences(search_space, anchor)
        anchor_used = anchor
        # Retry with whitespace-stripped anchor.  The original anchor captured
        # from inside an AC macro body (e.g. <info>) may carry a trailing newline
        # that is absent in the new storage after markdown→HTML conversion.
        if not occurrences:
            stripped = anchor.strip()
            if stripped and stripped != anchor:
                strip_occurrences = _find_all_occurrences(search_space, stripped)
                if strip_occurrences:
                    occurrences = strip_occurrences
                    anchor_used = stripped
        if occurrences:
            row_matched_occurrences = [
                index
                for index in occurrences
                if _table_row_context_matches(search_space, index, left_context, right_context)
            ]
            if row_matched_occurrences:
                occurrences = row_matched_occurrences
            elif any(_find_enclosing_table_row_span(search_space, index) is not None for index in occurrences):
                occurrences = []
        selected_index: Optional[int] = None
        if occurrences:
            selected_index = _pick_best_occurrence_by_context(
                text=search_space,
                anchor=anchor_used,
                occurrences=occurrences,
                left_context=left_context,
                right_context=right_context,
                preferred_index=preferred_index,
            )
        if occurrences and preferred_index is not None:
            left_pos, left_len = _find_best_context_fragment(search_space, left_context, from_left=True)
            search_start = (left_pos + left_len) if left_pos is not None else 0
            right_pos, right_len = _find_best_context_fragment(search_space, right_context, from_left=False, start_at=search_start)
            if max(left_len, right_len) < _MIN_CONTEXT_FRAGMENT:
                if _wrap_deleted_heading(ref, left_context, preferred_index, heading_path):
                    continue
        if occurrences and selected_index is None:
            edited_span = _pick_edited_context_span(
                search_space,
                left_context,
                right_context,
                preferred_index=preferred_index,
            )
            if edited_span is not None:
                span_start_rel, span_end_rel = edited_span
                if not _table_row_context_matches(search_space, span_start_rel, left_context, right_context):
                    edited_span = None
                else:
                    edited_anchor = search_space[span_start_rel:span_end_rel]
                    edited_context_score = _score_occurrence_context(
                        search_space,
                        edited_anchor,
                        span_start_rel,
                        left_context,
                        right_context,
                    )
                    if (
                        section_span is not None
                        and preferred_index is not None
                        and (
                            _is_inside_heading(search_space, span_start_rel)
                            or _should_route_deleted_anchor_to_heading(anchor_used, edited_anchor, edited_context_score)
                        )
                    ):
                        if _wrap_deleted_heading(ref, left_context, preferred_index, heading_path):
                            continue
                    span_start_abs = scope_start + span_start_rel
                    span_end_abs = scope_start + span_end_rel
                    fallback_anchor = edited_anchor
                    wrapped = f'<ac:inline-comment-marker ac:ref="{ref}">{fallback_anchor}</ac:inline-comment-marker>'
                    _commit_injection(span_start_abs, span_end_abs, wrapped)
                    continue
            if preferred_index is not None:
                if _wrap_deleted_heading(ref, left_context, preferred_index, heading_path):
                    continue
            if preferred_index is not None:
                nearest = min(occurrences, key=lambda idx: abs(idx - preferred_index))
                max_dist = max(len(anchor_used) * 3, 120)
                if abs(nearest - preferred_index) <= max_dist:
                    selected_index = nearest
        if selected_index is not None:
            if (
                section_span is not None
                and preferred_index is not None
                and heading_path
                and not _occurrence_matches_heading_path(search_space, selected_index, heading_path)
            ):
                selected_context_score = _score_occurrence_context(
                    search_space,
                    anchor_used,
                    selected_index,
                    left_context,
                    right_context,
                )
                if selected_context_score < _MIN_CONTEXT_SCORE:
                    if _wrap_deleted_heading(ref, left_context, preferred_index, heading_path):
                        continue
            if not _is_safe_wrap_span(search_space, selected_index, selected_index + len(anchor_used)):
                selected_index = None
            else:
                selected_index_abs = scope_start + selected_index
                wrapped = f'<ac:inline-comment-marker ac:ref="{ref}">{anchor_used}</ac:inline-comment-marker>'
                _commit_injection(selected_index_abs, selected_index_abs + len(anchor_used), wrapped)
                continue

        # If anchor text changed (edited), use surrounding context to find a
        # safe replacement span so the comment stays on the edited text.
        if not occurrences:
            if section_span is not None and preferred_index is not None and anchor_was_nested_marker:
                heading_span_rel = _pick_heading_span_matching_anchor(
                    search_space,
                    anchor,
                    preferred_index,
                )
                if heading_span_rel is None:
                    heading_span_rel = _pick_heading_span_near_right_context(
                        search_space,
                        right_context,
                        heading_path=heading_path,
                    )
                if heading_span_rel is not None:
                    span_start_rel, span_end_rel = heading_span_rel
                    span_start_abs = scope_start + span_start_rel
                    span_end_abs = scope_start + span_end_rel
                    fallback_anchor = search_space[span_start_rel:span_end_rel]
                    wrapped = f'<ac:inline-comment-marker ac:ref="{ref}">{fallback_anchor}</ac:inline-comment-marker>'
                    _commit_injection(span_start_abs, span_end_abs, wrapped)
                    continue
                if _wrap_deleted_heading(ref, left_context, preferred_index, heading_path):
                    continue
            edited_span = _pick_edited_context_span(
                search_space,
                left_context,
                right_context,
                preferred_index=preferred_index,
            )
            if edited_span is not None:
                span_start_rel, span_end_rel = edited_span
                if not _table_row_context_matches(search_space, span_start_rel, left_context, right_context):
                    edited_span = None
                else:
                    edited_anchor = search_space[span_start_rel:span_end_rel]
                    edited_context_score = _score_occurrence_context(
                        search_space,
                        edited_anchor,
                        span_start_rel,
                        left_context,
                        right_context,
                    )
                    if (
                        section_span is not None
                        and preferred_index is not None
                        and _should_route_deleted_anchor_to_heading(anchor_used, edited_anchor, edited_context_score)
                    ):
                        if _wrap_deleted_heading(ref, left_context, preferred_index, heading_path):
                            continue
                    if not _is_safe_wrap_span(search_space, span_start_rel, span_end_rel):
                        edited_span = None
                    else:
                        span_start_abs = scope_start + span_start_rel
                        span_end_abs = scope_start + span_end_rel
                        fallback_anchor = search_space[span_start_rel:span_end_rel]
                        wrapped = f'<ac:inline-comment-marker ac:ref="{ref}">{fallback_anchor}</ac:inline-comment-marker>'
                        _commit_injection(span_start_abs, span_end_abs, wrapped)
                        continue
            if section_span is not None:
                if _wrap_deleted_heading(ref, left_context, preferred_index, heading_path):
                    continue

        # If original anchor text was deleted entirely, preserve comment at the
        # original position using a visible icon placeholder at that location.
        if not occurrences and preferred_index is not None:
            insert_rel = _find_deleted_icon_insertion_point(
                search_space, preferred_index, left_context, right_context
            )
            insert_abs = scope_start + insert_rel
            wrapped = f'<ac:inline-comment-marker ac:ref="{ref}">{_DELETED_COMMENT_ICON_HTML}</ac:inline-comment-marker>'
            _commit_injection(insert_abs, insert_abs, wrapped)
            deleted_anchor_icon_count += 1
            continue

        fallback_span = _pick_fallback_anchor_span(search_space, left_context, right_context)
        if fallback_span is None:
            fallback_span = _pick_last_resort_anchor_span(search_space, left_context, right_context)
            if fallback_span is None:
                skipped += 1
                continue

        span_start_rel, span_end_rel = fallback_span
        span_start_abs = scope_start + span_start_rel
        span_end_abs = scope_start + span_end_rel

        if span_end_rel > span_start_rel:
            if not _is_safe_wrap_span(search_space, span_start_rel, span_end_rel):
                if section_span is not None and preferred_index is not None:
                    if _wrap_deleted_heading(ref, left_context, preferred_index, heading_path):
                        continue
                insert_rel = _normalize_insertion_point_outside_tag(search_space, span_start_rel)
                span_start_rel = insert_rel
                span_end_rel = insert_rel
                span_start_abs = scope_start + span_start_rel
                span_end_abs = span_start_abs
                fallback_anchor = _DELETED_COMMENT_ICON_HTML
                deleted_anchor_icon_count += 1
            else:
                fallback_anchor = search_space[span_start_rel:span_end_rel]
        else:
            nearest_token_span = _pick_nearest_text_token_span(search_space, span_start_rel)
            if nearest_token_span is not None:
                token_start_rel, token_end_rel = nearest_token_span
                span_start_rel, span_end_rel = token_start_rel, token_end_rel
                span_start_abs = scope_start + span_start_rel
                span_end_abs = scope_start + span_end_rel
                if not _is_safe_wrap_span(search_space, span_start_rel, span_end_rel):
                    if section_span is not None and preferred_index is not None:
                        if _wrap_deleted_heading(ref, left_context, preferred_index, heading_path):
                            continue
                    insert_rel = _normalize_insertion_point_outside_tag(search_space, span_start_rel)
                    span_start_rel = insert_rel
                    span_end_rel = insert_rel
                    span_start_abs = scope_start + span_start_rel
                    span_end_abs = span_start_abs
                    fallback_anchor = _DELETED_COMMENT_ICON_HTML
                    deleted_anchor_icon_count += 1
                else:
                    fallback_anchor = search_space[span_start_rel:span_end_rel]
            else:
                if preferred_index is not None:
                    insert_rel = _normalize_insertion_point_outside_tag(search_space, preferred_index)
                else:
                    insert_rel = _normalize_insertion_point_outside_tag(search_space, span_start_rel)
                span_start_rel = insert_rel
                span_end_rel = insert_rel
                span_start_abs = scope_start + span_start_rel
                span_end_abs = span_start_abs
                fallback_anchor = _DELETED_COMMENT_ICON_HTML
                deleted_anchor_icon_count += 1

        wrapped = f'<ac:inline-comment-marker ac:ref="{ref}">{fallback_anchor}</ac:inline-comment-marker>'
        _commit_injection(span_start_abs, span_end_abs, wrapped)
    return result, reanchored, skipped, deleted_anchor_icon_count


def _update_page_with_storage(
    base_url: str,
    page_id: str,
    version: int,
    title: str,
    storage_html: str,
    auth: Any,
    headers: Dict[str, str],
) -> bool:
    """PUT the page with new storage HTML content, retrying on version conflicts."""
    url = f"{base_url.rstrip('/')}/rest/api/content/{page_id}"
    put_headers = {k: v for k, v in headers.items()}
    put_headers["Content-Type"] = "application/json"

    current_version = int(version)
    current_title = str(title or "")
    for _attempt in range(3):
        payload = {
            "version": {"number": current_version},
            "title": current_title,
            "type": "page",
            "body": {"storage": {"value": storage_html, "representation": "storage"}},
        }
        resp = requests.put(url, json=payload, auth=auth, headers=put_headers, timeout=60)
        if resp.status_code in (200, 201):
            return True
        if resp.status_code != 409:
            return False

        try:
            latest_resp = requests.get(
                url,
                params={"expand": STORAGE_EXPAND},
                auth=auth,
                headers=headers,
                timeout=60,
            )
            latest_resp.raise_for_status()
            latest_data = latest_resp.json()
            current_version = int(((latest_data.get("version") or {}).get("number") or 0)) + 1
            current_title = str(latest_data.get("title") or current_title)
        except Exception:
            return False

    return False


def _reanchor_after_overwrite(
    args: argparse.Namespace,
    config_module: Any,
    old_markers: List[Dict[str, Any]],
    open_ref_ids: set,
    heading_title: str,
    heading_level: Optional[int] = None,
) -> Dict[str, Any]:
    """After overwrite: fetch new storage, re-inject inline markers for open comments,
    then push the updated storage back to Confluence."""
    if not old_markers or not open_ref_ids:
        return {"status": "skipped", "reason": "no open inline markers found before overwrite"}
    try:
        page_info = _fetch_page_storage_with_auth(args, config_module)
        new_storage = page_info["storage_html"]
        new_version = page_info["version"] + 1
        title = page_info["title"]
        auth = page_info["auth"]
        hdrs = page_info["headers"]
        section_span = _find_heading_section_span(new_storage, heading_title, heading_level=heading_level)
        if section_span is None:
            section_span = _find_surviving_section_span_from_markers(new_storage, old_markers)

        # Strip existing marker wrappers for refs we are about to re-anchor,
        # so comments can move to the correct heading when content is deleted.
        refs_to_strip = set(str(m.get("ref") or "") for m in old_markers if m.get("ref"))
        if refs_to_strip:
            new_storage, _ = _strip_inline_markers_by_ref(new_storage, refs_to_strip)

        # Use all captured markers. Confluence already removes markers for
        # resolved comments from storage HTML, so every marker in old_markers
        # is for an active comment. The UUID-based ac:ref does not match the
        # numeric comment IDs in open_ref_ids, so filtering here would always
        # produce an empty list and suppress re-injection entirely.
        updated_storage, reanchored, skipped, deleted_anchor_icon_count = _inject_inline_markers(
            new_storage,
            old_markers,
            open_ref_ids,
            section_span=section_span,
        )
        payload_section_span = _find_heading_section_span(
            updated_storage,
            heading_title,
            heading_level=heading_level,
        )
        if payload_section_span is None:
            payload_section_span = _find_surviving_section_span_from_markers(updated_storage, old_markers)
        payload_section_html = (
            updated_storage
            if payload_section_span is None
            else updated_storage[payload_section_span[0]:payload_section_span[1]]
        )

        if reanchored == 0:
            return {
                "status": "nothing-to-anchor",
                "reanchored": 0,
                "skipped": skipped,
                "payload_section_html": payload_section_html,
            }

        if updated_storage == new_storage:
            return {
                "status": "no-change",
                "reanchored": 0,
                "skipped": skipped,
                "payload_section_html": payload_section_html,
            }

        success = _update_page_with_storage(
            args.base_url, args.page_id, new_version, title, updated_storage, auth, hdrs
        )
        return {
            "status": "ok" if success else "update-failed",
            "reanchored": reanchored,
            "skipped": skipped,
            "deleted_anchor_icon_count": deleted_anchor_icon_count,
            "section_found": section_span is not None,
            "payload_storage_html": updated_storage,
            "payload_section_html": payload_section_html,
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


# ---------------------------------------------------------------------------

def _default_guard_script() -> str:
    return os.path.join(_bundled_clone_root(), "scdp_compare_guard.py")


def _build_guard_command(args: argparse.Namespace, guard_json_path: str) -> List[str]:
    command: List[str] = [
        args.python_executable,
        args.guard_script,
        "--project-root",
        args.project_root,
        "--page-id",
        args.page_id,
        "--md-path",
        args.md_path,
        "--heading-title",
        args.heading_title,
        "--compare-mode",
        args.compare_mode,
        "--output-json",
        guard_json_path,
    ]

    if args.split_level is not None:
        command.extend(["--split-level", str(args.split_level)])

    if args.apply:
        command.append("--apply")
    if args.yes:
        command.append("--yes")
    if args.force_scdp_override:
        command.append("--force-scdp-override")
    if args.yes_override:
        command.append("--yes-override")
    if args.no_prompt_override:
        command.append("--no-prompt-override")
        if args.no_prompt_missing_heading or args.no_prompt_override:
            command.append("--no-prompt-missing-heading")
    if args.reflect_on_page:
        command.append("--reflect-on-page")
        command.extend(["--reflect-mode", args.reflect_mode])
        if args.reflect_keep_after_refresh:
            command.append("--reflect-keep-after-refresh")
        if args.reflect_persist_manual:
            command.append("--reflect-persist-manual")
        if args.reflect_compare_latest_previous:
            command.append("--reflect-compare-latest-previous")
        command.extend(["--reflect-auto-clear-seconds", str(args.reflect_auto_clear_seconds)])

    return command


def _run_guard_command(command: List[str]) -> Dict[str, Any]:
    process = subprocess.run(command, text=True, capture_output=True, encoding="utf-8", errors="replace")
    if process.stdout:
        _write_text_safe(sys.stdout, process.stdout)
    if process.returncode != 0:
        if process.stderr:
            _write_text_safe(sys.stderr, process.stderr)
        raise RuntimeError(f"scdp_compare_guard.py failed with exit code {process.returncode}")
    return {
        "returncode": process.returncode,
        "stdout": process.stdout,
        "stderr": process.stderr,
    }


def _comment_sets(comments: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    mapped: Dict[str, Dict[str, Any]] = {}
    for item in comments:
        comment_id = str(item.get("id") or "").strip()
        if comment_id:
            mapped[comment_id] = item
    return mapped


def _build_comment_delta(before_active: List[Dict[str, Any]], after_active: List[Dict[str, Any]], 
                          before_all: List[Dict[str, Any]], after_all: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build comprehensive delta tracking both active and resolved comments."""
    before_active_map = _comment_sets(before_active)
    after_active_map = _comment_sets(after_active)
    before_all_map = _comment_sets(before_all)
    after_all_map = _comment_sets(after_all)

    before_active_ids = set(before_active_map)
    after_active_ids = set(after_active_map)
    before_all_ids = set(before_all_map)
    after_all_ids = set(after_all_map)

    # Active comment tracking
    active_preserved_ids = sorted(before_active_ids & after_active_ids)
    active_missing_ids = sorted(before_active_ids - after_active_ids)
    active_new_ids = sorted(after_active_ids - before_all_ids)

    # Auto-resolved tracking: was active before, resolved after (still in system as resolved)
    auto_resolved_ids = sorted([cid for cid in active_missing_ids if cid in after_all_ids])

    # Resolved comment tracking
    before_resolved_ids = set(cid for cid in before_all_ids if before_all_map[cid].get("status") != "current")
    after_resolved_ids = set(cid for cid in after_all_ids if after_all_map[cid].get("status") != "current")
    resolved_preserved_ids = sorted(before_resolved_ids & after_resolved_ids)
    resolved_missing_ids = sorted(before_resolved_ids - after_resolved_ids)
    resolved_new_ids = sorted(after_resolved_ids - before_resolved_ids)

    return {
        # Active comments
        "before_active_count": len(before_active),
        "after_active_count": len(after_active),
        "active_preserved_count": len(active_preserved_ids),
        "active_missing_count": len([cid for cid in active_missing_ids if cid not in auto_resolved_ids]),
        "active_auto_resolved_count": len(auto_resolved_ids),
        "active_new_count": len(active_new_ids),
        # Resolved comments
        "before_resolved_count": len(before_resolved_ids),
        "after_resolved_count": len(after_resolved_ids),
        "resolved_preserved_count": len(resolved_preserved_ids),
        "resolved_missing_count": len(resolved_missing_ids),
        "resolved_new_count": len(resolved_new_ids),
        # Tracking IDs
        "active_preserved_ids": sorted(active_preserved_ids),
        "auto_resolved_ids": auto_resolved_ids,
        "active_missing_ids": sorted([cid for cid in active_missing_ids if cid not in auto_resolved_ids]),
        "active_new_ids": sorted(active_new_ids),
        "resolved_preserved_ids": resolved_preserved_ids,
        "resolved_missing_ids": resolved_missing_ids,
        "resolved_new_ids": resolved_new_ids,
        # Preview
        "active_missing_preview": [
            {
                "id": cid,
                "author": before_active_map[cid].get("author"),
                "body_preview": str(before_active_map[cid].get("body_plain") or "")[:220],
            }
            for cid in sorted([cid for cid in active_missing_ids if cid not in auto_resolved_ids])[:20]
        ],
        "auto_resolved_preview": [
            {
                "id": cid,
                "author": before_active_map[cid].get("author"),
                "body_preview": str(before_active_map[cid].get("body_plain") or "")[:220],
            }
            for cid in auto_resolved_ids[:20]
        ],
        "resolved_preserved_preview": [
            {
                "id": cid,
                "author": before_all_map[cid].get("author"),
                "body_preview": str(before_all_map[cid].get("body_plain") or "")[:220],
            }
            for cid in resolved_preserved_ids[:20]
        ],
        "resolved_missing_preview": [
            {
                "id": cid,
                "author": before_all_map[cid].get("author"),
                "body_preview": str(before_all_map[cid].get("body_plain") or "")[:220],
            }
            for cid in resolved_missing_ids[:20]
        ],
        "resolved_new_preview": [
            {
                "id": cid,
                "author": after_all_map[cid].get("author"),
                "body_preview": str(after_all_map[cid].get("body_plain") or "")[:220],
            }
            for cid in resolved_new_ids[:20]
        ],
    }


def _calculate_similarity_score(before_text: str, after_text: str) -> float:
    """Calculate text similarity as % match (0-100). Returns 0 if either is empty."""
    before = str(before_text or "").strip()
    after = str(after_text or "").strip()
    if not before or not after:
        return 0.0 if before != after else 100.0
    
    # Exact match
    if before.lower() == after.lower():
        return 100.0
    
    # Simple common character count similarity
    before_chars = set(before.lower())
    after_chars = set(after.lower())
    if not before_chars or not after_chars:
        return 0.0
    intersection = len(before_chars & after_chars)
    union = len(before_chars | after_chars)
    return round((intersection / union) * 100, 1) if union > 0 else 0.0


def _build_position_audit(
    before_active: List[Dict[str, Any]],
    after_active: List[Dict[str, Any]],
    preserved_ids: List[str],
) -> List[Dict[str, Any]]:
    """Audit position/location of preserved comments by comparing body similarity."""
    before_map = {c["id"]: c for c in before_active}
    after_map = {c["id"]: c for c in after_active}
    
    audit = []
    for comment_id in preserved_ids:
        before_c = before_map.get(comment_id) or {}
        after_c = after_map.get(comment_id) or {}
        before_body = before_c.get("body_plain", "")
        after_body = after_c.get("body_plain", "")
        similarity = _calculate_similarity_score(before_body, after_body)
        
        audit.append({
            "id": comment_id,
            "author": before_c.get("author"),
            "body_before_preview": (before_body or "")[:200],
            "body_after_preview": (after_body or "")[:200],
            "similarity_percent": similarity,
            "same_location": similarity == 100.0,
        })
    return audit


def _normalize_audit_context(value: str) -> str:
    plain = _html_to_plain_text(value or "")
    plain = re.sub(r"\s+", " ", plain).strip().lower()
    return plain


def _build_storage_anchor_audit_from_markers(
    before_markers: List[Dict[str, Any]],
    after_markers: List[Dict[str, Any]],
) -> Dict[str, Any]:
    after_by_ref = {str(marker.get("ref") or ""): marker for marker in after_markers if marker.get("ref")}
    details: List[Dict[str, Any]] = []

    for before_marker in before_markers:
        ref = str(before_marker.get("ref") or "")
        if not ref:
            continue

        before_anchor_text = _normalize_audit_context(str(before_marker.get("anchor_html") or ""))
        before_left = _normalize_audit_context(str(before_marker.get("left_context") or ""))
        before_right = _normalize_audit_context(str(before_marker.get("right_context") or ""))
        before_start = int(before_marker.get("start", -1))
        after_marker = after_by_ref.get(ref)

        item: Dict[str, Any] = {
            "ref": ref,
            "before_anchor_text_preview": before_anchor_text[:200],
            "after_anchor_text_preview": "",
            "before_start": before_start,
            "after_start": None,
            "offset_delta": None,
            "left_context_match_chars": 0,
            "right_context_match_chars": 0,
            "local_context_score": 0,
            "same_anchor_text": False,
            "visible_after_publish": False,
            "exact_position": False,
            "classification": "not_visible_after_publish",
        }

        if after_marker is None:
            details.append(item)
            continue

        after_anchor_text = _normalize_audit_context(str(after_marker.get("anchor_html") or ""))
        after_left = _normalize_audit_context(str(after_marker.get("left_context") or ""))
        after_right = _normalize_audit_context(str(after_marker.get("right_context") or ""))
        after_start = int(after_marker.get("start", -1))
        left_match = _common_suffix_len(before_left, after_left)
        right_match = _common_prefix_len(before_right, after_right)
        local_context_score = left_match + right_match
        offset_delta = abs(after_start - before_start) if before_start >= 0 and after_start >= 0 else None
        same_anchor_text = bool(before_anchor_text) and before_anchor_text == after_anchor_text
        exact_position = False

        if offset_delta is not None:
            max_offset_delta = max(len(before_anchor_text) * 4, 120)
            available_context = min(len(before_left), len(after_left)) + min(len(before_right), len(after_right))
            required_context = max(1, min(_MIN_CONTEXT_SCORE, available_context))
            exact_position = local_context_score >= required_context and offset_delta <= max_offset_delta

        classification = "reanchored_with_changed_local_context"
        if exact_position:
            classification = "exact_local_position"
        elif same_anchor_text:
            classification = "visible_same_anchor_text_but_context_changed"

        item.update(
            {
                "after_anchor_text_preview": after_anchor_text[:200],
                "after_start": after_start,
                "offset_delta": offset_delta,
                "left_context_match_chars": left_match,
                "right_context_match_chars": right_match,
                "local_context_score": local_context_score,
                "same_anchor_text": same_anchor_text,
                "visible_after_publish": True,
                "exact_position": exact_position,
                "classification": classification,
            }
        )
        details.append(item)

    visible_count = sum(1 for item in details if item["visible_after_publish"])
    exact_count = sum(1 for item in details if item["exact_position"])
    same_anchor_text_count = sum(1 for item in details if item["same_anchor_text"])
    return {
        "method": "storage_inline_marker_context",
        "scope": "recoverable_inline_markers_only",
        "recoverable_marker_count": len(details),
        "visible_marker_count": visible_count,
        "exact_position_count": exact_count,
        "same_anchor_text_count": same_anchor_text_count,
        "details": details[:50],
    }


def _build_storage_anchor_audit(
    args: argparse.Namespace,
    config_module: Any,
    heading_title: str,
    heading_level: Optional[int],
    before_markers: List[Dict[str, Any]],
    before_section_span: Optional[Tuple[int, int]],
) -> Dict[str, Any]:
    audit = {
        "method": "storage_inline_marker_context",
        "scope": "recoverable_inline_markers_only",
        "recoverable_marker_count": len(before_markers),
        "visible_marker_count": 0,
        "exact_position_count": 0,
        "same_anchor_text_count": 0,
        "section_found": False,
        "details": [],
    }
    if not args.apply or not before_markers:
        return audit

    try:
        before_scope_start = int(before_section_span[0]) if before_section_span is not None else 0
        normalized_before_markers: List[Dict[str, Any]] = []
        for marker in before_markers:
            normalized = dict(marker)
            if int(normalized.get("start", -1)) >= 0:
                normalized["start"] = int(normalized.get("start", -1)) - before_scope_start
            if int(normalized.get("end", -1)) >= 0:
                normalized["end"] = int(normalized.get("end", -1)) - before_scope_start
            normalized_before_markers.append(normalized)

        page_info = _fetch_page_storage_with_auth(args, config_module)
        storage_html = page_info.get("storage_html") or ""
        section_span = _find_heading_section_span(storage_html, heading_title, heading_level=heading_level)
        audit["section_found"] = section_span is not None
        section_html = storage_html if section_span is None else storage_html[section_span[0]:section_span[1]]
        after_markers = _extract_inline_markers(section_html)
        summary = _build_storage_anchor_audit_from_markers(normalized_before_markers, after_markers)
        audit.update(summary)
        audit["section_found"] = section_span is not None
    except Exception as exc:
        audit["error"] = str(exc)

    return audit


def _build_comment_audit_summary(
    before_comments: List[Dict[str, Any]],
    after_comments: List[Dict[str, Any]],
    preserved_ids: List[str],
) -> Dict[str, Any]:
    audit_details = _build_position_audit(before_comments, after_comments, preserved_ids)
    return {
        "method": "comment_body_similarity_only",
        "total_preserved": len(preserved_ids),
        "same_location_count": sum(1 for item in audit_details if item["same_location"]),
        "avg_similarity_percent": round(
            sum(item["similarity_percent"] for item in audit_details) / max(1, len(audit_details)),
            1,
        ) if audit_details else 0.0,
        "details": audit_details[:50],
    }


def _extract_compare_snapshot(compare_json: Dict[str, Any]) -> Dict[str, Any]:
    guard = compare_json.get("guard") or {}
    decision = compare_json.get("decision") or {}
    compare = compare_json.get("compare") or {}
    markdown_summary = ((compare.get("markdown") or {}).get("summary") or {})
    storage_summary = ((compare.get("storage") or {}).get("summary") or {})

    return {
        "guard_status": guard.get("status"),
        "drift": bool(guard.get("drift")),
        "safe_to_publish": bool(guard.get("safe_to_publish")),
        "override_required": bool(decision.get("override_required")),
        "final_allowed": bool(decision.get("final_allowed")),
        "markdown_summary": markdown_summary,
        "storage_summary": storage_summary,
    }


def _build_inline_visibility_audit(
    args: argparse.Namespace,
    config_module: Any,
    heading_title: str,
    heading_level: Optional[int],
    recoverable_marker_count: int,
    active_comment_count: int,
    supplemented_marker_count: int,
) -> Dict[str, Any]:
    audit = {
        "active_comment_count": active_comment_count,
        "recoverable_marker_count": recoverable_marker_count,
        "supplemented_marker_count": supplemented_marker_count,
        "visible_marker_count": 0,
        "section_found": False,
        "visible_marker_refs": [],
    }
    if not args.apply:
        return audit

    try:
        page_info = _fetch_page_storage_with_auth(args, config_module)
        storage_html = page_info.get("storage_html") or ""
        section_span = _find_heading_section_span(storage_html, heading_title, heading_level=heading_level)
        audit["section_found"] = section_span is not None
        section_html = storage_html if section_span is None else storage_html[section_span[0]:section_span[1]]
        markers = _extract_inline_markers(section_html)
        audit["visible_marker_count"] = len(markers)
        audit["visible_marker_refs"] = sorted(str(m.get("ref") or "") for m in markers if m.get("ref"))
    except Exception as exc:
        audit["error"] = str(exc)

    return audit


def _build_reinjection_payload_audit(
    target_markers: List[Dict[str, Any]],
    payload_storage_html: str,
    saved_storage_html: str,
) -> Dict[str, Any]:
    target_refs = {str(marker.get("ref") or "") for marker in target_markers if marker.get("ref")}
    payload_refs = {
        str(marker.get("ref") or "")
        for marker in _extract_inline_markers(payload_storage_html)
        if str(marker.get("ref") or "") in target_refs
    }
    saved_refs = {
        str(marker.get("ref") or "")
        for marker in _extract_inline_markers(saved_storage_html)
        if str(marker.get("ref") or "") in target_refs
    }
    dropped_after_save_refs = sorted(payload_refs - saved_refs)
    unexpected_saved_refs = sorted(saved_refs - payload_refs)
    return {
        "method": "pre_save_vs_saved_storage",
        "scope": "full_page_target_refs",
        "target_ref_count": len(target_refs),
        "payload_visible_marker_count": len(payload_refs),
        "saved_visible_marker_count": len(saved_refs),
        "dropped_after_save_count": len(dropped_after_save_refs),
        "unexpected_saved_marker_count": len(unexpected_saved_refs),
        "dropped_after_save_refs_preview": dropped_after_save_refs[:25],
        "saved_visible_refs_preview": sorted(saved_refs)[:25],
        "unexpected_saved_refs_preview": unexpected_saved_refs[:25],
    }


def _save_json(path: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2)


def _save_text(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_text_safe(stream: Any, text: str) -> None:
    if not text:
        return
    try:
        stream.write(text)
    except UnicodeEncodeError:
        encoding = getattr(stream, "encoding", None) or "utf-8"
        buffer = getattr(stream, "buffer", None)
        if buffer is None:
            stream.write(text.encode(encoding, errors="replace").decode(encoding, errors="replace"))
        else:
            buffer.write(text.encode(encoding, errors="replace"))
    if not text.endswith("\n"):
        stream.write("\n")
    stream.flush()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Isolated DDS helper: compare/apply publish plus pre/post inline-comment preservation audit"
    )

    parser.add_argument(
        "--project-root",
        default=_bundled_clone_root(),
        help="Path to confluence-api-project root. Defaults to the bundled standalone clone under this folder.",
    )
    parser.add_argument("--base-url", required=True, help="Confluence/SCDP base URL, e.g. https://scdp-dev.cisco.com/conf")
    parser.add_argument("--page-id", required=True, help="SCDP Confluence page ID")
    parser.add_argument("--md-path", required=True, help="Markdown file used by Doc Engine publish")
    parser.add_argument(
        "--heading-title",
        required=True,
        help="Heading title used for compare/publish, or 'auto' to resolve exactly one changed heading.",
    )

    parser.add_argument("--compare-mode", choices=["both", "markdown", "storage"], default="both")
    parser.add_argument("--split-level", type=int, choices=range(1, 7), default=1, help="Markdown heading level to split for guard compare")
    parser.add_argument("--apply", action="store_true", help="Run actual overwrite publish after compare")
    parser.add_argument("--yes", action="store_true", help="Pass --yes to guard script")
    parser.add_argument("--force-scdp-override", action="store_true", help="Pass override gate to guard script")
    parser.add_argument("--yes-override", action="store_true", help="Skip override prompt")
    parser.add_argument("--no-prompt-override", action="store_true", help="Do not prompt for override in compare-only runs")
    parser.add_argument(
        "--no-prompt-missing-heading",
        action="store_true",
        help="Do not prompt when the requested heading is missing from local markdown.",
    )
    parser.add_argument(
        "--require-visible-inline-markers",
        action="store_true",
        help="Fail with a non-zero exit code if active comments cannot all be shown inline after publish.",
    )

    parser.add_argument("--reflect-on-page", action="store_true", help="Enable temporary on-page visual diff reflection")
    parser.add_argument("--reflect-mode", choices=["markdown", "storage"], default="markdown")
    parser.add_argument("--reflect-keep-after-refresh", action="store_true")
    parser.add_argument("--reflect-persist-manual", action="store_true")
    parser.add_argument("--reflect-compare-latest-previous", action="store_true")
    parser.add_argument("--reflect-auto-clear-seconds", type=int, default=0)

    parser.add_argument("--username", help="Confluence username")
    parser.add_argument("--token", help="Confluence token/password")
    parser.add_argument("--access-token", help="Confluence bearer token")
    parser.add_argument("--session-cookie", help="Confluence session cookie")

    parser.add_argument("--guard-script", default=_default_guard_script(), help="Path to scdp_compare_guard.py")
    parser.add_argument("--python-executable", default=sys.executable, help="Python executable to run guard script")
    parser.add_argument("--output-dir", default=os.path.abspath(os.path.join(os.path.dirname(__file__), "output")))

    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    args = parse_args()

    if not os.path.exists(args.guard_script):
        raise SystemExit(f"Guard script not found: {args.guard_script}")

    resolved_md_path = os.path.abspath(args.md_path)
    if not os.path.exists(resolved_md_path):
        raise SystemExit(f"Markdown file not found: {resolved_md_path}")

    config_module = _load_config_module(args.project_root)
    requested_heading_title = str(args.heading_title or "").strip()
    if requested_heading_title.lower() == "auto":
        page_info_for_resolution = _fetch_page_storage_with_auth(args, config_module)
        baseline_payload = _load_auto_heading_baseline(args.output_dir, args.page_id, resolved_md_path, args.split_level)
        marker = _fetch_publish_marker_with_auth(args, config_module)
        baseline_markdown = None
        baseline_sections_by_title = None
        if baseline_payload and isinstance(baseline_payload.get("headings"), dict):
            baseline_sections_by_title = {
                str(title or "").strip(): str(markdown or "")
                for title, markdown in (baseline_payload.get("headings") or {}).items()
                if str(title or "").strip()
            }
        if marker:
            raw_section_map = marker.get("published_section_markdown_by_heading")
            if not baseline_sections_by_title and isinstance(raw_section_map, dict):
                baseline_sections_by_title = {}
                for title, raw_value in raw_section_map.items():
                    normalized_title = str(title or "").strip()
                    if not normalized_title:
                        continue
                    baseline_sections_by_title[normalized_title] = _decompress_marker_text(str(raw_value or ""))
            raw_baseline_markdown = marker.get("published_content_markdown")
            if baseline_markdown is None and raw_baseline_markdown:
                baseline_markdown = _decompress_marker_text(str(raw_baseline_markdown))
        changed_titles = _resolve_changed_heading_titles(
            resolved_md_path,
            page_info_for_resolution["storage_html"],
            args.split_level,
            baseline_markdown=baseline_markdown,
            baseline_sections_by_title=baseline_sections_by_title,
        )
        if not changed_titles:
            raise SystemExit(
                "Unable to auto-resolve a changed heading because no split-level section differs from the current page. "
                "Pass --heading-title explicitly."
            )
        if len(changed_titles) > 1:
            return _run_multi_heading_publish(args, changed_titles)
        args.heading_title = changed_titles[0]
    else:
        args.heading_title = requested_heading_title

    timestamp = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    prefix = f"{args.page_id}_{timestamp}"
    os.makedirs(args.output_dir, exist_ok=True)

    before_comments_path = os.path.join(args.output_dir, f"{prefix}_comments_before.json")
    after_comments_path = os.path.join(args.output_dir, f"{prefix}_comments_after.json")
    guard_output_json = os.path.join(args.output_dir, f"{prefix}_compare_guard.json")
    final_report_json = os.path.join(args.output_dir, f"{prefix}_comment_preservation_report.json")
    reanchor_payload_storage_path = os.path.join(args.output_dir, f"{prefix}_reanchor_payload_storage.html")
    saved_storage_after_reanchor_path = os.path.join(args.output_dir, f"{prefix}_saved_storage_after_reanchor.html")
    reanchor_payload_section_path = os.path.join(args.output_dir, f"{prefix}_reanchor_payload_section.html")
    saved_section_after_reanchor_path = os.path.join(args.output_dir, f"{prefix}_saved_section_after_reanchor.html")

    print(f"[source] Markdown file: {resolved_md_path}")
    if requested_heading_title.lower() == "auto":
        print("[source] Requested heading title: auto")
        print(f"[source] Auto-resolved heading title: {args.heading_title}")
    else:
        print(f"[source] Heading title: {args.heading_title}")
    print(
        "[source] Last modified: "
        + dt.datetime.fromtimestamp(os.path.getmtime(resolved_md_path), dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    )

    auth_method, all_comments_before, active_comments_before = _fetch_comments_with_fallback_auth(args, config_module)
    before_inline_props: List[Dict[str, str]] = []
    after_inline_props: List[Dict[str, str]] = []

    # Capture inline comment markers from page storage BEFORE overwrite
    old_markers: List[Dict[str, Any]] = []
    open_ref_ids: set = set(c["id"] for c in active_comments_before)
    supplemented = 0
    if args.apply and open_ref_ids:
        try:
            page_info_before = _fetch_page_storage_with_auth(args, config_module)
            storage_before = page_info_before["storage_html"]
            old_markers_all = _extract_inline_markers(storage_before)
            section_span_before = _find_heading_section_span(
                storage_before, args.heading_title, heading_level=args.split_level
            )
            if section_span_before is not None:
                old_markers = _filter_markers_by_span(old_markers_all, section_span_before)
                old_section_html = storage_before[section_span_before[0]:section_span_before[1]]
                print(
                    f"[anchor-preserve] Found {len(old_markers)} inline marker(s) in heading '{args.heading_title}' before overwrite."
                )
                _record_comment_ref_heading_ownership(
                    args.output_dir,
                    args.page_id,
                    args.heading_title,
                    old_markers,
                )
            else:
                old_markers = old_markers_all
                print(
                    f"[anchor-preserve] Heading '{args.heading_title}' not found in old storage; using all {len(old_markers)} inline marker(s)."
                )

            # If marker tags were removed in prior runs, recover marker refs and
            # anchor text from Confluence inlineProperties for active comments.
            if section_span_before is not None and open_ref_ids:
                inline_props = _fetch_inline_properties_with_fallback_auth(args, config_module, open_ref_ids)
                before_inline_props = list(inline_props)
                owned_refs = _resolve_owned_comment_refs_for_heading(
                    args.output_dir,
                    args.page_id,
                    args.heading_title,
                )
                old_markers, supplemented = _supplement_markers_from_inline_properties(
                    storage_before,
                    section_span_before,
                    old_markers,
                    inline_props,
                    owned_refs=owned_refs or None,
                )
                if supplemented:
                    print(
                        f"[anchor-preserve] Recovered {supplemented} missing marker(s) from inline comment metadata."
                    )
                old_markers, history_supplemented = _supplement_markers_from_history(
                    args.output_dir,
                    args.page_id,
                    args.heading_title,
                    section_span_before,
                    old_markers,
                    inline_props,
                )
                supplemented += history_supplemented
                if history_supplemented:
                    print(
                        f"[anchor-preserve] Recovered {history_supplemented} additional marker(s) from historical compare artifacts."
                    )
            if section_span_before is not None:
                old_markers = _annotate_markers_with_heading_path(
                    old_section_html,
                    int(section_span_before[0]),
                    old_markers,
                )
                old_markers, history_enriched = _enrich_markers_from_history(
                    args.output_dir,
                    args.page_id,
                    args.heading_title,
                    old_markers,
                )
                if history_enriched:
                    print(
                        f"[anchor-preserve] Refined {history_enriched} marker(s) from historical compare artifacts."
                    )
        except Exception as exc:
            print(f"[anchor-preserve] Warning: could not fetch page storage before overwrite: {exc}")

    before_comment_marker_map = _build_comment_marker_map(active_comments_before, before_inline_props)
    _save_json(
        before_comments_path,
        {
            "auth_method": auth_method,
            "all_comments": all_comments_before,
            "active_only": active_comments_before,
            "inline_marker_map": before_comment_marker_map,
        },
    )

    guard_command = _build_guard_command(args, guard_output_json)
    _run_guard_command(guard_command)

    # Re-inject inline markers after overwrite so comments stay open and viewable
    reanchor_result: Dict[str, Any] = {"status": "skipped"}
    if args.apply and old_markers:
        print(f"[anchor-preserve] Re-injecting inline markers for {len(open_ref_ids)} open comment(s)...")
        reanchor_result = _reanchor_after_overwrite(
            args,
            config_module,
            old_markers,
            open_ref_ids,
            args.heading_title,
            heading_level=args.split_level,
        )
        status = reanchor_result.get("status", "")
        reanchored = reanchor_result.get("reanchored", 0)
        skipped = reanchor_result.get("skipped", 0)
        if status == "ok":
            print(f"[anchor-preserve] ✅ Re-anchored {reanchored} inline comment(s). {skipped} could not be re-anchored (anchor text no longer in page).")
        elif status in ("nothing-to-anchor", "no-change"):
            print(f"[anchor-preserve] ℹ️  No inline markers needed re-injection ({skipped} skipped).")
        elif status == "update-failed":
            print(f"[anchor-preserve] ⚠️  Page update to restore markers failed. Comments may be auto-resolved.")
        elif status == "error":
            print(f"[anchor-preserve] ⚠️  Error during re-anchor: {reanchor_result.get('error')}")

    reinjection_payload_audit: Dict[str, Any] = {
        "method": "pre_save_vs_saved_storage",
        "status": "not-captured",
        "target_ref_count": len({str(marker.get("ref") or "") for marker in old_markers if marker.get("ref")}),
        "payload_visible_marker_count": 0,
        "saved_visible_marker_count": 0,
        "dropped_after_save_count": 0,
        "unexpected_saved_marker_count": 0,
        "dropped_after_save_refs_preview": [],
        "saved_visible_refs_preview": [],
        "unexpected_saved_refs_preview": [],
    }
    payload_storage_html = str(reanchor_result.get("payload_storage_html") or "")
    payload_section_html = str(reanchor_result.get("payload_section_html") or "")
    if payload_storage_html:
        _save_text(reanchor_payload_storage_path, payload_storage_html)
    if payload_section_html:
        _save_text(reanchor_payload_section_path, payload_section_html)
        reinjection_payload_audit["status"] = "payload-captured"
        try:
            page_info_after_storage = _fetch_page_storage_with_auth(args, config_module)
            saved_storage_after = page_info_after_storage.get("storage_html") or ""
            _save_text(saved_storage_after_reanchor_path, saved_storage_after)
            saved_section_span = _find_heading_section_span(
                saved_storage_after,
                args.heading_title,
                heading_level=args.split_level,
            )
            saved_section_html = (
                saved_storage_after
                if saved_section_span is None
                else saved_storage_after[saved_section_span[0]:saved_section_span[1]]
            )
            _save_text(saved_section_after_reanchor_path, saved_section_html)
            reinjection_payload_audit = _build_reinjection_payload_audit(
                old_markers,
                payload_storage_html or payload_section_html,
                saved_storage_after,
            )
            reinjection_payload_audit["status"] = "captured"
            reinjection_payload_audit["section_found_after_publish"] = saved_section_span is not None
        except Exception as exc:
            reinjection_payload_audit["status"] = "error"
            reinjection_payload_audit["error"] = str(exc)

    all_comments_after: List[Dict[str, Any]] = all_comments_before
    active_comments_after: List[Dict[str, Any]] = active_comments_before
    if args.apply:
        auth_method_after, all_comments_after, active_comments_after = _fetch_comments_with_fallback_auth(args, config_module)
        if active_comments_after:
            after_inline_props = _fetch_inline_properties_with_fallback_auth(
                args,
                config_module,
                {str(comment.get("id") or "") for comment in active_comments_after if str(comment.get("id") or "")},
            )
    else:
        after_inline_props = list(before_inline_props)

    compare_result = _load_json(guard_output_json)
    delta = _build_comment_delta(active_comments_before, active_comments_after, all_comments_before, all_comments_after)

    # Build active/resolved comment audits for preserved comments.
    preserved_ids = delta.get("active_preserved_ids", [])
    audit_summary = _build_comment_audit_summary(active_comments_before, active_comments_after, preserved_ids)

    before_resolved_comments = [comment for comment in all_comments_before if str(comment.get("status") or "").lower() != "current"]
    after_resolved_comments = [comment for comment in all_comments_after if str(comment.get("status") or "").lower() != "current"]
    resolved_audit_summary = _build_comment_audit_summary(
        before_resolved_comments,
        after_resolved_comments,
        delta.get("resolved_preserved_ids", []),
    )

    inline_visibility = _build_inline_visibility_audit(
        args,
        config_module,
        args.heading_title,
        args.split_level,
        recoverable_marker_count=len(old_markers),
        active_comment_count=delta.get("before_active_count", 0),
        supplemented_marker_count=supplemented,
    )
    storage_anchor_audit = _build_storage_anchor_audit(
        args,
        config_module,
        args.heading_title,
        args.split_level,
        old_markers,
        section_span_before if 'section_span_before' in locals() else None,
    )
    marker_details_by_ref = {
        str(detail.get("ref") or ""): detail
        for detail in storage_anchor_audit.get("details", [])
        if str(detail.get("ref") or "")
    }
    visible_refs = {
        str(ref)
        for ref in inline_visibility.get("visible_marker_refs", [])
        if str(ref)
    }
    before_comment_marker_map = _build_comment_marker_map(
        active_comments_before,
        before_inline_props,
        marker_details_by_ref=marker_details_by_ref,
        visible_refs=visible_refs,
    )
    after_comment_marker_map = _build_comment_marker_map(
        active_comments_after,
        after_inline_props,
        marker_details_by_ref=marker_details_by_ref,
        visible_refs=visible_refs,
    )

    if args.apply:
        _save_json(
            after_comments_path,
            {
                "auth_method": auth_method_after,
                "all_comments": all_comments_after,
                "active_only": active_comments_after,
                "inline_marker_map": after_comment_marker_map,
            },
        )
    else:
        _save_json(
            after_comments_path,
            {
                "auth_method": auth_method,
                "all_comments": all_comments_before,
                "active_only": active_comments_before,
                "inline_marker_map": after_comment_marker_map,
                "note": "Apply not executed; after snapshot equals before snapshot.",
            },
        )

    inline_visibility_gap = False

    if delta.get("before_active_count", 0) == 0:
        recommendation_status = "no-active-comments"
        recommendation_message = "No open comments found on page before publish; nothing to preserve."
    elif args.apply and inline_visibility.get("recoverable_marker_count", 0) < delta.get("before_active_count", 0):
        missing_anchor_count = delta.get("before_active_count", 0) - inline_visibility.get("recoverable_marker_count", 0)
        recommendation_status = "warning-inline-anchor-metadata-missing"
        recommendation_message = (
            f"{missing_anchor_count} active comment(s) have no recoverable inline anchor metadata before publish. "
            "Those comments remain in Confluence, but they cannot all be shown inline automatically."
        )
        inline_visibility_gap = True
    elif args.apply and inline_visibility.get("visible_marker_count", 0) < inline_visibility.get("recoverable_marker_count", 0):
        recommendation_status = "warning-inline-markers-not-visible"
        dropped_after_save_count = reinjection_payload_audit.get("dropped_after_save_count", 0)
        if dropped_after_save_count > 0:
            recommendation_message = (
                f"Only {inline_visibility.get('visible_marker_count', 0)} of {inline_visibility.get('recoverable_marker_count', 0)} recoverable inline marker(s) are visible in saved page storage after publish. "
                f"{dropped_after_save_count} marker(s) were present in the reinjection payload but missing from saved storage after publish."
            )
        else:
            recommendation_message = (
                f"Only {inline_visibility.get('visible_marker_count', 0)} of {inline_visibility.get('recoverable_marker_count', 0)} recoverable inline marker(s) are visible in saved page storage after publish."
            )
        inline_visibility_gap = True
    elif delta.get("active_auto_resolved_count", 0) > 0:
        recommendation_status = "warning-auto-resolved"
        recommendation_message = f"{delta['active_auto_resolved_count']} open comment(s) were auto-resolved during overwrite (anchor text was changed/removed). Review the auto_resolved_preview in the report."
    elif delta.get("active_missing_count", 0) == 0:
        recommendation_status = "ok"
        recommendation_message = "All open comments were preserved after overwrite."
    else:
        recommendation_status = "review-required"
        recommendation_message = "Some open comments are missing after overwrite; use compare report and missing preview for manual re-anchor."

    report = {
        "schemaVersion": "1.0",
        "generatedAt": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "page_id": args.page_id,
            "heading_title": args.heading_title,
            "base_url": args.base_url,
            "md_path": resolved_md_path,
            "apply": bool(args.apply),
            "compare_mode": args.compare_mode,
            "split_level": args.split_level,
        },
        "guard": _extract_compare_snapshot(compare_result),
        "comment_preservation": delta,
        "position_audit": audit_summary,
        "storage_anchor_audit": storage_anchor_audit,
        "reinjection_payload_audit": reinjection_payload_audit,
        "resolved_position_audit": resolved_audit_summary,
        "inline_visibility": inline_visibility,
        "comment_marker_map": {
            "before": before_comment_marker_map,
            "after": after_comment_marker_map,
        },
        "anchor_reinjection": reanchor_result,
        "artifacts": {
            "comments_before": os.path.abspath(before_comments_path),
            "comments_after": os.path.abspath(after_comments_path),
            "compare_guard_json": os.path.abspath(guard_output_json),
            "reanchor_payload_storage": os.path.abspath(reanchor_payload_storage_path) if os.path.exists(reanchor_payload_storage_path) else None,
            "saved_storage_after_reanchor": os.path.abspath(saved_storage_after_reanchor_path) if os.path.exists(saved_storage_after_reanchor_path) else None,
            "reanchor_payload_section": os.path.abspath(reanchor_payload_section_path) if os.path.exists(reanchor_payload_section_path) else None,
            "saved_section_after_reanchor": os.path.abspath(saved_section_after_reanchor_path) if os.path.exists(saved_section_after_reanchor_path) else None,
        },
        "recommendation": {
            "status": recommendation_status,
            "message": recommendation_message,
        },
    }

    _save_json(final_report_json, report)

    if args.apply:
        try:
            baseline_headings = _build_markdown_section_map(resolved_md_path, args.split_level)
            _save_auto_heading_baseline(
                args.output_dir,
                args.page_id,
                resolved_md_path,
                args.split_level,
                baseline_headings,
            )
        except Exception as exc:
            print(f"[source] Warning: could not update local auto-heading baseline: {exc}")

    print(f"REPORT_PATH={os.path.abspath(final_report_json)}")
    print()
    print("=== ACTIVE COMMENTS ===")
    print(f"ACTIVE_COMMENTS_BEFORE={delta['before_active_count']}")
    print(f"ACTIVE_COMMENTS_AFTER={delta['after_active_count']}")
    print(f"ACTIVE_PRESERVED={delta['active_preserved_count']}")
    print(f"ACTIVE_MISSING={delta['active_missing_count']}")
    print(f"ACTIVE_AUTO_RESOLVED={delta['active_auto_resolved_count']}")
    print(f"ACTIVE_NEW={delta['active_new_count']}")
    if args.apply:
        print(f"RECOVERABLE_INLINE_MARKERS={inline_visibility['recoverable_marker_count']}")
        print(f"VISIBLE_INLINE_MARKERS={inline_visibility['visible_marker_count']}")
    print()
    print("=== POSITION VALIDATION ===")
    print(f"PRESERVED_COMMENTS={audit_summary['total_preserved']}")
    print(f"SAME_LOCATION={audit_summary['same_location_count']}")
    print(f"AVG_SIMILARITY={audit_summary['avg_similarity_percent']}%")
    print()
    print("=== RESOLVED COMMENTS ===")
    print(f"RESOLVED_BEFORE={delta['before_resolved_count']}")
    print(f"RESOLVED_AFTER={delta['after_resolved_count']}")
    print(f"RESOLVED_PRESERVED={delta['resolved_preserved_count']}")
    print(f"RESOLVED_SAME_LOCATION={resolved_audit_summary['same_location_count']}")

    if args.require_visible_inline_markers and inline_visibility_gap:
        print()
        print("INLINE_VISIBILITY_CHECK=FAILED")
        print(recommendation_message)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
