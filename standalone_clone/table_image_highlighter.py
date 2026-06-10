from collections import Counter
import html
import re
from typing import Any, Callable, Dict, List, Optional

from highlight_scenarios import image_tag_style, image_wrapper_style, table_row_style, table_wrapper_style


def collect_storage_image_changes(
    previous_storage: str,
    current_storage: str,
    collect_net_changes: Callable[[str, str], Dict[str, Any]],
) -> Dict[str, Any]:
    """Collect image-level changes directly from storage HTML."""

    def _extract_refs(storage_html: str) -> List[str]:
        text = str(storage_html or "")
        refs: List[str] = []

        for match in re.finditer(r'ri:filename\s*=\s*["\']([^"\']+)["\']', text, flags=re.IGNORECASE):
            filename = str(match.group(1) or "").strip()
            if filename:
                refs.append(filename)

        for match in re.finditer(r'<img\b[^>]*\bsrc\s*=\s*["\']([^"\']+)["\']', text, flags=re.IGNORECASE):
            src = str(match.group(1) or "").strip()
            if src:
                refs.append(src)

        out: List[str] = []
        seen = set()
        for item in refs:
            key = item.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(f"!{item}!")
        return out

    before_refs = _extract_refs(previous_storage)
    after_refs = _extract_refs(current_storage)
    if not before_refs and not after_refs:
        return {"added": [], "deleted": [], "replaced": []}

    return collect_net_changes("\n".join(before_refs), "\n".join(after_refs))


