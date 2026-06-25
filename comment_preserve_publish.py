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
_CONTEXT_WINDOW = 150  # Increased from 80 to capture more surrounding text for better matching
_MIN_CONTEXT_SCORE = 12
_MIN_CONTEXT_FRAGMENT = 8
_FALLBACK_SEARCH_WINDOW = 120
_MAX_FALLBACK_ANCHOR_CHARS = 220
_MAX_FALLBACK_ANCHOR_NEWLINES = 3
_DELETED_COMMENT_ICON_HTML = "\u200b"
_ORPHAN_COMMENT_EMPTY_ANCHOR_HTML = "\u00a0"
_FULL_PAGE_AUTO_SENTINEL = "__AUTO_FULL_PAGE__"
_ANCHOR_REGION_AUTO_SENTINEL = "__AUTO_ANCHOR_REGION__"
_PAGE_STORAGE_UPDATE_TIMEOUT_SECONDS = 300
_HEADING_PATH_SEPARATOR = " > "
_ORPHAN_CONTEXT_DISPLAY_SEPARATOR = " -> "
_DEFAULT_MANAGED_ANCHOR_START = "docautomation_start"
_DEFAULT_MANAGED_ANCHOR_END = "docautomation_end"
_INLINE_PROPERTIES_PAGE_SIZE = 500


def _bundled_clone_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "standalone_clone"))


def _default_md_input_dir() -> str:
    return os.path.join(_bundled_clone_root(), "input")


def _resolve_md_path(md_path: Optional[str]) -> str:
    if md_path:
        return os.path.abspath(md_path)

    input_dir = _default_md_input_dir()
    if not os.path.isdir(input_dir):
        raise SystemExit(
            "Markdown path not provided and default input directory was not found: "
            f"{input_dir}. Pass --md-path explicitly."
        )

    md_candidates = [
        os.path.join(input_dir, name)
        for name in os.listdir(input_dir)
        if os.path.isfile(os.path.join(input_dir, name)) and name.lower().endswith(".md")
    ]
    if not md_candidates:
        raise SystemExit(
            "Markdown path not provided and no .md files were found in default input directory: "
            f"{input_dir}. Pass --md-path explicitly."
        )

    md_candidates.sort(key=lambda path: os.path.getmtime(path), reverse=True)
    return os.path.abspath(md_candidates[0])


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
            output: List[Dict[str, str]] = []
            seen_comment_ids: set = set()
            start = 0

            while True:
                resp = requests.get(
                    url,
                    params={
                        "expand": "extensions.inlineProperties",
                        "limit": _INLINE_PROPERTIES_PAGE_SIZE,
                        "depth": "root",
                        "start": start,
                    },
                    auth=auth,
                    headers=headers,
                    timeout=60,
                )
                resp.raise_for_status()
                payload = resp.json() or {}
                results = payload.get("results") or []
                if not results:
                    break

                for item in results:
                    comment_id = str(item.get("id") or "").strip()
                    if (
                        not comment_id
                        or comment_id in seen_comment_ids
                        or (open_comment_ids and comment_id not in open_comment_ids)
                    ):
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
                    seen_comment_ids.add(comment_id)

                if len(results) < _INLINE_PROPERTIES_PAGE_SIZE:
                    break
                start += len(results)

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


def _reconcile_existing_markers_from_inline_properties(
    storage_html: str,
    section_span: Tuple[int, int],
    existing_markers: List[Dict[str, Any]],
    inline_props: List[Dict[str, str]],
    owned_refs: Optional[set] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    scope_start, scope_end = section_span
    scope_start = max(0, min(scope_start, len(storage_html)))
    scope_end = max(scope_start, min(scope_end, len(storage_html)))
    search_space = storage_html[scope_start:scope_end]
    if not search_space or not existing_markers:
        return list(existing_markers), 0

    props_by_ref = {
        str(item.get("ref") or ""): str(item.get("anchor_html") or "")
        for item in inline_props
        if str(item.get("ref") or "") and str(item.get("anchor_html") or "")
    }
    if not props_by_ref:
        return list(existing_markers), 0

    reconciled = 0
    updated_markers: List[Dict[str, Any]] = []
    for marker in existing_markers:
        updated = dict(marker)
        ref = str(updated.get("ref") or "")
        inline_anchor = props_by_ref.get(ref, "")
        if not inline_anchor:
            updated_markers.append(updated)
            continue

        current_visible = _marker_visible_anchor_text(str(updated.get("anchor_html") or ""))
        inline_visible = _marker_visible_anchor_text(inline_anchor)
        if not inline_visible or current_visible == inline_visible:
            updated_markers.append(updated)
            continue

        occurrences = _find_all_occurrences(search_space, inline_anchor)
        page_occurrences = _find_all_occurrences(storage_html, inline_anchor)
        selected_rel: Optional[int] = None
        
        # Always prefer heading_path match when available (for nested heading comments).
        heading_path = updated.get("heading_path") or []
        if heading_path and occurrences:
            branch_span = _pick_heading_span_from_path(search_space, heading_path)
            if branch_span is not None:
                branch_start, branch_end = branch_span
                branch_occurrences = [
                    rel_index
                    for rel_index in occurrences
                    if branch_start <= rel_index < branch_end
                ]
            else:
                branch_occurrences = [
                    rel_index
                    for rel_index in occurrences
                    if _occurrence_matches_heading_path_fuzzy(search_space, rel_index, heading_path)
                ]
            if len(branch_occurrences) == 1:
                selected_rel = branch_occurrences[0]
        
        # Fallback: if no heading_path match, use simple occurrence logic.
        if selected_rel is None:
            if len(occurrences) == 1:
                selected_rel = occurrences[0]
                if owned_refs is not None and ref in owned_refs:
                    pass
                elif len(page_occurrences) != 1:
                    selected_rel = None

        if selected_rel is None:
            updated_markers.append(updated)
            continue

        abs_start = scope_start + selected_rel
        abs_end = abs_start + len(inline_anchor)
        updated["anchor_html"] = inline_anchor
        updated["left_context"] = storage_html[max(0, abs_start - _CONTEXT_WINDOW):abs_start]
        updated["right_context"] = storage_html[abs_end:min(len(storage_html), abs_end + _CONTEXT_WINDOW)]
        updated["start"] = abs_start
        updated["end"] = abs_end
        reconciled += 1
        updated_markers.append(updated)

    return updated_markers, reconciled


def _build_top_orphan_markers_from_inline_properties(inline_props: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    markers: List[Dict[str, Any]] = []
    seen_refs: set = set()
    for idx, item in enumerate(inline_props):
        ref = str(item.get("ref") or "").strip()
        if not ref or ref in seen_refs:
            continue
        seen_refs.add(ref)
        markers.append(
            {
                "ref": ref,
                "anchor_html": _ORPHAN_COMMENT_EMPTY_ANCHOR_HTML,
                "full_tag": "",
                "left_context": "",
                "right_context": "",
                "start": idx,
                "end": idx,
                "heading_path": [],
                "orphan_seeded": True,
            }
        )
    return markers


def _seed_missing_orphan_markers(
    existing_markers: List[Dict[str, Any]],
    inline_props: List[Dict[str, str]],
) -> Tuple[List[Dict[str, Any]], int]:
    existing_refs = {str(marker.get("ref") or "").strip() for marker in existing_markers}
    missing_inline_props = [
        item
        for item in inline_props
        if str(item.get("ref") or "").strip() and str(item.get("ref") or "").strip() not in existing_refs
    ]
    if not missing_inline_props:
        return list(existing_markers), 0

    orphan_markers = _build_top_orphan_markers_from_inline_properties(missing_inline_props)
    if not orphan_markers:
        return list(existing_markers), 0

    return list(existing_markers) + orphan_markers, len(orphan_markers)


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
    if plain in {html.unescape(_DELETED_COMMENT_ICON_HTML), "💬"}:
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
        current_visible_text = _marker_visible_anchor_text(str(updated.get("anchor_html") or ""))
        current_heading_path = updated.get("heading_path") or []
        current_in_target_heading = any(
            str(item.get("normalized_text") or "") == target_heading for item in current_heading_path
        )

        candidates = history_candidates.get(ref) or []
        if not candidates:
            updated_markers.append(updated)
            continue

        best_candidate, best_in_target_heading = _select_best_history_candidate(candidates, target_heading)
        candidate_visible_text = _marker_visible_anchor_text(str(best_candidate.get("anchor_html") or ""))
        current_quality = _marker_anchor_quality(updated)
        candidate_quality = _marker_anchor_quality(best_candidate)

        should_apply = False
        if (
            current_visible_text
            and candidate_visible_text
            and current_visible_text != candidate_visible_text
        ):
            should_apply = False
        elif best_in_target_heading and not current_in_target_heading and not current_visible_text:
            should_apply = True
        elif candidate_quality > current_quality and not current_visible_text:
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
    Each entry: {ref, anchor_html, full_tag, force_orphan (if orphaned)}
    force_orphan is set when anchor_html contains only whitespace/non-breaking-space."""
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
            anchor_html = storage_html[open_end:token.start()]
            
            # Mark as orphan if anchor contains only whitespace or non-breaking space
            is_orphan = not _marker_visible_anchor_text(anchor_html)
            
            marker_entry = {
                "ref": str(opened["ref"]),
                "anchor_html": anchor_html,
                "full_tag": storage_html[start:end],
                "left_context": left_context,
                "right_context": right_context,
                "start": start,
                "end": end,
            }
            if is_orphan:
                marker_entry["force_orphan"] = True
            markers.append(marker_entry)
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

    target_path = _split_heading_path(heading_title)
    target = _normalize_heading_text(target_path[-1] if target_path else heading_title)
    if not target:
        return None

    candidates = _iter_heading_candidates(storage_html)
    if not candidates:
        return None

    for idx, candidate in enumerate(candidates):
        current_level = int(candidate["level"])
        if heading_level is not None and current_level != heading_level:
            continue
        heading_text = str(candidate["normalized_text"])
        if heading_text != target:
            continue
        if target_path:
            candidate_path = [
                str(item.get("normalized_text") or "")
                for item in _heading_path_at_index(storage_html, int(candidate["start"]))
            ]
            if candidate_path != [_normalize_heading_text(part) for part in target_path]:
                continue
        section_start = int(candidate["start"])
        section_end = len(storage_html)
        for later_candidate in candidates[idx + 1:]:
            later_level = int(later_candidate["level"])
            if later_level <= current_level:
                section_end = int(later_candidate["start"])
                break
        if section_end <= section_start:
            return None
        return (section_start, section_end)

    relaxed_target = _normalize_heading_text(target_path[-1] if target_path else heading_title, relax=True)
    if not relaxed_target or relaxed_target == target:
        return None

    relaxed_target_path = [_normalize_heading_text(part, relax=True) for part in target_path] if target_path else []
    relaxed_matches: List[Tuple[int, Dict[str, Any]]] = []
    for idx, candidate in enumerate(candidates):
        current_level = int(candidate["level"])
        if heading_level is not None and current_level != heading_level:
            continue
        heading_text = _normalize_heading_text(str(candidate.get("text") or ""), relax=True)
        if heading_text != relaxed_target:
            continue
        if relaxed_target_path:
            candidate_path = [
                _normalize_heading_text(str(item.get("text") or ""), relax=True)
                for item in _heading_path_at_index(storage_html, int(candidate["start"]))
            ]
            if candidate_path != relaxed_target_path:
                continue
        relaxed_matches.append((idx, candidate))

    if len(relaxed_matches) != 1:
        return None

    idx, candidate = relaxed_matches[0]
    current_level = int(candidate["level"])
    section_start = int(candidate["start"])
    section_end = len(storage_html)
    for later_candidate in candidates[idx + 1:]:
        later_level = int(later_candidate["level"])
        if later_level <= current_level:
            section_end = int(later_candidate["start"])
            break
    if section_end <= section_start:
        return None
    return (section_start, section_end)

    return None


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


def _find_anchor_region_span(
    storage_html: str,
    start_anchor_name: str,
    end_anchor_name: str,
) -> Optional[Tuple[int, int]]:
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

    return (int(start_block.get("end") or 0), int(end_block.get("start") or 0))


def _is_anchor_region_target(target: str) -> bool:
    return str(target or "").strip() == _ANCHOR_REGION_AUTO_SENTINEL


def _find_target_storage_span(
    storage_html: str,
    target_title: str,
    heading_level: Optional[int],
    anchor_start_name: str,
    anchor_end_name: str,
) -> Optional[Tuple[int, int]]:
    if _is_anchor_region_target(target_title):
        return _find_anchor_region_span(storage_html, anchor_start_name, anchor_end_name)
    return _find_heading_section_span(storage_html, target_title, heading_level=heading_level)


def _split_heading_path(value: str) -> List[str]:
    return [part.strip() for part in str(value or "").split(_HEADING_PATH_SEPARATOR) if part.strip()]


def _join_heading_path(parts: List[str]) -> str:
    clean_parts = [str(part or "").strip() for part in parts if str(part or "").strip()]
    return _HEADING_PATH_SEPARATOR.join(clean_parts)


def _section_identifier(section: Dict[str, Any]) -> str:
    return str(section.get("path_key") or section.get("title") or "").strip()


def _parse_markdown_sections_from_lines(lines: List[str], split_level: int, default_title: str) -> List[Dict[str, Any]]:
    sections: List[Dict[str, Any]] = []
    current_title: Optional[str] = None
    current_path: List[str] = []
    current_lines: List[str] = []
    preface: List[str] = []
    in_fenced_code = False
    heading_pattern = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
    heading_stack: List[Tuple[int, str]] = []

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
                heading_text = heading_match.group(2).strip() or f"Section {len(sections) + 1}"
                while heading_stack and int(heading_stack[-1][0]) >= heading_depth:
                    heading_stack.pop()
                heading_stack.append((heading_depth, heading_text))

                if heading_depth == split_level:
                    if current_title is not None:
                        sections.append(
                            {
                                "title": current_title,
                                "markdown": "\n".join(current_lines).strip(),
                                "path": list(current_path),
                                "path_key": _join_heading_path(current_path),
                            }
                        )

                    current_title = heading_text
                    current_path = [item[1] for item in heading_stack]
                    current_lines = []
                    continue

                if current_title is not None:
                    current_lines.append(line)
                else:
                    preface.append(line)
                continue

        if current_title is not None:
            current_lines.append(line)
        else:
            preface.append(line)

    if current_title is not None:
        sections.append(
            {
                "title": current_title,
                "markdown": "\n".join(current_lines).strip(),
                "path": list(current_path),
                "path_key": _join_heading_path(current_path),
            }
        )

    if preface and sections:
        sections[0]["markdown"] = ("\n".join(preface).strip() + "\n\n" + str(sections[0].get("markdown") or "")).strip()

    if not sections:
        sections.append(
            {"title": default_title, "markdown": "\n".join(preface).strip(), "path": [default_title], "path_key": default_title}
        )

    return sections


def _parse_markdown_sections(md_path: str, split_level: int = 1) -> List[Dict[str, Any]]:
    if split_level < 1 or split_level > 6:
        raise ValueError("split_level must be between 1 and 6")

    with open(md_path, "r", encoding="utf-8") as handle:
        lines = handle.read().splitlines()

    return _parse_markdown_sections_from_lines(
        lines,
        split_level=split_level,
        default_title=os.path.splitext(os.path.basename(md_path))[0] or "Document",
    )


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


def _deleted_heading_titles(local_titles: List[str], baseline_titles: List[str]) -> List[str]:
    local_title_set = {str(title or "").strip() for title in local_titles if str(title or "").strip()}
    return [
        str(title or "").strip()
        for title in baseline_titles
        if str(title or "").strip() and str(title or "").strip() not in local_title_set
    ]


def _extract_storage_heading_titles(storage_html: str, heading_level: int) -> List[str]:
    return [_section_identifier(section) for section in _extract_storage_sections(storage_html, heading_level)]


def _extract_storage_sections(storage_html: str, heading_level: int) -> List[Dict[str, Any]]:
    sections: List[Dict[str, Any]] = []
    for candidate in _iter_heading_candidates(storage_html or ""):
        if int(candidate["level"]) != int(heading_level):
            continue
        path = [str(item.get("text") or "").strip() for item in _heading_path_at_index(storage_html, int(candidate["start"]))]
        title = str(candidate.get("text") or "").strip()
        if not title:
            continue
        sections.append({"title": title, "path": path, "path_key": _join_heading_path(path)})
    return sections


def _resolve_changed_heading_titles_against_markdown(
    md_path: str,
    baseline_markdown: str,
    split_level: int,
) -> List[str]:
    sections = _parse_markdown_sections(md_path, split_level=split_level)
    baseline_sections = _parse_markdown_sections_from_text(baseline_markdown, split_level=split_level)
    local_titles = [_section_identifier(section) for section in sections if _section_identifier(section)]
    baseline_titles = [
        _section_identifier(section)
        for section in baseline_sections
        if _section_identifier(section)
    ]
    if _deleted_heading_titles(local_titles, baseline_titles):
        return [_FULL_PAGE_AUTO_SENTINEL]
    baseline_by_title = {_section_identifier(section): section for section in baseline_sections if _section_identifier(section)}
    changed_titles: List[str] = []

    for section in sections:
        title = _section_identifier(section)
        if not title:
            continue
        baseline_section = baseline_by_title.get(title)
        if baseline_section is None and str(section.get("title") or "").strip() != title:
            baseline_section = baseline_by_title.get(str(section.get("title") or "").strip())
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

    return changed_titles


def _resolve_changed_heading_titles_against_section_map(
    md_path: str,
    baseline_sections_by_title: Dict[str, str],
    split_level: int,
) -> List[str]:
    sections = _parse_markdown_sections(md_path, split_level=split_level)
    normalized_baseline_sections, unresolved_legacy_titles = _normalize_baseline_sections_by_title(
        sections,
        baseline_sections_by_title,
    )
    local_titles = [_section_identifier(section) for section in sections if _section_identifier(section)]
    baseline_titles = [str(title or "").strip() for title in normalized_baseline_sections.keys() if str(title or "").strip()]
    if _deleted_heading_titles(local_titles, baseline_titles):
        return [_FULL_PAGE_AUTO_SENTINEL]
    changed_titles: List[str] = []

    for section in sections:
        title = _section_identifier(section)
        if not title:
            continue
        baseline_markdown = normalized_baseline_sections.get(title)
        if baseline_markdown is None and str(section.get("title") or "").strip() in unresolved_legacy_titles:
            continue
        if baseline_markdown is None:
            changed_titles.append(title)
            continue

        baseline_normalized = _normalize_section_body_for_autodetect(str(baseline_markdown), is_html=False)
        local_normalized = _normalize_section_body_for_autodetect(str(section.get("markdown") or ""), is_html=False)
        if baseline_normalized != local_normalized:
            changed_titles.append(title)

    return changed_titles


def _normalize_baseline_sections_by_title(
    sections: List[Dict[str, Any]],
    baseline_sections_by_title: Dict[str, str],
) -> Tuple[Dict[str, str], set]:
    normalized: Dict[str, str] = {}
    unresolved_legacy_titles: set = set()
    if not baseline_sections_by_title:
        return normalized, unresolved_legacy_titles

    local_by_identifier = {
        _section_identifier(section): section
        for section in sections
        if _section_identifier(section)
    }
    local_by_leaf_title: Dict[str, List[Dict[str, Any]]] = {}
    has_path_qualified_local_titles = any(_HEADING_PATH_SEPARATOR in identifier for identifier in local_by_identifier)
    for section in sections:
        leaf_title = str(section.get("title") or "").strip()
        if not leaf_title:
            continue
        local_by_leaf_title.setdefault(leaf_title, []).append(section)

    for raw_title, raw_markdown in baseline_sections_by_title.items():
        baseline_title = str(raw_title or "").strip()
        if not baseline_title:
            continue
        baseline_markdown = str(raw_markdown or "")

        if baseline_title in local_by_identifier:
            normalized[baseline_title] = baseline_markdown
            continue

        matches = list(local_by_leaf_title.get(baseline_title, []))
        if len(matches) == 1:
            normalized[_section_identifier(matches[0])] = baseline_markdown
            continue

        if len(matches) > 1 and has_path_qualified_local_titles:
            baseline_normalized = _normalize_section_body_for_autodetect(baseline_markdown, is_html=False)
            exact_matches = [
                section
                for section in matches
                if _normalize_section_body_for_autodetect(str(section.get("markdown") or ""), is_html=False)
                == baseline_normalized
            ]
            if len(exact_matches) == 1:
                normalized[_section_identifier(exact_matches[0])] = baseline_markdown
                continue
            unresolved_legacy_titles.add(baseline_title)
            continue

        normalized[baseline_title] = baseline_markdown

    return normalized, unresolved_legacy_titles


def _parse_markdown_sections_from_text(markdown_text: str, split_level: int = 1) -> List[Dict[str, Any]]:
    lines = [raw_line.rstrip("\r") for raw_line in (markdown_text or "").replace("\r\n", "\n").split("\n")]
    return _parse_markdown_sections_from_lines(lines, split_level=split_level, default_title="Document")


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

    saved_md_path = os.path.abspath(str(payload.get("md_path") or "")).lower()
    requested_md_path = os.path.abspath(md_path).lower()
    if saved_md_path != requested_md_path:
        try:
            requested_sections = _parse_markdown_sections(md_path, split_level=split_level)
            requested_titles = [
                _section_identifier(section)
                for section in requested_sections
                if _section_identifier(section)
            ]
        except Exception:
            return None

        saved_headings = payload.get("headings") or {}
        if not isinstance(saved_headings, dict):
            return None
        saved_titles = [str(title or "").strip() for title in saved_headings.keys() if str(title or "").strip()]
        if requested_titles != saved_titles:
            normalized_saved_headings, unresolved_legacy_titles = _normalize_baseline_sections_by_title(
                requested_sections,
                {str(title or "").strip(): str(markdown or "") for title, markdown in saved_headings.items()},
            )
            normalized_saved_titles = [str(title or "").strip() for title in normalized_saved_headings.keys() if str(title or "").strip()]
            if requested_titles != normalized_saved_titles and not unresolved_legacy_titles:
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
        title = _section_identifier(section)
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
    local_titles = [_section_identifier(section) for section in sections if _section_identifier(section)]
    live_titles = _extract_storage_heading_titles(storage_html, split_level)
    if _deleted_heading_titles(local_titles, live_titles):
        return [_FULL_PAGE_AUTO_SENTINEL]
    changed_titles: List[str] = []

    for section in sections:
        title = _section_identifier(section)
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


def _select_auto_heading_target(changed_titles: List[str], allow_full_page_fallback: bool) -> str:
    if not changed_titles:
        raise SystemExit(
            "Unable to auto-resolve a changed heading because no split-level section differs from the current page. "
            "Pass --heading-title explicitly."
        )

    requires_full_page = _FULL_PAGE_AUTO_SENTINEL in changed_titles or len(changed_titles) > 1
    if not requires_full_page:
        return changed_titles[0]

    if allow_full_page_fallback:
        return _FULL_PAGE_AUTO_SENTINEL

    if _FULL_PAGE_AUTO_SENTINEL in changed_titles:
        raise SystemExit(
            "Auto heading resolution detected deleted or renamed headings that require a full-page overwrite. "
            "Blocked by default to avoid overwriting non-Markdown page content. "
            "Pass --heading-title explicitly or rerun with --allow-full-page-fallback."
        )

    raise SystemExit(
        "Auto heading resolution found multiple changed split-level sections. "
        "Blocked by default to avoid a full-page overwrite. "
        f"Changed headings: {changed_titles}. Pass --heading-title explicitly or rerun with --allow-full-page-fallback."
    )


def _select_auto_publish_target(
    changed_titles: List[str],
    allow_full_page_fallback: bool,
    anchor_region_available: bool,
) -> str:
    concrete_titles = [title for title in changed_titles if str(title or "").strip() and title != _FULL_PAGE_AUTO_SENTINEL]
    if anchor_region_available:
        return _ANCHOR_REGION_AUTO_SENTINEL
    if _FULL_PAGE_AUTO_SENTINEL in changed_titles:
        raise SystemExit(
            "Auto heading resolution requires managed anchor-region mode for this document, "
            "but the start/end anchors were not found on the live page. "
            "Publish is blocked to avoid full-page overwrite."
        )
    if len(concrete_titles) == 1:
        return concrete_titles[0]
    # Treat multi-section updates as one integrated document publish.
    # This ensures intro + other heading changes are applied together.
    if len(concrete_titles) > 1:
        return _select_auto_heading_target(changed_titles, allow_full_page_fallback)
    return _select_auto_heading_target(changed_titles, allow_full_page_fallback)


def _display_heading_target(heading_title: str) -> str:
    if str(heading_title or "") == _FULL_PAGE_AUTO_SENTINEL:
        return "FULL_PAGE_AUTO"
    if str(heading_title or "") == _ANCHOR_REGION_AUTO_SENTINEL:
        return "ANCHOR_REGION_AUTO"
    return str(heading_title or "")


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
        "--anchor-start-name",
        str(args.anchor_start_name),
        "--anchor-end-name",
        str(args.anchor_end_name),
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
        ("--require-visible-inline-markers", args.require_visible_inline_markers),
        ("--allow-reanchor-conflict-retry", args.allow_reanchor_conflict_retry),
        ("--require-low-risk-reanchor", args.require_low_risk_reanchor),
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


def _find_visible_phrase_spans(text: str, phrase: str) -> List[Tuple[int, int]]:
    if not text or not phrase:
        return []

    normalized_phrase = " ".join(str(phrase or "").split()).strip().lower()
    if not normalized_phrase:
        return []

    projected_chars: List[str] = []
    projected_raw_indices: List[int] = []
    in_tag = False
    previous_was_space = True

    for raw_index, ch in enumerate(text):
        if in_tag:
            if ch == ">":
                in_tag = False
            continue
        if ch == "<":
            in_tag = True
            continue

        if ch.isspace():
            if not previous_was_space:
                projected_chars.append(" ")
                projected_raw_indices.append(raw_index)
                previous_was_space = True
            continue

        projected_chars.append(ch)
        projected_raw_indices.append(raw_index)
        previous_was_space = False

    projected_text = "".join(projected_chars)
    projected_lower = projected_text.lower()
    positions: List[Tuple[int, int]] = []
    cursor = projected_lower.find(normalized_phrase)
    while cursor != -1:
        end_cursor = cursor + len(normalized_phrase) - 1
        if 0 <= cursor < len(projected_raw_indices) and 0 <= end_cursor < len(projected_raw_indices):
            raw_start = projected_raw_indices[cursor]
            raw_end = projected_raw_indices[end_cursor] + 1
            positions.append((raw_start, raw_end))
        cursor = projected_lower.find(normalized_phrase, cursor + 1)
    return positions


def _pick_visible_phrase_span(
    text: str,
    phrase: str,
    preferred_index: Optional[int] = None,
) -> Optional[Tuple[int, int]]:
    spans = _find_visible_phrase_spans(text, phrase)
    if not spans:
        return None
    if preferred_index is None or len(spans) == 1:
        return spans[0]
    return min(spans, key=lambda span: abs(span[0] - preferred_index))


_INLINE_WRAPPABLE_TAGS = {"a", "b", "code", "em", "i", "span", "strong", "sub", "sup", "u"}


def _expand_span_to_enclosing_inline_tags(text: str, start: int, end: int) -> Tuple[int, int]:
    expanded_start = start
    expanded_end = end

    while expanded_start > 0:
        left_text = text[:expanded_start]
        open_match = re.search(r'<([a-zA-Z][\w:-]*)\b[^>]*>\s*$', left_text)
        if not open_match:
            break
        tag_name = open_match.group(1).lower()
        if tag_name not in _INLINE_WRAPPABLE_TAGS:
            break
        expanded_start = open_match.start()

    while expanded_end < len(text):
        close_match = re.match(r'\s*</([a-zA-Z][\w:-]*)\s*>', text[expanded_end:])
        if not close_match:
            break
        tag_name = close_match.group(1).lower()
        if tag_name not in _INLINE_WRAPPABLE_TAGS:
            break
        expanded_end += close_match.end()

    return expanded_start, expanded_end


def _score_visible_span_context(
    text: str,
    start: int,
    end: int,
    left_context: str,
    right_context: str,
) -> int:
    plain_left = _html_to_plain_text(left_context or "")
    plain_right = _html_to_plain_text(right_context or "")
    plain_before = _html_to_plain_text(text[:start])
    plain_after = _html_to_plain_text(text[end:])
    return _common_suffix_len(plain_left, plain_before) + _common_prefix_len(plain_right, plain_after)


def _has_meaningful_plain_context_overlap(context: str, surrounding: str, from_left: bool) -> bool:
    plain_context = _html_to_plain_text(context or "").strip().lower()
    plain_surrounding = _html_to_plain_text(surrounding or "").strip().lower()
    if not plain_context or not plain_surrounding:
        return False

    words = [word for word in re.split(r"\s+", plain_context) if word]
    if len(words) >= 2:
        phrase = " ".join(words[-2:] if from_left else words[:2])
        if phrase and phrase in plain_surrounding:
            return True
    if words:
        token = words[-1] if from_left else words[0]
        if len(token) >= 4 and token in plain_surrounding:
            return True
    return False


def _strip_inline_marker_tags(text: str) -> str:
    return re.sub(r"</?ac:inline-comment-marker\b[^>]*>", "", str(text or ""), flags=re.IGNORECASE)


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


def _try_partial_anchor_match(text: str, anchor: str, preferred_index: Optional[int] = None) -> Optional[int]:
    """Try to find anchor using partial text when full anchor text is lost.
    Strategy: Try progressively shorter prefixes (first 50%, then 25%, then 10% of anchor).
    Only returns match if context score would be acceptable.
    CONSERVATIVE: Don't use if we already have heading path - let existing logic handle it."""
    if not anchor or len(anchor) < 8:  # Only try for reasonably sized anchors
        return None
    
    # Try progressively smaller prefixes
    for prefix_ratio in [0.6, 0.4, 0.25]:  # Higher thresholds - be more conservative
        prefix_len = max(8, int(len(anchor) * prefix_ratio))  # Longer minimum prefix
        partial = anchor[:prefix_len]
        
        # Try exact match first in HTML
        plain_partial = _html_to_plain_text(partial).strip()
        if len(plain_partial) < 5:  # Skip very short fragments
            continue
        
        positions = _find_all_occurrences(text, partial)
        if positions:
            # If multiple positions, only use if preferred_index is very close to one
            if len(positions) == 1:
                return positions[0]
            elif preferred_index and len(positions) > 1:
                best = min(positions, key=lambda p: abs(p - preferred_index))
                if abs(best - preferred_index) < 500:  # Only if close enough
                    return best
    
    return None


def _recover_by_heading_context(
    text: str,
    heading_path: Optional[List[Dict[str, Any]]],
    preferred_index: Optional[int],
    section_start: int,
) -> Optional[int]:
    """Try to recover comment position by heading hierarchy when anchor text is lost.
    Uses the heading path to find the correct section, then returns position at section start."""
    if not heading_path or len(heading_path) == 0:
        return None
    
    # Use the deepest heading in path to locate the section
    target_heading = heading_path[-1]
    heading_text = target_heading.get('text', '').strip()
    
    if not heading_text or len(heading_text) < 2:
        return None
    
    # Search for matching heading in text
    heading_pattern = re.escape(heading_text[:20])  # Use first 20 chars to find heading
    matches = re.finditer(heading_pattern, text, re.IGNORECASE)
    
    for match in matches:
        # Found a heading match - position comment after it
        pos = match.end()
        # Move forward to end of heading tag
        close_tag_match = re.search(r'</h[1-6]>', text[pos:], re.IGNORECASE)
        if close_tag_match:
            return pos + close_tag_match.end()
        return pos
    
    return None


def _lock_position_by_section_offset(
    text: str,
    original_offset: int,
    section_start: int,
    preferred_index: Optional[int],
    anchor_text_found: bool,
) -> Optional[int]:
    """Pin comment to section + relative offset when anchor text cannot be matched exactly.
    If anchor was found but context weak, use offset-based positioning as fallback."""
    if preferred_index is None or not anchor_text_found:
        return None
    
    # Calculate relative offset within section
    relative_offset = preferred_index - section_start
    if relative_offset < 0:
        return None
    
    # Try to find position at relative offset in new section
    search_area = text[section_start:] if section_start < len(text) else ""
    if len(search_area) > relative_offset:
        # Find nearest paragraph or content boundary
        search_start = section_start + min(relative_offset, len(search_area) - 1)
        
        # Look for paragraph tag near this position
        before = text[:search_start]
        after = text[search_start:]
        
        # Try to find opening para/div/li tag after the position
        para_match = re.search(r'[</>]', after[:200])
        if para_match:
            return search_start + para_match.start()
        
        return search_start
    
    return None


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
        
        # For a unique occurrence, check if the original left_context can be found
        # in the new storage near the occurrence. If not, it indicates the context
        # has changed (e.g., surrounding rows/blocks were deleted).
        before_occurrence = text[:occurrences[0]]
        if left_context:
            normalized_left_context = _strip_inline_marker_tags(left_context)
            normalized_before_occurrence = _strip_inline_marker_tags(before_occurrence)
            if normalized_left_context not in normalized_before_occurrence:
                # Avoid fragile exact-context checks: injected marker tags and
                # nearby edits can slightly shift context while the anchor is
                # still on the same semantic row/item.
                plain_left = _html_to_plain_text(normalized_left_context)
                plain_before = _html_to_plain_text(normalized_before_occurrence)
                left_words = [word for word in re.split(r"\s+", plain_left.strip()) if word]
                if len(left_words) >= 2:
                    trailing_phrase = " ".join(left_words[-2:]).lower()
                    if trailing_phrase and trailing_phrase not in plain_before.lower():
                        return None
                elif left_words:
                    token = left_words[-1].lower()
                    if len(token) >= 3 and token not in plain_before.lower():
                        return None
        
        # Context seems to match - use the unique occurrence if score is good
        if best_score >= _MIN_CONTEXT_SCORE:
            return best_index
        
        # Weak score but unique - need reasonable distance
        max_dist = max(len(anchor), 30)
        if abs(best_index - preferred_index) <= max_dist:
            return best_index
        return None

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
    original_anchor: Optional[str] = None,
) -> Optional[Tuple[int, int]]:
    """Pick a safe anchor span using surrounding context when anchor text changed.
    Falls back to finding partial anchor matches if context-based approach fails."""
    def _recover_from_original_phrase(
        search_start: int = 0,
        search_end: Optional[int] = None,
    ) -> Optional[Tuple[int, int]]:
        anchor_text = str(original_anchor or "").strip()
        if not anchor_text:
            return None

        limit = len(text) if search_end is None else max(search_start, min(search_end, len(text)))
        haystack = text[search_start:limit]
        haystack_lower = haystack.lower()
        if not haystack:
            return None

        phrases: List[str] = []
        seen = set()

        def _add_phrase(value: str) -> None:
            cleaned = str(value or "").strip()
            key = cleaned.lower()
            if cleaned and key not in seen:
                seen.add(key)
                phrases.append(cleaned)

        _add_phrase(anchor_text)
        _add_phrase(anchor_text.rstrip('.,;:!?'))
        words = [token for token in anchor_text.rstrip('.,;:!?').split() if token]
        for prefix_len in range(min(len(words), 4), 1, -1):
            _add_phrase(" ".join(words[:prefix_len]))

        for phrase in phrases:
            phrase_lower = phrase.lower()
            positions: List[int] = []
            offset = haystack_lower.find(phrase_lower)
            while offset != -1:
                positions.append(search_start + offset)
                offset = haystack_lower.find(phrase_lower, offset + 1)
            if not positions:
                continue
            if len(positions) > 1:
                if preferred_index is None:
                    continue
                positions.sort(key=lambda pos: abs(pos - preferred_index))
            phrase_start = positions[0]
            phrase_end = phrase_start + len(phrase)
            while phrase_end < limit and text[phrase_end] not in "<>\n":
                phrase_end += 1
                if text[phrase_end - 1] in ".!?;":
                    break
            normalized = _normalize_fallback_span(text, (phrase_start, phrase_end))
            if normalized[1] <= normalized[0]:
                continue
            candidate_text = text[normalized[0]:normalized[1]].strip()
            if len(candidate_text) >= max(_MIN_CONTEXT_FRAGMENT, len(anchor_text) // 3):
                return normalized
        return None

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

    # When exact anchor is deleted but context is available, be more lenient.
    # Require either: strong context on one side (>= MIN_CONTEXT_FRAGMENT),
    # or weak-but-present context on both sides (score >= 4).
    has_strong = max(left_len, right_len) >= _MIN_CONTEXT_FRAGMENT
    has_weak_both = left_len >= 2 and right_len >= 2
    
    # If context is too weak, try matching the original anchor before giving up.
    if not (has_strong or has_weak_both) and original_anchor:
        recovered = _recover_from_original_phrase()
        if recovered is not None:
            return recovered
    
    if not (has_strong or has_weak_both):
        if score == 0:
            return None

    start = left_pos + left_len if left_pos is not None else right_pos
    if start is None:
        return None
    end = right_pos if right_pos is not None else start
    if end < start:
        end = start

    if end <= start:
        if original_anchor and " " in str(original_anchor or ""):
            run_start = start
            while run_start > 0 and text[run_start - 1] not in "<>\n":
                run_start -= 1
            run_end = start
            while run_end < len(text) and text[run_end] not in "<>\n":
                run_end += 1
            recovered = _recover_from_original_phrase(run_start, run_end)
            if recovered is not None:
                return recovered
        if (
            original_anchor
            and " " in str(original_anchor or "")
            and start > 0
            and text[start - 1] not in ">"
        ):
            expanded_end = start
            while expanded_end < len(text) and text[expanded_end] not in "<>\n":
                expanded_end += 1
                if text[expanded_end - 1] in ".!?;":
                    break
            normalized = _normalize_fallback_span(text, (start, expanded_end))
            if normalized[1] > normalized[0]:
                candidate_text = text[normalized[0]:normalized[1]].strip()
                minimum_len = max(_MIN_CONTEXT_FRAGMENT, len(str(original_anchor).strip()) // 3)
                if len(candidate_text) >= minimum_len:
                    return normalized
        token_span = _pick_nearest_text_token_span(text, start)
        return token_span
    
    # Expand span to capture full text token, not just between markers.
    expanded_start = start
    while expanded_start > 0 and text[expanded_start - 1] not in '<> \n\t':
        expanded_start -= 1
    expanded_end = end
    while expanded_end < len(text) and text[expanded_end] not in '<> \n\t':
        expanded_end += 1
    
    # Try the expanded span first, then fall back to original
    normalized = _normalize_fallback_span(text, (expanded_start, expanded_end))
    if normalized[1] <= normalized[0]:
        # Fallback to original span if expansion didn't work
        normalized = _normalize_fallback_span(text, (start, end))
    if normalized[1] <= normalized[0]:
        return None
    if original_anchor and " " in str(original_anchor or ""):
        candidate_text = text[normalized[0]:normalized[1]].strip()
        if len(candidate_text) < max(_MIN_CONTEXT_FRAGMENT, len(str(original_anchor).strip()) // 2):
            run_start = normalized[0]
            while run_start > 0 and text[run_start - 1] not in "<>\n":
                run_start -= 1
            run_end = normalized[1]
            while run_end < len(text) and text[run_end] not in "<>\n":
                run_end += 1
            recovered = _recover_from_original_phrase(run_start, run_end)
            if recovered is not None:
                return recovered
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
    if _is_index_inside_tag(text, start) or _is_index_inside_tag(text, end):
        return False
    candidate = text[start:end]
    if "<" in candidate or ">" in candidate:
        plain_candidate = _html_to_plain_text(candidate).strip()
        return _is_safe_anchor_text(plain_candidate)
    return _is_safe_anchor_text(candidate)


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


def _format_heading_path_for_display(
    heading_path: Optional[List[Dict[str, Any]]],
    fallback_heading_title: str = "",
) -> str:
    parts: List[str] = []
    for item in heading_path or []:
        text = _html_to_plain_text(str((item or {}).get("text") or "")).strip()
        if text and (not parts or parts[-1] != text):
            parts.append(text)

    if not parts and fallback_heading_title:
        for raw_part in _split_heading_path(fallback_heading_title):
            text = _html_to_plain_text(str(raw_part or "")).strip()
            if text and (not parts or parts[-1] != text):
                parts.append(text)

    return _ORPHAN_CONTEXT_DISPLAY_SEPARATOR.join(parts)


def _build_orphan_context_reply_storage(heading_path_text: str, anchor_preview: str = "") -> str:
    escaped_heading_path = html.escape(str(heading_path_text or "").strip())
    escaped_anchor_preview = html.escape(str(anchor_preview or "").strip())
    body_parts = [
        "<p><strong>Original location:</strong> " + escaped_heading_path + "</p>",
    ]
    if escaped_anchor_preview:
        body_parts.append("<p><strong>Original commented text:</strong> " + escaped_anchor_preview + "</p>")
    body_parts.append(
        "<p><em>This comment was preserved as an orphan because the original page content changed or was removed.</em></p>"
    )
    return "".join(body_parts)


def _build_orphan_context_targets(
    storage_anchor_audit: Dict[str, Any],
    inline_props: List[Dict[str, str]],
    markers: List[Dict[str, Any]],
    fallback_heading_title: str,
) -> List[Dict[str, str]]:
    props_by_ref = {
        str(item.get("ref") or ""): item
        for item in inline_props
        if str(item.get("ref") or "") and str(item.get("comment_id") or "")
    }
    markers_by_ref = {
        str(marker.get("ref") or ""): marker
        for marker in markers
        if str(marker.get("ref") or "")
    }

    targets: List[Dict[str, str]] = []
    seen_comment_ids: set = set()
    for detail in storage_anchor_audit.get("details", []):
        ref = str(detail.get("ref") or "")
        if not ref:
            continue
        if not bool(detail.get("visible_after_publish")):
            continue
        if str(detail.get("after_anchor_text_preview") or "").strip():
            continue

        inline_prop = props_by_ref.get(ref) or {}
        comment_id = str(inline_prop.get("comment_id") or "").strip()
        if not comment_id or comment_id in seen_comment_ids:
            continue

        marker = markers_by_ref.get(ref) or {}
        heading_path_text = _format_heading_path_for_display(
            marker.get("heading_path") or [],
            fallback_heading_title=fallback_heading_title,
        )
        if not heading_path_text:
            continue

        anchor_preview = _preview_text(
            str(marker.get("inline_anchor_html") or marker.get("anchor_html") or inline_prop.get("anchor_html") or ""),
            limit=120,
        )
        targets.append(
            {
                "comment_id": comment_id,
                "ref": ref,
                "heading_path_text": heading_path_text,
                "anchor_preview": anchor_preview,
                "reply_storage": _build_orphan_context_reply_storage(heading_path_text, anchor_preview),
            }
        )
        seen_comment_ids.add(comment_id)

    return targets


def _fetch_comment_replies(
    base_url: str,
    comment_id: str,
    auth: Optional[Tuple[str, str]],
    headers: Dict[str, str],
) -> List[Dict[str, Any]]:
    url = f"{base_url.rstrip('/')}/rest/api/content/{comment_id}/child/comment"
    resp = requests.get(
        url,
        params={"expand": "body.storage", "depth": "all"},
        auth=auth,
        headers=headers,
        timeout=60,
    )
    # Some Confluence instances reject or error on nested reply listing endpoints.
    # Fail open here so duplicate-check does not block reply posting.
    if resp.status_code < 200 or resp.status_code >= 300:
        return []
    resp.raise_for_status()
    payload = resp.json() or {}
    return payload.get("results") or []


def _reply_already_contains_orphan_context(existing_replies: List[Dict[str, Any]], reply_storage: str) -> bool:
    wanted_plain = _html_to_plain_text(reply_storage)
    if not wanted_plain:
        return False

    for reply in existing_replies:
        reply_storage_html = (((reply.get("body") or {}).get("storage") or {}).get("value") or "")
        reply_plain = _html_to_plain_text(reply_storage_html)
        if reply_plain == wanted_plain:
            return True
    return False


def _post_comment_reply(
    base_url: str,
    comment_id: str,
    reply_storage: str,
    auth: Optional[Tuple[str, str]],
    headers: Dict[str, str],
) -> Dict[str, Any]:
    post_headers = {k: v for k, v in headers.items()}
    post_headers["Content-Type"] = "application/json"
    payload = {
        "type": "comment",
        "container": {"id": str(comment_id), "type": "comment"},
        "body": {"storage": {"value": reply_storage, "representation": "storage"}},
    }
    attempts = [
        (
            f"{base_url.rstrip('/')}/rest/api/content",
            payload,
        ),
        (
            f"{base_url.rstrip('/')}/rest/api/content/{comment_id}/child/comment",
            {"type": "comment", "body": {"storage": {"value": reply_storage, "representation": "storage"}}},
        ),
    ]

    last_result: Dict[str, Any] = {"ok": False, "status": "not-attempted"}
    for url, body in attempts:
        resp = requests.post(url, json=body, auth=auth, headers=post_headers, timeout=60)
        if resp.status_code in (200, 201):
            return {"ok": True, "status": "ok", "http_status": int(resp.status_code), "url": url}
        last_result = {
            "ok": False,
            "status": "http-error",
            "http_status": int(resp.status_code),
            "url": url,
            "response_preview": str(resp.text or "")[:500],
        }
    return last_result


def _post_orphan_context_replies(
    args: argparse.Namespace,
    config_module: Any,
    targets: List[Dict[str, str]],
) -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "enabled": bool(getattr(args, "orphan_context_reply", False)),
        "candidate_count": len(targets),
        "posted_count": 0,
        "skipped_existing_count": 0,
        "failed_count": 0,
        "details": [],
    }
    if not getattr(args, "orphan_context_reply", False):
        summary["status"] = "disabled"
        return summary
    if not args.apply:
        summary["status"] = "skipped-no-apply"
        return summary
    if not targets:
        summary["status"] = "no-orphan-targets"
        return summary
    
    # Note: This feature requires Confluence authentication with permission to create child comments.
    # If using Bearer token auth, the service may not allow child comment creation (Confluence permission model).
    # Some Confluence instances require Basic Auth with a service account for this feature to work.
    # If all replies fail with 401, this is likely a permission/auth scope issue, not a code bug.

    last_error: Optional[str] = None
    for auth, headers, auth_name in _auth_strategies(args, config_module):
        try:
            posted_count = 0
            skipped_existing_count = 0
            failed_count = 0
            details: List[Dict[str, Any]] = []
            for target in targets:
                comment_id = str(target.get("comment_id") or "")
                reply_storage = str(target.get("reply_storage") or "")
                if not comment_id or not reply_storage:
                    continue

                existing_replies = _fetch_comment_replies(args.base_url, comment_id, auth, headers)
                if _reply_already_contains_orphan_context(existing_replies, reply_storage):
                    skipped_existing_count += 1
                    details.append(
                        {
                            "comment_id": comment_id,
                            "ref": str(target.get("ref") or ""),
                            "status": "already-present",
                            "heading_path_text": str(target.get("heading_path_text") or ""),
                        }
                    )
                    continue

                post_result = _post_comment_reply(args.base_url, comment_id, reply_storage, auth, headers)
                if bool(post_result.get("ok")):
                    posted_count += 1
                    details.append(
                        {
                            "comment_id": comment_id,
                            "ref": str(target.get("ref") or ""),
                            "status": "posted",
                            "heading_path_text": str(target.get("heading_path_text") or ""),
                        }
                    )
                else:
                    failed_count += 1
                    details.append(
                        {
                            "comment_id": comment_id,
                            "ref": str(target.get("ref") or ""),
                            "status": "failed",
                            "heading_path_text": str(target.get("heading_path_text") or ""),
                            "error": str(post_result.get("response_preview") or post_result.get("status") or ""),
                        }
                    )

            summary.update(
                {
                    "status": "ok",
                    "auth_method": auth_name,
                    "posted_count": posted_count,
                    "skipped_existing_count": skipped_existing_count,
                    "failed_count": failed_count,
                    "details": details,
                }
            )
            return summary
        except Exception as exc:
            last_error = str(exc)

    summary["status"] = "error"
    summary["error"] = last_error or "unknown error"
    summary["failed_count"] = len(targets)
    return summary


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


def _has_deleted_heading_context(text: str, left_context: str) -> bool:
    context = str(left_context or "")
    if not context:
        return False

    matches = list(re.finditer(r"<(h[1-6])\b[^>]*>(.*?)</\1>", context, re.IGNORECASE | re.DOTALL))
    if not matches:
        return False

    deleted_heading_text = _html_to_plain_text(matches[-1].group(2)).strip().lower()
    if not deleted_heading_text:
        return False

    for candidate in _iter_heading_candidates(text):
        current_text = str(candidate.get("normalized_text") or "").strip().lower()
        if current_text == deleted_heading_text:
            return False
    return True


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
        candidate_info = _pick_heading_candidate_from_path(text, heading_path)
        if candidate_info is not None:
            best_candidate, _best_depth, _target_depth, _match_kind = candidate_info
            return int(best_candidate["end"])

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


def _pick_heading_span_by_level(
    text: str,
    target_level: int,
    preferred_index: Optional[int],
) -> Optional[Tuple[int, int]]:
    candidates = [candidate for candidate in _iter_heading_candidates(text) if int(candidate["level"]) == int(target_level)]
    if not candidates:
        return None
    if preferred_index is None:
        chosen = candidates[0]
    else:
        chosen = min(candidates, key=lambda candidate: abs(int(candidate["start"]) - preferred_index))
    return (int(chosen["content_start"]), int(chosen["content_end"]))


def _pick_heading_branch_span_by_level(
    text: str,
    target_level: int,
    preferred_index: Optional[int],
) -> Optional[Tuple[int, int]]:
    candidates = [candidate for candidate in _iter_heading_candidates(text) if int(candidate["level"]) == int(target_level)]
    if not candidates:
        return None
    if preferred_index is None:
        chosen_index = 0
    else:
        chosen_index = min(
            range(len(candidates)),
            key=lambda index: abs(int(candidates[index]["start"]) - preferred_index),
        )
    chosen = candidates[chosen_index]
    branch_end = len(text)
    for candidate in candidates[chosen_index + 1:]:
        if int(candidate["start"]) > int(chosen["start"]):
            branch_end = int(candidate["start"])
            break
    return (int(chosen["end"]), branch_end)


def _iter_heading_branch_spans_by_level(text: str, target_level: int) -> List[Tuple[int, int]]:
    candidates = [candidate for candidate in _iter_heading_candidates(text) if int(candidate["level"]) == int(target_level)]
    branch_spans: List[Tuple[int, int]] = []
    for index, candidate in enumerate(candidates):
        branch_end = len(text)
        for later_candidate in candidates[index + 1:]:
            if int(later_candidate["start"]) > int(candidate["start"]):
                branch_end = int(later_candidate["start"])
                break
        branch_spans.append((int(candidate["end"]), branch_end))
    return branch_spans


def _pick_heading_span_from_path(
    text: str,
    heading_path: List[Dict[str, Any]],
) -> Optional[Tuple[int, int]]:
    candidate_info = _pick_heading_candidate_from_path(text, heading_path)
    if candidate_info is None:
        return None
    best_candidate, _best_depth, _target_depth, _match_kind = candidate_info
    return (int(best_candidate["content_start"]), int(best_candidate["content_end"]))


def _context_indicates_heading_anchor(left_context: str, right_context: str) -> bool:
    left = str(left_context or "")
    right = str(right_context or "")
    if not left or not right:
        return False
    return bool(
        re.search(r"<h[1-6]\b[^>]*>[^<]*$", left, re.IGNORECASE | re.DOTALL)
        and re.search(r"^.*?</h[1-6]>", right, re.IGNORECASE | re.DOTALL)
    )


def _pick_renamed_descendant_heading_span_from_path(
    text: str,
    heading_path: List[Dict[str, Any]],
    preferred_index: Optional[int],
) -> Optional[Tuple[int, int]]:
    if len(heading_path) < 2:
        return None

    parent_info = _pick_heading_candidate_from_path(text, heading_path[:-1])
    if parent_info is None:
        return None

    parent_candidate, _best_depth, _target_depth, _match_kind = parent_info
    parent_level = int(parent_candidate["level"])
    target_level = int(heading_path[-1].get("level") or 0)
    if target_level <= parent_level:
        return None

    branch_end = len(text)
    descendants: List[Dict[str, Any]] = []
    parent_seen = False
    for candidate in _iter_heading_candidates(text):
        if int(candidate["start"]) == int(parent_candidate["start"]):
            parent_seen = True
            continue
        if not parent_seen:
            continue
        if int(candidate["level"]) <= parent_level:
            branch_end = int(candidate["start"])
            break
        if int(candidate["start"]) < branch_end:
            descendants.append(candidate)

    if not descendants:
        return None

    same_level = [candidate for candidate in descendants if int(candidate["level"]) == target_level]
    pool = same_level or descendants
    if preferred_index is None:
        chosen = pool[0]
    else:
        chosen = min(pool, key=lambda candidate: abs(int(candidate["start"]) - preferred_index))
    return (int(chosen["content_start"]), int(chosen["content_end"]))


def _pick_heading_candidate_from_path(
    text: str,
    heading_path: List[Dict[str, Any]],
) -> Optional[Tuple[Dict[str, Any], int, int, str]]:
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
    best_priority = -1
    best_match_kind = ""

    for candidate in _iter_heading_candidates(text):
        while current_path and int(current_path[-1]["level"]) >= int(candidate["level"]):
            current_path.pop()
        current_path.append(candidate)

        current_normalized = [str(item.get("normalized_text") or "") for item in current_path]
        matched_depth = 0
        matched_candidate: Optional[Dict[str, Any]] = None
        match_kind = ""
        match_priority = -1

        if current_normalized == target_path:
            matched_depth = len(target_path)
            matched_candidate = current_path[-1]
            match_kind = "exact"
            match_priority = 4
        elif len(current_normalized) <= len(target_path) and current_normalized == target_path[-len(current_normalized):]:
            matched_depth = len(current_normalized)
            matched_candidate = current_path[-1]
            match_kind = "leaf_suffix"
            match_priority = 3
        elif len(current_normalized) <= len(target_path) and current_normalized == target_path[:len(current_normalized)]:
            matched_depth = len(current_normalized)
            matched_candidate = current_path[-1]
            match_kind = "ancestor_prefix"
            match_priority = 2
        else:
            max_depth = min(len(current_normalized), len(target_path))
            for depth in range(1, max_depth + 1):
                if current_normalized[:depth] == target_path[:depth]:
                    matched_depth = depth
                else:
                    break
            if matched_depth > 0:
                matched_candidate = current_path[matched_depth - 1]
                match_kind = "prefix_partial"
                match_priority = 1

        if matched_candidate is None or matched_depth == 0:
            continue

        if (
            match_priority > best_priority
            or (match_priority == best_priority and matched_depth > best_depth)
        ):
            best_priority = match_priority
            best_depth = matched_depth
            best_candidate = matched_candidate
            best_match_kind = match_kind

    if best_candidate is None:
        return None
    return best_candidate, best_depth, len(target_path), best_match_kind


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


def _occurrence_matches_heading_path_fuzzy(
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
    if not actual or len(actual) != len(expected):
        return False
    if len(expected) == 1:
        return expected[0] == actual[0] or expected[0] in actual[0] or actual[0] in expected[0]
    if actual[:-1] != expected[:-1]:
        return False

    expected_leaf = expected[-1]
    actual_leaf = actual[-1]
    return (
        expected_leaf == actual_leaf
        or expected_leaf in actual_leaf
        or actual_leaf in expected_leaf
    )


def _normalize_anchor_for_matching(anchor: str) -> Tuple[str, bool]:
    raw_anchor = str(anchor or "")
    if "<ac:inline-comment-marker" in raw_anchor.lower():
        visible_anchor = _html_to_plain_text(raw_anchor).strip()
        if visible_anchor:
            return visible_anchor, True
    return raw_anchor, False


def _find_heading_by_text(text: str, heading_text: str, target_level: Optional[int] = None) -> Optional[Tuple[int, int]]:
    """Find a heading by its text content when heading_path is stale.
    
    This helps when large content shifts make original heading paths unreliable.
    Searches for a heading tag containing the target text.
    """
    if not text or not heading_text:
        return None
    
    heading_pattern = re.compile(
        r'<h([1-6])\b[^>]*>([^<]+)</h\1>', 
        re.IGNORECASE | re.DOTALL
    )
    
    normalized_target = str(heading_text or "").strip().lower()
    
    for match in heading_pattern.finditer(text):
        level_str = match.group(1)
        heading_content = match.group(2).strip()
        normalized_content = heading_content.lower()
        
        # If target_level specified, only match that level
        if target_level is not None and int(level_str) != target_level:
            continue
        
        # Allow partial match (e.g., "APIC Setup" matches "APIC Setup and Configuration")
        if normalized_target in normalized_content or normalized_content in normalized_target:
            return (match.start(), match.end())
    
    return None


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

    # Confluence can return already-orphaned copies (empty visible anchor) for active refs.
    # Remove only those empty-anchor copies first, then let normal reinjection logic run.
    refs_in_run = {str(m.get("ref") or "") for m in markers if str(m.get("ref") or "")}
    if refs_in_run:
        existing = _extract_inline_markers(result)
        if section_span is not None:
            sec_start, sec_end = section_span
            existing = [
                m for m in existing
                if int(m.get("start", -1)) >= sec_start and int(m.get("end", -1)) <= sec_end
            ]
        orphan_refs_to_strip = {
            str(m.get("ref") or "")
            for m in existing
            if str(m.get("ref") or "") in refs_in_run
            and not _marker_visible_anchor_text(str(m.get("anchor_html") or ""))
        }
        if orphan_refs_to_strip:
            result, _ = _strip_inline_markers_by_ref(result, orphan_refs_to_strip, section_span=section_span)
    
    scope_start = 0
    scope_end = len(result)
    if section_span is not None:
        raw_start, raw_end = section_span
        scope_start = max(0, min(raw_start, len(result)))
        scope_end = max(scope_start, min(raw_end, len(result)))

    reanchored = 0
    skipped = 0
    deleted_anchor_icon_count = 0
    orphan_refs_to_batch: List[str] = []  # Collect all orphan refs for batch injection at end
    orphan_refs_with_deleted_icon: set = set()
    markers_by_ref: Dict[str, Dict[str, Any]] = {
        str(m.get("ref") or ""): m
        for m in markers
        if str(m.get("ref") or "")
    }
    old_scope_start = 0
    accumulated_injection_delta = 0
    if section_span is not None:
        old_scope_start = int(section_span[0])

    def _heading_path_key(path: Optional[List[Dict[str, Any]]]) -> Tuple[Tuple[int, str], ...]:
        if not path:
            return tuple()
        key_parts: List[Tuple[int, str]] = []
        for item in path:
            level = int(item.get("level") or 0)
            normalized_text = str(item.get("normalized_text") or item.get("text") or "").strip().lower()
            if level > 0 and normalized_text:
                key_parts.append((level, normalized_text))
        return tuple(key_parts)

    # Evidence that a missing top-level heading is a rename (not a delete):
    # we can still map a heading-anchor comment for the same heading path.
    initial_search_space = result[scope_start:scope_end]
    renamed_top_level_paths: set = set()
    for marker in markers:
        marker_heading_path = marker.get("heading_path") or []
        if not marker_heading_path or len(marker_heading_path) != 1:
            continue
        if int(marker_heading_path[-1].get("level") or 0) != 1:
            continue
        marker_left_context = str(marker.get("left_context") or "")
        marker_right_context = str(marker.get("right_context") or "")
        if not _context_indicates_heading_anchor(marker_left_context, marker_right_context):
            continue

        marker_old_start = int(marker.get("start", -1))
        marker_preferred_index: Optional[int] = None
        if marker_old_start >= 0:
            marker_preferred_index = max(0, marker_old_start - old_scope_start)

        candidate_span_rel = _pick_heading_span_by_level(
            initial_search_space,
            1,
            marker_preferred_index,
        )
        if candidate_span_rel is None:
            continue

        candidate_start_rel, candidate_end_rel = candidate_span_rel
        candidate_anchor = initial_search_space[candidate_start_rel:candidate_end_rel]
        candidate_context_score = _score_occurrence_context(
            initial_search_space,
            candidate_anchor,
            candidate_start_rel,
            marker_left_context,
            marker_right_context,
        )
        candidate_right_score = _common_prefix_len(
            marker_right_context,
            initial_search_space[candidate_end_rel:],
        )
        if candidate_context_score >= 16 and candidate_right_score >= _MIN_CONTEXT_FRAGMENT:
            renamed_top_level_paths.add(_heading_path_key(marker_heading_path))

    def _commit_injection(span_start_abs: int, span_end_abs: int, wrapped: str) -> None:
        nonlocal result, scope_end, reanchored, accumulated_injection_delta
        replaced_len = span_end_abs - span_start_abs
        result = result[:span_start_abs] + wrapped + result[span_end_abs:]
        delta = len(wrapped) - replaced_len
        scope_end += delta
        accumulated_injection_delta += delta
        reanchored += 1

    def _commit_top_orphan_marker(ref: str, count_deleted_icon: bool = True) -> None:
        # Collect orphan refs for batch injection at the end
        orphan_refs_to_batch.append(ref)
        if count_deleted_icon:
            orphan_refs_with_deleted_icon.add(ref)

    def _wrap_deleted_heading(
        ref: str,
        left_context: str,
        preferred_index: Optional[int],
        heading_path: Optional[List[Dict[str, Any]]],
    ) -> bool:
        if heading_path and _context_indicates_heading_anchor(left_context, right_context):
            renamed_heading_span_rel = _pick_renamed_descendant_heading_span_from_path(
                search_space,
                heading_path,
                preferred_index,
            )
            if renamed_heading_span_rel is not None:
                span_start_rel, span_end_rel = renamed_heading_span_rel
                span_start_abs = scope_start + span_start_rel
                span_end_abs = scope_start + span_end_rel
                fallback_anchor = search_space[span_start_rel:span_end_rel]
                wrapped = f'<ac:inline-comment-marker ac:ref="{ref}">{fallback_anchor}</ac:inline-comment-marker>'
                _commit_injection(span_start_abs, span_end_abs, wrapped)
                return True

        if heading_path:
            candidate_info = _pick_heading_candidate_from_path(search_space, heading_path)
            if candidate_info is None:
                target_level = int(heading_path[-1].get("level") or 0) if heading_path else 0
                has_next_same_level_in_old_context = bool(
                    re.search(rf"<h{target_level}\b", str(right_context or ""), re.IGNORECASE)
                ) if target_level > 0 else False
                if has_next_same_level_in_old_context and len(heading_path or []) >= 2:
                    parent_span_rel = _pick_heading_span_from_path(search_space, heading_path[:-1])
                    if parent_span_rel is not None:
                        parent_insert_abs = scope_start + int(parent_span_rel[1])
                        wrapped = f'<ac:inline-comment-marker ac:ref="{ref}">{_ORPHAN_COMMENT_EMPTY_ANCHOR_HTML}</ac:inline-comment-marker>'
                        _commit_injection(parent_insert_abs, parent_insert_abs, wrapped)
                        return True
                _commit_top_orphan_marker(ref)
                return True

            _best_candidate, best_depth, target_depth, match_kind = candidate_info
            should_use_nearest_surviving_heading = (
                match_kind == "leaf_suffix"
                or (match_kind == "ancestor_prefix" and best_depth >= 2 and best_depth == target_depth - 1)
            )
            if best_depth < target_depth and not should_use_nearest_surviving_heading:
                target_level = int(heading_path[-1].get("level") or 0) if heading_path else 0
                has_next_same_level_in_old_context = bool(
                    re.search(rf"<h{target_level}\b", str(right_context or ""), re.IGNORECASE)
                ) if target_level > 0 else False
                insert_rel = _pick_deleted_heading_insertion_point(
                    search_space,
                    left_context,
                    preferred_index,
                    heading_path=heading_path,
                )
                if insert_rel is None:
                    if has_next_same_level_in_old_context and len(heading_path or []) >= 2:
                        parent_span_rel = _pick_heading_span_from_path(search_space, heading_path[:-1])
                        if parent_span_rel is not None:
                            parent_insert_abs = scope_start + int(parent_span_rel[1])
                            wrapped = f'<ac:inline-comment-marker ac:ref="{ref}">{_ORPHAN_COMMENT_EMPTY_ANCHOR_HTML}</ac:inline-comment-marker>'
                            _commit_injection(parent_insert_abs, parent_insert_abs, wrapped)
                            return True
                    _commit_top_orphan_marker(ref)
                    return True
                if has_next_same_level_in_old_context:
                    insert_abs = scope_start + int(insert_rel)
                    wrapped = f'<ac:inline-comment-marker ac:ref="{ref}">{_ORPHAN_COMMENT_EMPTY_ANCHOR_HTML}</ac:inline-comment-marker>'
                    _commit_injection(insert_abs, insert_abs, wrapped)
                else:
                    _commit_top_orphan_marker(ref)
                return True

        heading_span_rel = _pick_deleted_heading_anchor_span(
            search_space,
            left_context,
            preferred_index,
            heading_path=heading_path,
        )
        if heading_span_rel is None:
            if heading_path:
                _commit_top_orphan_marker(ref)
                return True
            return False
        span_start_rel, span_end_rel = heading_span_rel
        span_start_abs = scope_start + span_start_rel
        span_end_abs = scope_start + span_end_rel
        fallback_anchor = search_space[span_start_rel:span_end_rel]
        if (
            heading_path
            and len(heading_path) == 1
            and int(heading_path[-1].get("level") or 0) == 1
            and not _context_indicates_heading_anchor(left_context, right_context)
        ):
            heading_fallback_score = _score_occurrence_context(
                search_space,
                fallback_anchor,
                span_start_rel,
                left_context,
                right_context,
            )
            if heading_fallback_score < 16:
                _commit_top_orphan_marker(ref)
                return True
        wrapped = f'<ac:inline-comment-marker ac:ref="{ref}">{fallback_anchor}</ac:inline-comment-marker>'
        # Check if this marker was originally an orphan (force_orphan flag)
        # If so, route to batch collection to keep all orphans consolidated
        marker_meta = markers_by_ref.get(ref, {})
        if marker_meta.get("force_orphan"):
            # Treat as orphan even if we found fallback text
            _commit_top_orphan_marker(ref)
        else:
            # Normal re-anchored marker with fallback text
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
        visible_anchor_text = _marker_visible_anchor_text(anchor)
        anchor, anchor_was_nested_marker = _normalize_anchor_for_matching(anchor)
        search_space = result[scope_start:scope_end]
        if not visible_anchor_text:
            # Recover from inlineProperties anchor text when the old marker was already orphaned.
            inline_anchor = str(m.get("inline_anchor_html") or "")
            inline_visible = _marker_visible_anchor_text(inline_anchor)
            if inline_visible and search_space:
                inline_occurrences = _find_all_occurrences(search_space, inline_anchor)
                selected_inline_index: Optional[int] = None
                if len(inline_occurrences) == 1:
                    selected_inline_index = inline_occurrences[0]
                elif inline_occurrences:
                    if heading_path:
                        branch_occurrences = [
                            idx for idx in inline_occurrences
                            if _occurrence_matches_heading_path_fuzzy(search_space, idx, heading_path)
                        ]
                        if len(branch_occurrences) == 1:
                            selected_inline_index = branch_occurrences[0]
                    if selected_inline_index is None and preferred_index is not None:
                        selected_inline_index = min(
                            inline_occurrences,
                            key=lambda idx: abs(idx - preferred_index),
                        )
                if selected_inline_index is not None and _is_safe_wrap_span(
                    search_space,
                    selected_inline_index,
                    selected_inline_index + len(inline_anchor),
                ):
                    inline_start_abs = scope_start + selected_inline_index
                    inline_end_abs = inline_start_abs + len(inline_anchor)
                    wrapped = f'<ac:inline-comment-marker ac:ref="{ref}">{inline_anchor}</ac:inline-comment-marker>'
                    _commit_injection(inline_start_abs, inline_end_abs, wrapped)
                    continue

            _commit_top_orphan_marker(ref)
            continue
        if not anchor or not anchor.strip():
            skipped += 1
            continue
        if not search_space:
            skipped += 1
            continue
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

        heading_path_missing = bool(heading_path) and _pick_heading_span_from_path(search_space, heading_path) is None
        if heading_path_missing:
            if len(heading_path) == 1:
                target_level = int(heading_path[-1].get("level") or 0)
                heading_anchor_context = _context_indicates_heading_anchor(left_context, right_context)
                if heading_anchor_context:
                    if target_level == 1 and _heading_path_key(heading_path) not in renamed_top_level_paths:
                        _commit_top_orphan_marker(ref, count_deleted_icon=False)
                        continue
                    renamed_heading_span_rel = _pick_heading_span_by_level(search_space, target_level, preferred_index)
                    if renamed_heading_span_rel is not None:
                        span_start_rel, span_end_rel = renamed_heading_span_rel
                        span_start_abs = scope_start + span_start_rel
                        span_end_abs = scope_start + span_end_rel
                        fallback_anchor = search_space[span_start_rel:span_end_rel]
                        heading_right_context_score = _common_prefix_len(
                            right_context,
                            search_space[span_end_rel:],
                        )
                        heading_context_score = _score_occurrence_context(
                            search_space,
                            fallback_anchor,
                            span_start_rel,
                            left_context,
                            right_context,
                        )
                        # Fail closed unless heading-side context has a meaningful match.
                        # Low scores tend to come only from generic tag boundaries and can
                        # incorrectly preserve deleted-heading comments on unrelated headings.
                        if (
                            heading_context_score >= 16
                            and heading_right_context_score >= _MIN_CONTEXT_FRAGMENT
                        ):
                            wrapped = f'<ac:inline-comment-marker ac:ref="{ref}">{fallback_anchor}</ac:inline-comment-marker>'
                            _commit_injection(span_start_abs, span_end_abs, wrapped)
                            continue
                if not heading_anchor_context:
                    has_next_same_level_heading_in_old_context = bool(
                        re.search(rf"<h{target_level}\b", str(right_context or ""), re.IGNORECASE)
                    )
                    allow_body_rebind_for_missing_h1 = True
                    if target_level == 1:
                        allow_body_rebind_for_missing_h1 = (
                            _heading_path_key(heading_path) in renamed_top_level_paths
                        )
                    branch_matches: List[Tuple[int, int, int, int, str]] = []
                    if not has_next_same_level_heading_in_old_context and allow_body_rebind_for_missing_h1:
                        for branch_start_rel, branch_end_rel in _iter_heading_branch_spans_by_level(search_space, target_level):
                            branch_search_space = search_space[branch_start_rel:branch_end_rel]
                            if not branch_search_space:
                                continue

                            branch_preferred_index = preferred_index
                            if branch_preferred_index is not None:
                                branch_preferred_index = max(0, min(branch_preferred_index - branch_start_rel, len(branch_search_space) - 1))

                            branch_anchor = anchor
                            branch_occurrences = _find_all_occurrences(branch_search_space, branch_anchor)
                            if not branch_occurrences:
                                stripped_anchor = anchor.strip()
                                if stripped_anchor and stripped_anchor != anchor:
                                    stripped_occurrences = _find_all_occurrences(branch_search_space, stripped_anchor)
                                    if stripped_occurrences:
                                        branch_occurrences = stripped_occurrences
                                        branch_anchor = stripped_anchor

                            if branch_occurrences:
                                branch_selected_index = _pick_best_occurrence_by_context(
                                    text=branch_search_space,
                                    anchor=branch_anchor,
                                    occurrences=branch_occurrences,
                                    left_context=left_context,
                                    right_context=right_context,
                                    preferred_index=branch_preferred_index,
                                )
                                if branch_selected_index is not None and _is_safe_wrap_span(
                                    branch_search_space,
                                    branch_selected_index,
                                    branch_selected_index + len(branch_anchor),
                                ):
                                    branch_score = _score_occurrence_context(
                                        branch_search_space,
                                        branch_anchor,
                                        branch_selected_index,
                                        left_context,
                                        right_context,
                                    )
                                    branch_matches.append((2, branch_score, branch_start_rel, branch_selected_index, branch_anchor))
                                    continue

                            branch_edited_span = _pick_edited_context_span(
                                branch_search_space,
                                left_context,
                                right_context,
                                preferred_index=branch_preferred_index,
                                original_anchor=anchor,
                            )
                            if branch_edited_span is not None:
                                branch_span_start_rel, branch_span_end_rel = branch_edited_span
                                if _is_safe_wrap_span(branch_search_space, branch_span_start_rel, branch_span_end_rel):
                                    edited_anchor = branch_search_space[branch_span_start_rel:branch_span_end_rel]
                                    branch_score = _score_occurrence_context(
                                        branch_search_space,
                                        edited_anchor,
                                        branch_span_start_rel,
                                        left_context,
                                        right_context,
                                    )
                                    if branch_score >= 16:
                                        branch_matches.append((1, branch_score, branch_start_rel, branch_span_start_rel, edited_anchor))

                    if len(branch_matches) == 1:
                        _match_kind, _match_score, branch_start_rel, branch_offset_rel, matched_anchor = branch_matches[0]
                        branch_selected_abs = scope_start + branch_start_rel + branch_offset_rel
                        wrapped = f'<ac:inline-comment-marker ac:ref="{ref}">{matched_anchor}</ac:inline-comment-marker>'
                        _commit_injection(branch_selected_abs, branch_selected_abs + len(matched_anchor), wrapped)
                        continue

                    # Before falling back to orphan, try to find the heading by its text
                    # This helps when heading_path is stale due to large content shifts
                    if heading_path and len(heading_path) > 0:
                        heading_text = heading_path[-1].get("text", "")
                        if heading_text:
                            found_heading = _find_heading_by_text(search_space, heading_text, target_level)
                            if found_heading is not None:
                                heading_start, heading_end = found_heading
                                heading_content = search_space[heading_start:heading_end]
                                wrapped = f'<ac:inline-comment-marker ac:ref="{ref}">{heading_content}</ac:inline-comment-marker>'
                                _commit_injection(scope_start + heading_start, scope_start + heading_end, wrapped)
                                continue
                    if target_level == 1:
                        _commit_top_orphan_marker(ref, count_deleted_icon=False)
                    else:
                        _commit_top_orphan_marker(ref, count_deleted_icon=False)
                    continue
                # Single-level heading but no matches found - try to find by heading text
                if heading_path and len(heading_path) > 0:
                    heading_text = heading_path[-1].get("text", "")
                    if heading_text:
                        found_heading = _find_heading_by_text(search_space, heading_text, target_level)
                        if found_heading is not None:
                            heading_start, heading_end = found_heading
                            heading_content = search_space[heading_start:heading_end]
                            wrapped = f'<ac:inline-comment-marker ac:ref="{ref}">{heading_content}</ac:inline-comment-marker>'
                            _commit_injection(scope_start + heading_start, scope_start + heading_end, wrapped)
                            continue

                if target_level == 1:
                    _commit_top_orphan_marker(ref, count_deleted_icon=False)
                else:
                    _commit_top_orphan_marker(ref)
                continue
            else:
                # For multi-level heading paths (nested headings), try to preserve
                # by finding the best matching heading in the path before marking as orphan
                if _wrap_deleted_heading(ref, left_context, preferred_index, heading_path):
                    continue
                # Before orphaning, try to find the heading by its text
                if heading_path and len(heading_path) > 0:
                    heading_text = heading_path[-1].get("text", "")
                    if heading_text:
                        target_level = int(heading_path[-1].get("level") or 0)
                        found_heading = _find_heading_by_text(search_space, heading_text, target_level)
                        if found_heading is not None:
                            heading_start, heading_end = found_heading
                            heading_content = search_space[heading_start:heading_end]
                            wrapped = f'<ac:inline-comment-marker ac:ref="{ref}">{heading_content}</ac:inline-comment-marker>'
                            _commit_injection(scope_start + heading_start, scope_start + heading_end, wrapped)
                            continue
                # If still not preserved, mark as orphan
                _commit_top_orphan_marker(ref)
                continue

        if section_span is not None and preferred_index is not None and anchor_was_nested_marker:
            heading_span_rel = _pick_heading_span_matching_anchor(
                search_space,
                anchor,
                preferred_index,
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
        
        # SMART ANCHOR RECOVERY: If exact anchor not found, try partial match
        # DISABLED: Causing test failures - stick with existing context-based approach
        # if not occurrences:
        #     partial_match = _try_partial_anchor_match(search_space, anchor, preferred_index)
        #     if partial_match is not None:
        #         occurrences = [partial_match]
        #         anchor_used = anchor  # Use original for wrapping
        
        # Prefer occurrences within heading_path branch for nested comments
        if occurrences and heading_path:
            branch_occurrences = [
                idx for idx in occurrences
                if _occurrence_matches_heading_path_fuzzy(search_space, idx, heading_path)
            ]
            if branch_occurrences:
                occurrences = branch_occurrences
        
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
            if (
                selected_index is None
                and len(occurrences) == 1
                and preferred_index is not None
                and heading_path
                and _occurrence_matches_heading_path(search_space, occurrences[0], heading_path)
            ):
                unique_index = occurrences[0]
                unique_context_score = _score_occurrence_context(
                    search_space,
                    anchor_used,
                    unique_index,
                    left_context,
                    right_context,
                )
                unique_right_score = _common_prefix_len(
                    right_context,
                    search_space[unique_index + len(anchor_used):],
                )
                if unique_context_score > 0 or unique_right_score >= _MIN_CONTEXT_FRAGMENT:
                    selected_index = unique_index
        
        # HEADING CONTEXT RECOVERY: Try to find by heading path when anchor lost
        # DISABLED: Was causing issues with existing heading placement logic
        # if selected_index is None and not occurrences and heading_path:
        #     heading_recovery_idx = _recover_by_heading_context(
        #         search_space, heading_path, preferred_index, scope_start
        #     )
        #     if heading_recovery_idx is not None:
        #         selected_index = heading_recovery_idx
        #         # Use orphan marker at recovered position
        #         anchor_used = _ORPHAN_COMMENT_EMPTY_ANCHOR_HTML
        
        if occurrences and preferred_index is not None:
            left_pos, left_len = _find_best_context_fragment(search_space, left_context, from_left=True)
            search_start = (left_pos + left_len) if left_pos is not None else 0
            right_pos, right_len = _find_best_context_fragment(search_space, right_context, from_left=False, start_at=search_start)
            if max(left_len, right_len) < _MIN_CONTEXT_FRAGMENT:
                if _wrap_deleted_heading(ref, left_context, preferred_index, heading_path):
                    continue
        # When exactly 1 occurrence is found but it has CROSSED a block boundary from the expected
        # position (anchor word survived in a different paragraph after a local word replacement),
        # the edited-span picker can locate the replacement word using the surrounding context.
        # Only triggers when the occurrence jumped across a </p>/<li> boundary AND the edited-span
        # has a better left-context score — preventing drift to a surviving copy in another paragraph.
        if (
            selected_index is not None
            and len(occurrences) == 1
            and preferred_index is not None
        ):
            low = min(preferred_index, selected_index)
            high = max(preferred_index, selected_index)
            between_text = search_space[low:high]
            crosses_block = bool(
                re.search(r'</p>|<li\b|</li>|</td>', between_text, re.IGNORECASE)
            )
            if crosses_block:
                occ_left_score = _common_suffix_len(left_context, search_space[:selected_index])
                edited_span_candidate = _pick_edited_context_span(
                    search_space,
                    left_context,
                    right_context,
                    preferred_index=preferred_index,
                    original_anchor=anchor_used,
                )
                if edited_span_candidate is not None:
                    alt_left_score = _common_suffix_len(left_context, search_space[:edited_span_candidate[0]])
                    if alt_left_score > occ_left_score and _is_safe_wrap_span(
                        search_space, edited_span_candidate[0], edited_span_candidate[1]
                    ):
                        span_start_abs = scope_start + edited_span_candidate[0]
                        span_end_abs = scope_start + edited_span_candidate[1]
                        fallback_anchor = search_space[edited_span_candidate[0]:edited_span_candidate[1]]
                        wrapped = f'<ac:inline-comment-marker ac:ref="{ref}">{fallback_anchor}</ac:inline-comment-marker>'
                        _commit_injection(span_start_abs, span_end_abs, wrapped)
                        continue
        if selected_index is None:
            # Only try edited-span picker if anchor genuinely doesn't exist (occurrences is empty).
            # If occurrences exist but context rejected them, skip to fallback handling.
            if not occurrences:
                visible_phrase_span = _pick_visible_phrase_span(
                    search_space,
                    anchor_used,
                    preferred_index=preferred_index,
                )
                if visible_phrase_span is not None:
                    visible_start_rel, visible_end_rel = _expand_span_to_enclosing_inline_tags(
                        search_space,
                        visible_phrase_span[0],
                        visible_phrase_span[1],
                    )
                    if _is_safe_wrap_span(search_space, visible_start_rel, visible_end_rel):
                        visible_context_score = _score_visible_span_context(
                            search_space,
                            visible_start_rel,
                            visible_end_rel,
                            left_context,
                            right_context,
                        )
                        if (
                            visible_context_score >= max(4, _MIN_CONTEXT_FRAGMENT // 2)
                            or _has_meaningful_plain_context_overlap(left_context, search_space[:visible_start_rel], from_left=True)
                            or _has_meaningful_plain_context_overlap(right_context, search_space[visible_end_rel:], from_left=False)
                        ):
                            visible_start_abs = scope_start + visible_start_rel
                            visible_end_abs = scope_start + visible_end_rel
                            wrapped = f'<ac:inline-comment-marker ac:ref="{ref}">{search_space[visible_start_rel:visible_end_rel]}</ac:inline-comment-marker>'
                            _commit_injection(visible_start_abs, visible_end_abs, wrapped)
                            continue

                # Try edited-span picker when exact anchor is not found.
                # This covers: anchor changed (text exists but needs editing) and anchor deleted entirely.
                edited_span = _pick_edited_context_span(
                    search_space,
                    left_context,
                    right_context,
                    preferred_index=preferred_index,
                    original_anchor=anchor,
                )
                if edited_span is not None:
                    span_start_rel, span_end_rel = edited_span
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
                            or _has_deleted_heading_context(search_space, left_context)
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
            # Proximity fallback: Only use if we have multiple occurrences (single occurrence was already
            # context-checked and rejected). With multiple occurrences, proximity helps pick the best one.
            if preferred_index is not None and len(occurrences) > 1:
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

        visible_phrase_span = _pick_visible_phrase_span(
            search_space,
            anchor_used,
            preferred_index=preferred_index,
        )
        if visible_phrase_span is not None:
            visible_start_rel, visible_end_rel = _expand_span_to_enclosing_inline_tags(
                search_space,
                visible_phrase_span[0],
                visible_phrase_span[1],
            )
            if _is_safe_wrap_span(search_space, visible_start_rel, visible_end_rel):
                visible_context_score = _score_visible_span_context(
                    search_space,
                    visible_start_rel,
                    visible_end_rel,
                    left_context,
                    right_context,
                )
                if (
                    visible_context_score >= max(4, _MIN_CONTEXT_FRAGMENT // 2)
                    or _has_meaningful_plain_context_overlap(left_context, search_space[:visible_start_rel], from_left=True)
                    or _has_meaningful_plain_context_overlap(right_context, search_space[visible_end_rel:], from_left=False)
                ):
                    visible_start_abs = scope_start + visible_start_rel
                    visible_end_abs = scope_start + visible_end_rel
                    wrapped = f'<ac:inline-comment-marker ac:ref="{ref}">{search_space[visible_start_rel:visible_end_rel]}</ac:inline-comment-marker>'
                    _commit_injection(visible_start_abs, visible_end_abs, wrapped)
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
                original_anchor=anchor,
            )
            if edited_span is not None:
                edited_anchor = search_space[edited_span[0]:edited_span[1]]
                edited_context_score = _score_occurrence_context(
                    search_space,
                    edited_anchor,
                    edited_span[0],
                    left_context,
                    right_context,
                )
                if (
                    section_span is not None
                    and preferred_index is not None
                    and (
                        _has_deleted_heading_context(search_space, left_context)
                        or _should_route_deleted_anchor_to_heading(anchor_used, edited_anchor, edited_context_score)
                    )
                ):
                    if _wrap_deleted_heading(ref, left_context, preferred_index, heading_path):
                        continue
                span_start_rel, span_end_rel = edited_span
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

        # Exact occurrences existed but were rejected by context checks.
        # Do not fall back to broad span selection that can drift to sibling rows.
        if occurrences and selected_index is None and preferred_index is not None:
            if section_span is not None and _wrap_deleted_heading(ref, left_context, preferred_index, heading_path):
                continue
            _commit_top_orphan_marker(ref)
            continue

        # If original anchor text was deleted entirely, preserve comment at the
        # original position using a visible icon placeholder at that location.
        if not occurrences and preferred_index is not None:
            _commit_top_orphan_marker(ref)
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
                fallback_anchor = _ORPHAN_COMMENT_EMPTY_ANCHOR_HTML
                # Route empty-anchor orphans to batch collection instead of immediate injection
                # This ensures all orphans are consolidated at document top, not scattered
                _commit_top_orphan_marker(ref)
                continue
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
                    _commit_top_orphan_marker(ref)
                    continue
                else:
                    fallback_anchor = search_space[span_start_rel:span_end_rel]
            else:
                if preferred_index is not None:
                    insert_rel = _normalize_insertion_point_outside_tag(search_space, preferred_index)
                else:
                    insert_rel = _normalize_insertion_point_outside_tag(search_space, span_start_rel)
                _commit_top_orphan_marker(ref)
                continue

        wrapped = f'<ac:inline-comment-marker ac:ref="{ref}">{fallback_anchor}</ac:inline-comment-marker>'
        _commit_injection(span_start_abs, span_end_abs, wrapped)

    # Batch inject all orphan markers at document top (single consolidated empty space)
    if orphan_refs_to_batch:
        # Create consolidated orphan marker block - all refs share ONE empty space location
        orphan_block = "".join([
            f'<ac:inline-comment-marker ac:ref="{ref}">{_ORPHAN_COMMENT_EMPTY_ANCHOR_HTML}</ac:inline-comment-marker>'
            for ref in reversed(orphan_refs_to_batch)
        ])
        # Inject all orphans at document start in ONE operation
        _commit_injection(scope_start, scope_start, orphan_block)
        deleted_anchor_icon_count += len(orphan_refs_with_deleted_icon)
        # Count each orphaned comment as preserved/reanchored even though insertion is batched.
        if len(orphan_refs_to_batch) > 1:
            reanchored += len(orphan_refs_to_batch) - 1

    return result, reanchored, skipped, deleted_anchor_icon_count


def _update_page_with_storage(
    base_url: str,
    page_id: str,
    version: int,
    title: str,
    storage_html: str,
    auth: Any,
    headers: Dict[str, str],
    allow_conflict_retry: bool = False,
) -> Dict[str, Any]:
    """PUT the page with new storage HTML content.

    Returns a structured status and, by default, fails closed on version conflict.
    """
    url = f"{base_url.rstrip('/')}/rest/api/content/{page_id}"
    put_headers = {k: v for k, v in headers.items()}
    put_headers["Content-Type"] = "application/json"

    current_version = int(version)
    current_title = str(title or "")
    max_attempts = 3 if allow_conflict_retry else 1
    for _attempt in range(max_attempts):
        payload = {
            "version": {"number": current_version},
            "title": current_title,
            "type": "page",
            "body": {"storage": {"value": storage_html, "representation": "storage"}},
        }
        resp = requests.put(
            url,
            json=payload,
            auth=auth,
            headers=put_headers,
            timeout=_PAGE_STORAGE_UPDATE_TIMEOUT_SECONDS,
        )
        if resp.status_code in (200, 201):
            return {"ok": True, "status": "ok", "http_status": int(resp.status_code)}
        if resp.status_code != 409:
            return {
                "ok": False,
                "status": "http-error",
                "http_status": int(resp.status_code),
                "response_preview": str(resp.text or "")[:500],
            }

        if not allow_conflict_retry:
            latest_version = None
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
                latest_version = int(((latest_data.get("version") or {}).get("number") or 0))
            except Exception:
                latest_version = None
            return {
                "ok": False,
                "status": "version-conflict",
                "http_status": 409,
                "requested_version": current_version,
                "latest_version": latest_version,
            }

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
        except Exception as exc:
            return {
                "ok": False,
                "status": "conflict-refresh-failed",
                "http_status": 409,
                "error": str(exc),
            }

    return {
        "ok": False,
        "status": "version-conflict-retry-exhausted",
        "http_status": 409,
    }


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
        print("[anchor-preserve] Fetching latest page storage after overwrite...")
        page_info = _fetch_page_storage_with_auth(args, config_module)
        new_storage = page_info["storage_html"]
        new_version = page_info["version"] + 1
        title = page_info["title"]
        auth = page_info["auth"]
        hdrs = page_info["headers"]
        section_span = _find_target_storage_span(
            new_storage,
            heading_title,
            heading_level,
            args.anchor_start_name,
            args.anchor_end_name,
        )

        # Strip existing marker wrappers for refs we are about to re-anchor,
        # so comments can move to the correct heading when content is deleted.
        refs_to_strip = set(str(m.get("ref") or "") for m in old_markers if m.get("ref"))
        if refs_to_strip:
            new_storage, _ = _strip_inline_markers_by_ref(new_storage, refs_to_strip)

        print(
            f"[anchor-preserve] Recomputing inline marker placements for {len(old_markers)} captured marker(s)..."
        )
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
        payload_section_span = _find_target_storage_span(
            updated_storage,
            heading_title,
            heading_level,
            args.anchor_start_name,
            args.anchor_end_name,
        )
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

        print(
            f"[anchor-preserve] Saving re-anchored storage back to Confluence (timeout {_PAGE_STORAGE_UPDATE_TIMEOUT_SECONDS}s)..."
        )
        update_result = _update_page_with_storage(
            args.base_url,
            args.page_id,
            new_version,
            title,
            updated_storage,
            auth,
            hdrs,
            allow_conflict_retry=bool(args.allow_reanchor_conflict_retry),
        )
        success = bool(update_result.get("ok"))
        print(
            "[anchor-preserve] Storage save completed."
            if success
            else "[anchor-preserve] Storage save failed without exception."
        )
        return {
            "status": "ok" if success else "update-failed",
            "update_status": str(update_result.get("status") or ""),
            "reanchored": reanchored,
            "skipped": skipped,
            "deleted_anchor_icon_count": deleted_anchor_icon_count,
            "section_found": section_span is not None,
            "payload_storage_html": updated_storage,
            "payload_section_html": payload_section_html,
            "update_result": update_result,
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
    if args.anchor_start_name:
        command.extend(["--anchor-start-name", str(args.anchor_start_name)])
    if args.anchor_end_name:
        command.extend(["--anchor-end-name", str(args.anchor_end_name)])

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
    if args.allow_full_page_fallback:
        command.append("--allow-full-page-fallback")
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
    process = subprocess.run(command, text=True, encoding="utf-8", errors="replace")
    if process.returncode != 0:
        raise RuntimeError(f"scdp_compare_guard.py failed with exit code {process.returncode}")
    return {
        "returncode": process.returncode,
        "stdout": "",
        "stderr": "",
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


def _build_risk_assessment(
    delta: Dict[str, Any],
    storage_anchor_audit: Dict[str, Any],
    inline_visibility: Dict[str, Any],
    recommendation_status: str,
) -> Dict[str, Any]:
    details = storage_anchor_audit.get("details") or []
    orphaned_count = sum(
        1
        for item in details
        if bool(item.get("visible_after_publish"))
        and not str(item.get("after_anchor_text_preview") or "").strip()
    )
    changed_local_context_count = sum(
        1
        for item in details
        if str(item.get("classification") or "") == "reanchored_with_changed_local_context"
    )
    not_visible_count = sum(
        1
        for item in details
        if str(item.get("classification") or "") == "not_visible_after_publish"
    )
    recoverable_count = int(storage_anchor_audit.get("recoverable_marker_count") or 0)
    changed_ratio = (
        round((changed_local_context_count / recoverable_count) * 100.0, 1)
        if recoverable_count > 0
        else 0.0
    )

    visible_markers = int(inline_visibility.get("visible_marker_count") or 0)
    recoverable_markers = int(inline_visibility.get("recoverable_marker_count") or 0)
    visibility_gap_count = max(0, recoverable_markers - visible_markers)

    level = "low"
    reasons: List[str] = []
    if int(delta.get("active_missing_count") or 0) > 0:
        level = "critical"
        reasons.append("active_comments_missing")
    if not_visible_count > 0:
        level = "critical"
        reasons.append("markers_not_visible_after_publish")
    if visibility_gap_count > 0 and level != "critical":
        level = "high"
        reasons.append("visible_marker_gap")
    if orphaned_count > 0 and level in {"low", "medium"}:
        level = "high"
        reasons.append("orphaned_markers_present")
    if changed_local_context_count >= 3 and level in {"low", "medium"}:
        level = "high"
        reasons.append("many_changed_local_context_reanchors")
    elif changed_local_context_count > 0 and level == "low":
        level = "medium"
        reasons.append("changed_local_context_reanchors")
    if recommendation_status.startswith("warning") and level == "low":
        level = "medium"
        reasons.append("warning_recommendation_status")

    manual_review_required = level in {"high", "critical"} or recommendation_status == "review-required"
    return {
        "risk_level": level,
        "manual_review_required": manual_review_required,
        "reasons": reasons,
        "signals": {
            "active_missing_count": int(delta.get("active_missing_count") or 0),
            "orphaned_marker_count": orphaned_count,
            "not_visible_marker_count": not_visible_count,
            "changed_local_context_count": changed_local_context_count,
            "changed_local_context_ratio_percent": changed_ratio,
            "recoverable_marker_count": recoverable_count,
            "visible_marker_gap_count": visibility_gap_count,
        },
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


def _build_reanchor_conflict_telemetry(reanchor_result: Dict[str, Any]) -> Dict[str, Any]:
    update_result = reanchor_result.get("update_result") or {}
    update_status = str(reanchor_result.get("update_status") or update_result.get("status") or "")
    conflict_detected = update_status.startswith("version-conflict")
    telemetry = {
        "reanchor_status": str(reanchor_result.get("status") or ""),
        "update_status": update_status,
        "conflict_detected": conflict_detected,
        "requested_version": update_result.get("requested_version"),
        "latest_version": update_result.get("latest_version"),
        "http_status": update_result.get("http_status"),
        "response_preview": str(update_result.get("response_preview") or "")[:300],
    }
    return telemetry


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
    parser.add_argument(
        "--md-path",
        default=None,
        help=(
            "Markdown file used by Doc Engine publish. If omitted, the newest .md file under "
            f"{_default_md_input_dir()} is used."
        ),
    )
    parser.add_argument(
        "--heading-title",
        required=True,
        help="Heading title used for compare/publish, or 'auto' to resolve exactly one changed heading.",
    )

    parser.add_argument("--compare-mode", choices=["both", "markdown", "storage"], default="both")
    parser.add_argument("--split-level", type=int, choices=range(1, 7), default=1, help="Markdown heading level to split for guard compare")
    parser.add_argument("--anchor-start-name", default=_DEFAULT_MANAGED_ANCHOR_START, help="Confluence Anchor macro name marking the start of the managed document region")
    parser.add_argument("--anchor-end-name", default=_DEFAULT_MANAGED_ANCHOR_END, help="Confluence Anchor macro name marking the end of the managed document region")
    parser.add_argument("--apply", action="store_true", help="Run actual overwrite publish after compare")
    parser.add_argument("--yes", action="store_true", help="Pass --yes to guard script")
    parser.add_argument("--force-scdp-override", action="store_true", help="Pass override gate to guard script")
    parser.add_argument("--yes-override", action="store_true", help="Skip override prompt")
    parser.add_argument("--no-prompt-override", action="store_true", help="Do not prompt for override in compare-only runs")
    parser.add_argument(
        "--allow-full-page-fallback",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Allow auto/guard logic to fall back to full-page overwrite when section-safe publish is not possible "
            "(default: enabled). Use --no-allow-full-page-fallback to enforce strict section-only behavior."
        ),
    )
    parser.add_argument(
        "--require-visible-inline-markers",
        action="store_true",
        help="Fail with a non-zero exit code if active comments cannot all be shown inline after publish.",
    )
    parser.add_argument(
        "--allow-reanchor-conflict-retry",
        action="store_true",
        help="Allow retrying re-anchor storage save on version conflict (less strict). Default is fail-closed on conflict.",
    )
    parser.add_argument(
        "--require-low-risk-reanchor",
        action="store_true",
        help="Fail with a non-zero exit code if risk_assessment marks manual review required.",
    )
    parser.add_argument(
        "--orphan-context-reply",
        action="store_true",
        help="Post an informational reply on orphaned comments showing their original heading hierarchy.",
    )
    parser.add_argument(
        "--fast-preserve-only",
        action="store_true",
        help="Skip compare guard, risk assessment, and report generation. Only preserve comments (fastest mode).",
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
    fast_mode = bool(getattr(args, "fast_preserve_only", False))

    if not os.path.exists(args.guard_script):
        raise SystemExit(f"Guard script not found: {args.guard_script}")

    resolved_md_path = _resolve_md_path(args.md_path)
    if not os.path.exists(resolved_md_path):
        raise SystemExit(f"Markdown file not found: {resolved_md_path}")
    args.md_path = resolved_md_path

    config_module = _load_config_module(args.project_root)
    page_info_cached_before_overwrite: Optional[Dict[str, Any]] = None
    requested_heading_title = str(args.heading_title or "").strip()
    if requested_heading_title.lower() == "auto":
        page_info_for_resolution = _fetch_page_storage_with_auth(args, config_module)
        page_info_cached_before_overwrite = page_info_for_resolution
        anchor_region_available = bool(
            _find_anchor_region_span(
                page_info_for_resolution["storage_html"],
                args.anchor_start_name,
                args.anchor_end_name,
            )
        )
        if bool(args.allow_full_page_fallback):
            print(
                "[target-mode] Managed anchor-region mode active: ignoring --allow-full-page-fallback "
                "to prevent full-page overwrite."
            )
        args.allow_full_page_fallback = False
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

        concrete_changed_titles = [
            title
            for title in changed_titles
            if str(title or "").strip() and title != _FULL_PAGE_AUTO_SENTINEL
        ]
        if len(concrete_changed_titles) > 1 and not bool(args.allow_full_page_fallback):
            # Prefer explicit per-heading runs over broad fallback so auto mode stays section-local.
            return _run_multi_heading_publish(args, concrete_changed_titles)

        args.heading_title = _select_auto_publish_target(
            changed_titles,
            allow_full_page_fallback=bool(args.allow_full_page_fallback),
            anchor_region_available=anchor_region_available,
        )
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
        print(f"[source] Auto-resolved heading title: {_display_heading_target(args.heading_title)}")
    else:
        print(f"[source] Heading title: {_display_heading_target(args.heading_title)}")
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
            page_info_before = page_info_cached_before_overwrite or _fetch_page_storage_with_auth(args, config_module)
            storage_before = page_info_before["storage_html"]
            old_markers_all = _extract_inline_markers(storage_before)
            section_span_before = _find_target_storage_span(
                storage_before,
                args.heading_title,
                args.split_level,
                args.anchor_start_name,
                args.anchor_end_name,
            )
            if section_span_before is not None:
                old_markers = _filter_markers_by_span(old_markers_all, section_span_before)
                old_section_html = storage_before[section_span_before[0]:section_span_before[1]]
                print(
                    f"[anchor-preserve] Found {len(old_markers)} inline marker(s) in target '{args.heading_title}' before overwrite."
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
                    f"[anchor-preserve] Target '{args.heading_title}' not found in old storage; using all {len(old_markers)} inline marker(s)."
                )

            inline_props = _fetch_inline_properties_with_fallback_auth(args, config_module, open_ref_ids)
            before_inline_props = list(inline_props)

            # If marker tags were removed in prior runs, recover marker refs and
            # anchor text from Confluence inlineProperties for active comments.
            if section_span_before is not None and open_ref_ids:
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
                # Annotate heading_path FIRST so it's available for reconciliation and enrichment
                old_markers = _annotate_markers_with_heading_path(
                    old_section_html,
                    int(section_span_before[0]),
                    old_markers,
                )
                old_markers, reconciled = _reconcile_existing_markers_from_inline_properties(
                    storage_before,
                    section_span_before,
                    old_markers,
                    inline_props,
                    owned_refs=owned_refs if open_ref_ids else None,
                )
                if reconciled:
                    print(
                        f"[anchor-preserve] Reconciled {reconciled} marker(s) from inline comment metadata."
                    )
                # Skip historical enrichment in fast mode
                if not getattr(args, "fast_preserve_only", False):
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
                else:
                    history_enriched = 0
            old_markers, orphan_seeded = _seed_missing_orphan_markers(old_markers, before_inline_props)
            supplemented += orphan_seeded
            if orphan_seeded:
                print(
                    f"[anchor-preserve] Seeded {orphan_seeded} top-of-page orphan marker(s) from inline comment metadata."
                )

            # Attach inline-properties anchor text to each marker for fail-safe recovery
            # when the visible marker anchor is already blank (orphaned) in old storage.
            inline_anchor_by_ref = {
                str(item.get("ref") or ""): str(item.get("anchor_html") or "")
                for item in before_inline_props
                if str(item.get("ref") or "") and str(item.get("anchor_html") or "")
            }
            if inline_anchor_by_ref:
                for marker in old_markers:
                    ref = str(marker.get("ref") or "")
                    inline_anchor = inline_anchor_by_ref.get(ref, "")
                    if inline_anchor and _marker_visible_anchor_text(inline_anchor):
                        marker["inline_anchor_html"] = inline_anchor
        except Exception as exc:
            print(f"[anchor-preserve] Warning: could not fetch page storage before overwrite: {exc}")

    before_comment_marker_map = _build_comment_marker_map(active_comments_before, before_inline_props)
    # Skip saving before comments in fast mode
    if not fast_mode:
        _save_json(
            before_comments_path,
            {
                "auth_method": auth_method,
                "all_comments": all_comments_before,
                "active_only": active_comments_before,
                "inline_marker_map": before_comment_marker_map,
            },
        )

    # Fast mode still needs the guard apply step because that is the current
    # overwrite path. What we skip here is downstream compare consumption,
    # report generation, risk assessment, and other post-processing.
    guard_command = _build_guard_command(args, guard_output_json)
    if fast_mode:
        if args.apply:
            print("[source] ⚡ Fast mode: Running overwrite publish, skipping final compare processing, HTML report, and risk assessment.")
            _run_guard_command(guard_command)
        else:
            print("[source] ⚡ Fast mode: Skipping compare guard, HTML report, and risk assessment.")
    else:
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
    if payload_storage_html and not fast_mode:
        _save_text(reanchor_payload_storage_path, payload_storage_html)
    if payload_section_html and not fast_mode:
        _save_text(reanchor_payload_section_path, payload_section_html)
        reinjection_payload_audit["status"] = "payload-captured"
        try:
            page_info_after_storage = _fetch_page_storage_with_auth(args, config_module)
            saved_storage_after = page_info_after_storage.get("storage_html") or ""
            _save_text(saved_storage_after_reanchor_path, saved_storage_after)
            saved_section_span = _find_target_storage_span(
                saved_storage_after,
                args.heading_title,
                args.split_level,
                args.anchor_start_name,
                args.anchor_end_name,
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
    elif payload_section_html and fast_mode:
        reinjection_payload_audit["status"] = "skipped-fast-mode"

    all_comments_after: List[Dict[str, Any]] = all_comments_before
    active_comments_after: List[Dict[str, Any]] = active_comments_before
    if args.apply:
        auth_method_after, all_comments_after, active_comments_after = _fetch_comments_with_fallback_auth(args, config_module)
        if active_comments_after and not fast_mode:
            after_inline_props = _fetch_inline_properties_with_fallback_auth(
                args,
                config_module,
                {str(comment.get("id") or "") for comment in active_comments_after if str(comment.get("id") or "")},
            )
    else:
        after_inline_props = list(before_inline_props)

    compare_result = ({ } if fast_mode else _load_json(guard_output_json))
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

    if fast_mode and not args.require_visible_inline_markers:
        recoverable_marker_count = len({str(marker.get("ref") or "") for marker in old_markers if str(marker.get("ref") or "")})
        skipped_marker_count = int(reanchor_result.get("skipped") or 0)
        visible_marker_count = max(0, recoverable_marker_count - skipped_marker_count)
        inline_visibility = {
            "status": "skipped-fast-mode",
            "recoverable_marker_count": recoverable_marker_count,
            "visible_marker_count": visible_marker_count,
            "visible_marker_refs": [],
            "supplemented_marker_count": supplemented,
        }
        storage_anchor_audit = {
            "status": "skipped-fast-mode",
            "recoverable_marker_count": recoverable_marker_count,
            "details": [],
        }
    else:
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

    if not fast_mode:
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
        if fast_mode:
            recommendation_message = (
                f"{delta['active_auto_resolved_count']} open comment(s) were auto-resolved during overwrite "
                "(anchor text was changed/removed)."
            )
        else:
            recommendation_message = f"{delta['active_auto_resolved_count']} open comment(s) were auto-resolved during overwrite (anchor text was changed/removed). Review the auto_resolved_preview in the report."
    elif delta.get("active_missing_count", 0) == 0:
        recommendation_status = "ok"
        recommendation_message = "All open comments were preserved after overwrite."
    else:
        recommendation_status = "review-required"
        if fast_mode:
            recommendation_message = "Some open comments are missing after overwrite; manual review is recommended."
        else:
            recommendation_message = "Some open comments are missing after overwrite; use compare report and missing preview for manual re-anchor."

    # Skip risk assessment in fast mode
    if fast_mode:
        risk_assessment = {
            "risk_level": "low",
            "manual_review_required": False,
            "reasons": ["Fast mode: risk assessment skipped"],
            "signals": {},
        }
    else:
        risk_assessment = _build_risk_assessment(
            delta,
            storage_anchor_audit,
            inline_visibility,
            recommendation_status,
        )
    orphan_context_targets = []
    if not fast_mode:
        orphan_context_targets = _build_orphan_context_targets(
            storage_anchor_audit,
            before_inline_props,
            old_markers,
            args.heading_title,
        )
    # Skip orphan context replies in fast mode
    if fast_mode:
        orphan_context_replies = {
            "enabled": False,
            "status": "skipped-fast-mode",
            "candidate_count": 0,
            "posted_count": 0,
            "skipped_existing_count": 0,
            "failed_count": 0,
            "details": [],
        }
    else:
        orphan_context_replies = _post_orphan_context_replies(args, config_module, orphan_context_targets)
    reanchor_conflict_telemetry = _build_reanchor_conflict_telemetry(reanchor_result)
    if recommendation_status == "ok" and bool(risk_assessment.get("manual_review_required")):
        recommendation_status = "warning-manual-review-required"
        recommendation_message = (
            "Comments were preserved, but risk signals indicate potential placement ambiguity. "
            "Review storage_anchor_audit and risk_assessment before production sign-off."
        )

    if not fast_mode:
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
                "allow_reanchor_conflict_retry": bool(args.allow_reanchor_conflict_retry),
                "require_low_risk_reanchor": bool(args.require_low_risk_reanchor),
                "orphan_context_reply": bool(args.orphan_context_reply),
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
            "orphan_context_replies": orphan_context_replies,
            "anchor_reinjection": reanchor_result,
            "reanchor_conflict_telemetry": reanchor_conflict_telemetry,
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
            "risk_assessment": risk_assessment,
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

    if fast_mode:
        print("REPORT_PATH=SKIPPED_FAST_MODE")
    else:
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
    print()
    print("=== RISK ASSESSMENT ===")
    print(f"RISK_LEVEL={risk_assessment['risk_level']}")
    print(f"MANUAL_REVIEW_REQUIRED={str(bool(risk_assessment['manual_review_required'])).lower()}")
    print()
    print("=== REANCHOR SAVE STATUS ===")
    print(f"REANCHOR_STATUS={reanchor_conflict_telemetry['reanchor_status']}")
    print(f"REANCHOR_UPDATE_STATUS={reanchor_conflict_telemetry['update_status']}")
    print(f"REANCHOR_CONFLICT_DETECTED={str(bool(reanchor_conflict_telemetry['conflict_detected'])).lower()}")
    if args.orphan_context_reply:
        print()
        print("=== ORPHAN CONTEXT REPLIES ===")
        print(f"ORPHAN_CONTEXT_REPLY_STATUS={orphan_context_replies.get('status', '')}")
        print(f"ORPHAN_CONTEXT_REPLY_CANDIDATES={orphan_context_replies.get('candidate_count', 0)}")
        print(f"ORPHAN_CONTEXT_REPLY_POSTED={orphan_context_replies.get('posted_count', 0)}")
        print(f"ORPHAN_CONTEXT_REPLY_SKIPPED_EXISTING={orphan_context_replies.get('skipped_existing_count', 0)}")
        print(f"ORPHAN_CONTEXT_REPLY_FAILED={orphan_context_replies.get('failed_count', 0)}")

    if args.require_low_risk_reanchor and bool(risk_assessment.get("manual_review_required")):
        print()
        print("LOW_RISK_CHECK=FAILED")
        print(
            "Run requires manual review due to placement-risk signals. "
            "Use risk_assessment.reasons and storage_anchor_audit before production sign-off."
        )
        return 3

    if args.require_visible_inline_markers and inline_visibility_gap:
        print()
        print("INLINE_VISIBILITY_CHECK=FAILED")
        print(recommendation_message)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