def apply_direct_storage_html_highlights(
    previous_storage: str,
    current_storage: str,
    table_style: str = "added",
    paragraph_style_kind: str = "added",
) -> str:
    """Highlight only net-new table/image blocks by content-aware counting.
    
    For duplicates, only highlights the LAST (newest) occurrence.
    """
    prev = str(previous_storage or "")
    curr = str(current_storage or "")
    if not prev or not curr:
        return curr

    table_pat = re.compile(r"<table\b[^>]*>.*?</table>", re.IGNORECASE | re.DOTALL)
    ac_image_pat = re.compile(r"<ac:image\b[^>]*>.*?</ac:image>", re.IGNORECASE | re.DOTALL)
    html_img_pat = re.compile(r"<img\b[^>]*?/?>", re.IGNORECASE | re.DOTALL)

    def _normalize_block_key(block_html: str) -> str:
        """Aggressive normalization: collapse all whitespace, lowercase, remove noise."""
        cleaned = str(block_html or "")
        # Remove all style/class attributes that might differ (but keep content)
        cleaned = re.sub(r'\s+(style|class)\s*=\s*["\'][^"\']*["\']', '', cleaned, flags=re.IGNORECASE)
        # Collapse all consecutive whitespace to single space
        cleaned = re.sub(r'\s+', ' ', cleaned).strip().lower()
        return cleaned

    def _extract_blocks(pattern: re.Pattern[str], html_text: str) -> List[str]:
        """Extract all matching blocks."""
        blocks = []
        for match in pattern.finditer(str(html_text or "")):
            block = str(match.group(0) or "").strip()
            if block:
                blocks.append(block)
        return blocks

    def _identify_net_added_indices(pattern: re.Pattern[str]) -> Dict[str, List[int]]:
        """Return dict mapping normalized key to indices of net-added blocks in current.
        
        For duplicates, only indices of blocks NOT present in previous are marked.
        For truly new (added) duplicates, only the LAST occurrence is marked.
        """
        before_blocks = _extract_blocks(pattern, prev)
        after_blocks = _extract_blocks(pattern, curr)
        
        before_keys = [_normalize_block_key(b) for b in before_blocks]
        after_keys = [_normalize_block_key(b) for b in after_blocks]
        
        before_counter = Counter(before_keys)
        after_counter = Counter(after_keys)
        
        # Find which keys have net additions
        net_added_keys = {}
        for key, after_count in after_counter.items():
            before_count = before_counter.get(key, 0)
            delta = after_count - before_count
            if delta > 0:
                # This key has net additions. Find the indices of NEW ones.
                # Strategy: mark only the LAST (delta) occurrences as new
                indices = [i for i, k in enumerate(after_keys) if k == key]
                # Mark only the last (delta) indices as new
                new_indices = indices[-delta:] if delta <= len(indices) else indices
                net_added_keys[key] = new_indices
        
        return net_added_keys

    def _wrap_net_added_blocks(
        html_text: str,
        pattern: re.Pattern[str],
        net_added_indices_map: Dict[str, List[int]],
        wrapper_css: str,
    ) -> str:
        """Wrap only the net-added blocks at their specific indices.
        
        For duplicates: wraps only the LAST (newest) occurrence of each block type.
        """
        if not net_added_indices_map:
            return html_text

        initial_html = str(html_text or "")
        
        # Extract all match content from ORIGINAL html, preserving order
        all_matches = list(pattern.finditer(initial_html))
        if not all_matches:
            return initial_html
        
        all_match_contents = [str(m.group(0) or "").strip() for m in all_matches]
        
        # For each key in net_added_indices_map, mark which indices should be wrapped
        indices_to_wrap = set()
        for key, indices in net_added_indices_map.items():
            for idx in indices:
                if idx < len(all_matches):
                    indices_to_wrap.add(idx)
        
        # Now find all these match contents in the current (original) HTML
        # For each, track all positions it appears
        position_tracker: Dict[str, List[int]] = {}  # content -> list of positions
        for idx in indices_to_wrap:
            content = all_match_contents[idx]
            if content not in position_tracker:
                # Find all occurrences of this content
                positions = []
                search_start = 0
                while True:
                    pos = initial_html.find(content, search_start)
                    if pos == -1:
                        break
                    positions.append(pos)
                    search_start = pos + 1
                position_tracker[content] = positions
        
        # Build list of (position, content, length) tuples sorted by position (descending)
        # We process in reverse to avoid position shifts
        wraps_to_apply: List[tuple] = []
        for idx in indices_to_wrap:
            content = all_match_contents[idx]
            if content in position_tracker:
                positions = position_tracker[content]
                # For multiple occurrences of same content, mark only the LAST one(s)
                # Since we only have one "net added" occurrence per key, take the last position
                if positions:
                    last_pos = positions[-1]  # LAST occurrence
                    wraps_to_apply.append((last_pos, content, len(content)))
                    # Remove this position so we don't wrap it again
                    positions.pop()
        
        # Sort by position descending (process from end to start to avoid position shifts)
        wraps_to_apply.sort(reverse=True, key=lambda x: x[0])
        
        updated = initial_html
        for pos, content, length in wraps_to_apply:
            # Double-check this position still has the right content (it should)
            if updated[pos:pos + length] != content:
                continue
            
            # Check if already highlighted
            before_slice = updated[max(0, pos - 100):pos]
            if "data-dac='hl'" in before_slice or 'data-dac="hl"' in before_slice:
                continue
            
            # Wrap this specific occurrence
            wrapped = f"<div data-dac='hl' style='{wrapper_css}'>{content}</div>"
            updated = updated[:pos] + wrapped + updated[pos + length:]

        return updated

    result_html = curr
    result_html = _wrap_net_added_blocks(
        result_html, 
        table_pat, 
        _identify_net_added_indices(table_pat),
        table_wrapper_style(table_style)
    )
    image_css = image_wrapper_style(paragraph_style_kind)
    result_html = _wrap_net_added_blocks(
        result_html, 
        ac_image_pat, 
        _identify_net_added_indices(ac_image_pat),
        image_css
    )
    result_html = _wrap_net_added_blocks(
        result_html, 
        html_img_pat, 
        _identify_net_added_indices(html_img_pat),
        image_css
    )
    return result_html


def collect_storage_table_changes(
    previous_storage: str,
    current_storage: str,
    collect_net_changes: Callable[[str, str], Dict[str, Any]],
    normalize_compare_text: Callable[[str], str],
) -> Dict[str, Any]:
    """Collect table-row changes directly from storage HTML."""

    def _extract_rows(storage_html: str) -> List[str]:
        html_text = str(storage_html or "")
        rows: List[str] = []

        tr_pattern = re.compile(r"<tr\b[^>]*>(.*?)</tr>", flags=re.IGNORECASE | re.DOTALL)
        td_pattern = re.compile(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", flags=re.IGNORECASE | re.DOTALL)

        for tr_match in tr_pattern.finditer(html_text):
            tr_inner = str(tr_match.group(1) or "")
            cells: List[str] = []
            for td_match in td_pattern.finditer(tr_inner):
                cell_html = str(td_match.group(1) or "")
                cell_text = re.sub(r"<[^>]+>", " ", cell_html)
                cell_text = html.unescape(" ".join(cell_text.split()).strip())
                if cell_text:
                    cells.append(cell_text)

            if cells:
                rows.append("| " + " | ".join(cells) + " |")

        out: List[str] = []
        seen = set()
        for row in rows:
            key = normalize_compare_text(row)
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(row)
        return out

    before_rows = _extract_rows(previous_storage)
    after_rows = _extract_rows(current_storage)
    if not before_rows and not after_rows:
        return {"added": [], "deleted": [], "replaced": []}

    return collect_net_changes("\n".join(before_rows), "\n".join(after_rows))


def extract_image_candidates(line: str) -> List[str]:
    text = str(line or "").strip()
    candidates: List[str] = []

    def _normalize_src(value: str) -> str:
        src = str(value or "").strip()
        while len(src) >= 2:
            if (src.startswith('"') and src.endswith('"')) or (src.startswith("'") and src.endswith("'")):
                src = src[1:-1].strip()
                continue
            break
        return src

    def _basename(value: str) -> str:
        src = _normalize_src(value)
        src = src.replace("\\", "/")
        return src.split("/")[-1].split("?")[0].strip()

    md = re.match(r"^!\[[^\]]*\]\(([^)]+)\)$", text)
    if md:
        src = _normalize_src(md.group(1))
        if src:
            candidates.append(src)
            base = _basename(src)
            if base:
                candidates.append(base)

    conf = re.match(r"^!([^!|]+)(?:\|[^!]*)?!$", text)
    if conf:
        ref = _normalize_src(conf.group(1))
        if ref:
            candidates.append(ref)
            base = _basename(ref)
            if base:
                candidates.append(base)

    for match in re.finditer(r"ri:filename\s*=\s*['\"]([^'\"]+)['\"]", text, flags=re.IGNORECASE):
        filename = _normalize_src(match.group(1))
        if filename:
            candidates.append(filename)
            base = _basename(filename)
            if base:
                candidates.append(base)

    out: List[str] = []
    seen = set()
    for item in candidates:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def parse_table_cells(line: str) -> List[str]:
    stripped = str(line or "").strip()
    if stripped.startswith("|") and stripped.endswith("|"):
        if re.match(r"^[|:\- ]+$", stripped):
            return []
        return [
            re.sub(r"\\([\\`*_{}\[\]()#+\-.!|])", r"\1", cell.strip())
            for cell in stripped.strip("|").split("|")
            if cell.strip()
        ]
    if "\t" in stripped:
        return [
            re.sub(r"\\([\\`*_{}\[\]()#+\-.!|])", r"\1", cell.strip())
            for cell in stripped.split("\t")
            if cell.strip()
        ]
    return []


def image_change_key(line: str) -> str:
    refs = extract_image_candidates(line)
    if not refs:
        return ""
    preferred = refs[-1] if refs else refs[0]
    return str(preferred or "").strip().lower()


def table_change_key(line: str, normalize_compare_text: Callable[[str], str]) -> str:
    cells = parse_table_cells(line)
    normalized = [normalize_compare_text(cell) for cell in cells if normalize_compare_text(cell)]
    if not normalized:
        return ""
    return "|".join(normalized)


def disambiguate_table_with_context(
    html_text: str,
    candidates: List[re.Match[str]],
    context_width: int = 200,
) -> Optional[re.Match[str]]:
    if len(candidates) <= 1:
        return candidates[0] if candidates else None

    scored: List[tuple[int, int, re.Match[str]]] = []
    for match in candidates:
        table_start = match.start()
        table_end = match.end()
        before_start = max(0, table_start - context_width)
        before_text = html_text[before_start:table_start].strip()
        after_end = min(len(html_text), table_end + context_width)
        after_text = html_text[table_end:after_end].strip()

        before_plain = re.sub(r"<[^>]+>", " ", before_text)
        after_plain = re.sub(r"<[^>]+>", " ", after_text)
        before_words = {
            word.lower() for word in before_plain.split() if (len(word) >= 3 and word.isalnum()) or "_" in word or "-" in word
        }
        after_words = {
            word.lower() for word in after_plain.split() if (len(word) >= 3 and word.isalnum()) or "_" in word or "-" in word
        }
        context_size = len(before_words) + len(after_words)
        scored.append((context_size, -match.start(), match))

    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return scored[0][2] if scored else (candidates[0] if candidates else None)


def try_highlight_img(
    line: str,
    html_text: str,
    style: str,
    *,
    escape_text: Callable[[str], str],
    window_bounds: Callable[[Optional[tuple[int, int]], int], tuple[int, int]],
    debug_skip_once: Callable[[str], None],
    search_window: Optional[tuple[int, int]] = None,
    prefer_last: bool = False,
) -> str:
    candidates = extract_image_candidates(line)
    if not candidates:
        return html_text

    for candidate in candidates:
        src = escape_text(candidate)
        img_pat = re.compile(rf'(<img\b[^>]*src=["\']?[^"\'>]*{re.escape(src)}[^"\'>]*["\']?[^>]*/?>)', re.IGNORECASE)
        matches = [match for match in img_pat.finditer(html_text)]
        if search_window:
            left, right = window_bounds(search_window, len(html_text))
            matches = [match for match in matches if match.start() >= left and match.end() <= right]
        if (not search_window) and len(matches) > 1:
            debug_skip_once(f"Ambiguous <img> match for '{candidate}' ({len(matches)} candidates, no caption scope).")
            continue
        if prefer_last:
            matches = list(reversed(matches))
        if not matches:
            continue
        chosen = None
        for match in matches:
            img_tag = match.group(1)
            if "data-dac='hl'" in img_tag or 'data-dac="hl"' in img_tag:
                continue
            chosen = match
            break
        if not chosen:
            continue
        img_tag = chosen.group(1)
        style_value = image_tag_style(style)
        if re.search(r"\sstyle=", img_tag, re.IGNORECASE):
            updated_img = re.sub(
                r"\sstyle=(['\"])(.*?)\1",
                lambda mm: f" style={mm.group(1)}{mm.group(2)} {style_value}{mm.group(1)}",
                img_tag,
                count=1,
                flags=re.IGNORECASE,
            )
            updated_img = re.sub(r"<img\b", "<img data-dac='hl'", updated_img, count=1, flags=re.IGNORECASE)
        else:
            updated_img = re.sub(r"<img\b", f"<img data-dac='hl' style='{style_value}'", img_tag, count=1, flags=re.IGNORECASE)
        return html_text[:chosen.start()] + updated_img + html_text[chosen.end():]
    return html_text


def try_highlight_table_block(
    line: str,
    html_text: str,
    style: str,
    *,
    escape_text: Callable[[str], str],
    normalize_compare_text: Callable[[str], str],
    search_window: Optional[tuple[int, int]] = None,
    prefer_last: bool = False,
) -> str:
    stripped = str(line or "").strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        return html_text
    cells = [re.sub(r"\\([\\`*_{}\[\]()#+\-.!|])", r"\1", cell.strip()) for cell in stripped.strip("|").split("|") if cell.strip()]
    if not cells:
        return html_text
    key_cells = [cell for cell in cells if len(cell) >= 3 and not re.match(r"^[-:]+$", cell)]
    if not key_cells:
        return html_text

    table_pat = re.compile(r"<table\b[^>]*>.*?</table>", re.IGNORECASE | re.DOTALL)
    candidates = [match for match in table_pat.finditer(html_text)]
    if search_window:
        left, right = search_window
        candidates = [match for match in candidates if match.start() >= left and match.end() <= right]
    if prefer_last:
        candidates = list(reversed(candidates))

    matched_blocks: List[re.Match[str]] = []
    for match in candidates:
        block = match.group(0)
        if "data-dac='hl'" in block or 'data-dac="hl"' in block:
            continue
        block_lower = block.lower()
        exact_score = sum(1 for cell in key_cells if escape_text(cell).lower() in block_lower)
        if exact_score == 0:
            block_plain = normalize_compare_text(re.sub(r"<[^>]+>", " ", block))
            exact_score = sum(1 for cell in key_cells if normalize_compare_text(cell) and normalize_compare_text(cell) in block_plain)
        if exact_score > 0:
            matched_blocks.append(match)

    if not matched_blocks:
        return html_text

    if (not search_window) and len(matched_blocks) > 1:
        chosen = disambiguate_table_with_context(html_text, matched_blocks) or (matched_blocks[-1] if prefer_last else matched_blocks[0])
    else:
        chosen = matched_blocks[-1] if prefer_last else matched_blocks[0]

    block = chosen.group(0)
    wrapped = f"<div data-dac='hl' style='{table_wrapper_style(style)}'>{block}</div>"
    return html_text[:chosen.start()] + wrapped + html_text[chosen.end():]


def try_highlight_table_row(
    line: str,
    html_text: str,
    style: str,
    *,
    normalize_compare_text: Callable[[str], str],
    search_window: Optional[tuple[int, int]] = None,
    prefer_last: bool = False,
) -> str:
    stripped = str(line or "").strip()
    cells: List[str] = []
    if stripped.startswith("|") and stripped.endswith("|"):
        if re.match(r"^[|:\- ]+$", stripped):
            return html_text
        cells = [re.sub(r"\\([\\`*_{}\[\]()#+\-.!|])", r"\1", cell.strip()) for cell in stripped.strip("|").split("|") if cell.strip()]
    elif "\t" in stripped:
        cells = [re.sub(r"\\([\\`*_{}\[\]()#+\-.!|])", r"\1", cell.strip()) for cell in stripped.split("\t") if cell.strip()]
    else:
        return html_text
    if not cells:
        return html_text

    wanted_cells = [normalize_compare_text(cell) for cell in cells if normalize_compare_text(cell) and not re.match(r"^[-:]+$", str(cell or "").strip())]
    if not wanted_cells:
        return html_text

    tr_pat = re.compile(r"(<tr\b[^>]*>)(.*?)(</tr>)", re.IGNORECASE | re.DOTALL)
    td_pat = re.compile(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", re.IGNORECASE | re.DOTALL)
    scored_rows: List[tuple[int, int, int, re.Match[str]]] = []
    for match in tr_pat.finditer(html_text):
        row_html = match.group(2)
        row_cells_norm: List[str] = []
        for cell_match in td_pat.finditer(row_html):
            raw_cell_text = re.sub(r"<[^>]+>", " ", str(cell_match.group(1) or ""))
            normalized = normalize_compare_text(" ".join(raw_cell_text.split()).strip())
            if normalized:
                row_cells_norm.append(normalized)
        if not row_cells_norm:
            continue

        exact_hits = sum(1 for wanted in wanted_cells if wanted in row_cells_norm)
        substr_hits = 0
        if exact_hits == 0:
            for wanted in wanted_cells:
                if len(wanted) < 3:
                    continue
                for row_cell in row_cells_norm:
                    if wanted in row_cell or row_cell in wanted:
                        substr_hits += 1
                        break

        word_score = 0
        if exact_hits == 0 and substr_hits == 0:
            row_words = set(" ".join(row_cells_norm).split())
            for wanted in wanted_cells:
                wanted_words = set(wanted.split())
                shared = wanted_words & row_words
                if wanted_words and len(shared) / len(wanted_words) >= 0.5:
                    word_score += len(shared)

        hit_count = exact_hits * 3 + substr_hits * 2 + word_score
        if hit_count > 0:
            scored_rows.append((hit_count, len(row_cells_norm), -match.start(), match))

    if search_window:
        left, right = search_window
        scored_rows = [item for item in scored_rows if item[3].start() >= left and item[3].end() <= right]
    if not scored_rows:
        return html_text

    scored_rows.sort(reverse=True)
    matches = [item[3] for item in scored_rows]
    if prefer_last:
        matches = list(reversed(matches))

    chosen = None
    for match in matches:
        matched_row = match.group(0)
        if "data-dac='hl'" in matched_row or 'data-dac="hl"' in matched_row:
            continue
        chosen = match
        break
    if not chosen:
        return html_text

    matched_row = chosen.group(0)
    open_tr = chosen.group(1)
    row_style = table_row_style(style)
    if re.search(r"\sstyle=", open_tr, re.IGNORECASE):
        updated_open_tr = re.sub(
            r"\sstyle=(['\"])(.*?)\1",
            lambda mm: f" style={mm.group(1)}{mm.group(2)} {row_style}{mm.group(1)}",
            open_tr,
            count=1,
            flags=re.IGNORECASE,
        )
        updated_open_tr = re.sub(r"<tr\b", "<tr data-dac='hl'", updated_open_tr, count=1, flags=re.IGNORECASE)
    else:
        updated_open_tr = re.sub(r"<tr\b", f"<tr data-dac='hl' style='{row_style}'", open_tr, count=1, flags=re.IGNORECASE)
    return html_text[:chosen.start()] + matched_row.replace(open_tr, updated_open_tr, 1) + html_text[chosen.end():]


def try_highlight_table_cell_diff(
    old_line: str,
    new_line: str,
    html_text: str,
    *,
    normalize_compare_text: Callable[[str], str],
    visible_line_text: Callable[[str], str],
    try_highlight_text_block: Optional[Callable[[str, str, str], tuple[str, bool]]],
    search_window: Optional[tuple[int, int]] = None,
    prefer_last: bool = False,
) -> str:
    old_cells = parse_table_cells(old_line)
    new_cells = parse_table_cells(new_line)
    if not old_cells or not new_cells:
        return html_text

    wanted_cells = [normalize_compare_text(cell) for cell in new_cells if normalize_compare_text(cell) and not re.match(r"^[-:]+$", str(cell or "").strip())]
    if not wanted_cells:
        return html_text

    tr_pat = re.compile(r"(<tr\b[^>]*>)(.*?)(</tr>)", re.IGNORECASE | re.DOTALL)
    td_pat = re.compile(r"(<t[dh]\b[^>]*>)(.*?)(</t[dh]>)", re.IGNORECASE | re.DOTALL)

    scored_rows: List[tuple[int, int, int, re.Match[str]]] = []
    for match in tr_pat.finditer(html_text):
        row_html = match.group(2)
        row_cells_norm: List[str] = []
        for cell_match in td_pat.finditer(row_html):
            raw_cell_text = re.sub(r"<[^>]+>", " ", str(cell_match.group(2) or ""))
            normalized = normalize_compare_text(" ".join(raw_cell_text.split()).strip())
            if normalized:
                row_cells_norm.append(normalized)
        if not row_cells_norm:
            continue
        exact_hits = sum(1 for wanted in wanted_cells if wanted in row_cells_norm)
        if exact_hits > 0:
            scored_rows.append((exact_hits, len(row_cells_norm), -match.start(), match))

    if search_window:
        left, right = search_window
        scored_rows = [item for item in scored_rows if item[3].start() >= left and item[3].end() <= right]
    if not scored_rows:
        return html_text

    scored_rows.sort(reverse=True)
    matches = [item[3] for item in scored_rows]
    if prefer_last:
        matches = list(reversed(matches))

    chosen = None
    for match in matches:
        if "data-dac='hl'" in match.group(0) or 'data-dac="hl"' in match.group(0):
            continue
        chosen = match
        break
    if not chosen:
        return html_text

    row_html = chosen.group(2)
    cell_matches = list(td_pat.finditer(row_html))
    if not cell_matches:
        return html_text

    changed_indexes: List[int] = []
    max_len = min(len(old_cells), len(new_cells), len(cell_matches))
    for index in range(max_len):
        if normalize_compare_text(old_cells[index]) != normalize_compare_text(new_cells[index]):
            changed_indexes.append(index)
    if len(new_cells) > len(old_cells):
        changed_indexes.extend(i for i in range(len(old_cells), min(len(new_cells), len(cell_matches))))

    changed_indexes = sorted(set(index for index in changed_indexes if 0 <= index < len(cell_matches)))
    if not changed_indexes:
        return html_text

    updated_row_html = row_html
    cell_style = "background-color:#e3f2fd; box-shadow:0 0 0 1px #1e88e5 inset;"
    for index in reversed(changed_indexes):
        cell_match = cell_matches[index]
        open_cell = cell_match.group(1)
        inner_cell = cell_match.group(2)
        close_cell = cell_match.group(3)

        target_inner = inner_cell
        updated_text = visible_line_text(new_cells[index]) if index < len(new_cells) else ""
        if updated_text and try_highlight_text_block:
            target_inner, changed = try_highlight_text_block(inner_cell, updated_text, "replaced")
            if not changed:
                target_inner = inner_cell

        if re.search(r"\sstyle=", open_cell, re.IGNORECASE):
            updated_open = re.sub(
                r"\sstyle=(['\"])(.*?)\1",
                lambda mm: f" style={mm.group(1)}{mm.group(2)} {cell_style}{mm.group(1)}",
                open_cell,
                count=1,
                flags=re.IGNORECASE,
            )
        else:
            updated_open = re.sub(r"<t([dh])\b", rf"<t\1 data-dac='hl' style='{cell_style}'", open_cell, count=1, flags=re.IGNORECASE)
        if "data-dac='hl'" not in updated_open and 'data-dac="hl"' not in updated_open:
            updated_open = re.sub(r"<t([dh])\b", r"<t\1 data-dac='hl'", updated_open, count=1, flags=re.IGNORECASE)

        full_new_cell = f"{updated_open}{target_inner}{close_cell}"
        updated_row_html = updated_row_html[:cell_match.start()] + full_new_cell + updated_row_html[cell_match.end():]

    updated_row = chosen.group(1) + updated_row_html + chosen.group(3)
    return html_text[:chosen.start()] + updated_row + html_text[chosen.end():]


def try_highlight_any_ac_image(
    html_text: str,
    style: str,
    *,
    debug_skip_once: Callable[[str], None],
    search_window: Optional[tuple[int, int]] = None,
    prefer_last: bool = False,
) -> str:
    ac_pat = re.compile(r'<ac:image\b[^>]*>.*?</ac:image>', re.IGNORECASE | re.DOTALL)
    matches = [match for match in ac_pat.finditer(html_text)]
    if search_window:
        left, right = search_window
        matches = [match for match in matches if match.start() >= left and match.end() <= right]
    if (not search_window) and len(matches) > 1:
        debug_skip_once(f"Ambiguous generic image placeholder ({len(matches)} <ac:image> candidates, no caption scope).")
        return html_text
    if prefer_last:
        matches = list(reversed(matches))

    for match in matches:
        block = match.group(0)
        if "data-dac='hl'" in block or 'data-dac="hl"' in block:
            continue
        wrapped = f"<div data-dac='hl' style='{image_wrapper_style(style)}'>{block}</div>"
        return html_text[:match.start()] + wrapped + html_text[match.end():]
    return html_text


def try_highlight_ac_image(
    line: str,
    html_text: str,
    style: str,
    *,
    debug_skip_once: Callable[[str], None],
    search_window: Optional[tuple[int, int]] = None,
    prefer_last: bool = False,
) -> str:
    candidates = extract_image_candidates(line)
    if not candidates:
        return html_text

    ac_pat = re.compile(r'<ac:image\b[^>]*>.*?</ac:image>', re.IGNORECASE | re.DOTALL)
    matches = [match for match in ac_pat.finditer(html_text)]
    if search_window:
        left, right = search_window
        matches = [match for match in matches if match.start() >= left and match.end() <= right]

    candidate_matches: List[re.Match[str]] = []
    for match in matches:
        block = match.group(0)
        if "data-dac='hl'" in block or 'data-dac="hl"' in block:
            continue
        block_lower = block.lower()
        if any(candidate.lower() in block_lower for candidate in candidates):
            candidate_matches.append(match)

    if (not search_window) and len(candidate_matches) > 1:
        debug_skip_once(
            f"Ambiguous <ac:image> match for '{str(line or '').strip()[:80]}' ({len(candidate_matches)} candidates, no caption scope)."
        )
        return html_text
    if not candidate_matches:
        return html_text
    if prefer_last:
        candidate_matches = list(reversed(candidate_matches))

    chosen = candidate_matches[0]
    block = chosen.group(0)
    wrapped = f"<div data-dac='hl' style='{image_wrapper_style(style)}'>{block}</div>"
    return html_text[:chosen.start()] + wrapped + html_text[chosen.end():]
