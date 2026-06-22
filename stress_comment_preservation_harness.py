import argparse
import random
from typing import Dict, List, Tuple

from comment_preserve_publish import _extract_inline_markers, _inject_inline_markers


PROFILES = ("text", "table", "macro", "heading-merge")


def _build_base_section(profile: str, rows: int) -> Tuple[str, List[str]]:
    if profile == "table":
        table_rows = []
        anchors = []
        for i in range(rows):
            row = f"<tr><td>svc-{i}</td><td>shared-value-alpha-beta</td></tr>"
            table_rows.append(row)
            anchors.append(f"svc-{i}")
        html = "".join([
            "<h1>Services</h1>",
            "<table><tbody>",
            *table_rows,
            "</tbody></table>",
            "<h1>Archive</h1>",
            "<p>shared-value-alpha-beta shared-value-alpha-beta.</p>",
        ])
        return html, anchors

    if profile == "macro":
        lines = [
            "<h1>Macro Section</h1>",
            "<ac:structured-macro ac:name=\"info\"><ac:rich-text-body>",
        ]
        anchors = []
        for i in range(rows):
            phrase = f"macro line {i} carries shared marker text"
            lines.append(f"<p>{phrase}</p>")
            anchors.append(phrase)
        lines.extend([
            "</ac:rich-text-body></ac:structured-macro>",
            "<h1>Post Macro</h1>",
            "<p>macro line fallback region.</p>",
        ])
        return "".join(lines), anchors

    if profile == "heading-merge":
        lines = ["<h1>Parent</h1>"]
        anchors = []
        for i in range(rows):
            lines.append(f"<h2>Branch {i}</h2>")
            phrase = f"branch-{i} mutable shared phrase"
            lines.append(f"<p>{phrase}</p>")
            anchors.append(phrase)
        return "".join(lines), anchors

    lines = ["<h1>Section A</h1>", "<p>Header intro text.</p>"]
    anchors = []
    for i in range(rows):
        phrase = f"Item {i}: shared phrase alpha beta gamma."
        lines.append(f"<p>{phrase}</p>")
        anchors.append(phrase)
    lines.append("<h1>Section B</h1>")
    for i in range(rows):
        lines.append(f"<p>Shadow {i}: shared phrase alpha beta gamma.</p>")
    return "".join(lines), anchors


def _inject_seed_markers(storage: str, refs: List[str], anchors: List[str]) -> str:
    result = storage
    for ref, anchor in zip(refs, anchors):
        idx = result.find(anchor)
        if idx < 0:
            continue
        wrapped = f'<ac:inline-comment-marker ac:ref="{ref}">{anchor}</ac:inline-comment-marker>'
        result = result[:idx] + wrapped + result[idx + len(anchor):]
    return result


def _make_variant(profile: str, storage: str, rng: random.Random) -> str:
    updated = storage

    if profile == "table":
        if rng.random() < 0.7:
            updated = updated.replace("shared-value-alpha-beta", "shared-value-alpha-delta")
        if rng.random() < 0.4:
            updated = updated.replace("<tr><td>svc-0</td><td>shared-value-alpha-delta</td></tr>", "")
        return updated

    if profile == "macro":
        if rng.random() < 0.8:
            updated = updated.replace("shared marker text", "shared mutated marker text")
        if rng.random() < 0.4:
            updated = updated.replace(
                "<ac:structured-macro ac:name=\"info\"><ac:rich-text-body>",
                "<ac:structured-macro ac:name=\"panel\"><ac:rich-text-body>",
            )
        return updated

    if profile == "heading-merge":
        if rng.random() < 0.7:
            updated = updated.replace(" mutable shared phrase", " rewritten shared phrase")
        if rng.random() < 0.5:
            updated = updated.replace("<h2>Branch 0</h2>", "")
        return updated

    rewrites = [
        ("shared phrase alpha beta gamma", "shared phrase alpha beta delta"),
        ("Header intro text.", "Header overview intro text."),
    ]
    for old, new in rewrites:
        if rng.random() < 0.6:
            updated = updated.replace(old, new)

    if rng.random() < 0.25:
        start = updated.find("<h1>Section A</h1>")
        end = updated.find("<h1>Section B</h1>")
        if start >= 0 and end > start:
            updated = updated[:start] + updated[end:]

    marker = "<h1>Section B</h1>"
    b_start = updated.find(marker)
    if b_start >= 0 and rng.random() < 0.5:
        body = updated[b_start + len(marker):]
        row_tokens = [tok for tok in body.split("</p>") if tok.strip()]
        rng.shuffle(row_tokens)
        shuffled = "".join(tok + "</p>" for tok in row_tokens)
        updated = updated[:b_start + len(marker)] + shuffled

    return updated


def _capture_markers(storage_with_markers: str) -> List[Dict[str, object]]:
    markers = []
    for m in _extract_inline_markers(storage_with_markers):
        markers.append(
            {
                "ref": m.get("ref"),
                "anchor_html": m.get("anchor_html"),
                "left_context": m.get("left_context", ""),
                "right_context": m.get("right_context", ""),
                "start": m.get("start", -1),
                "end": m.get("end", -1),
                "heading_path": [],
            }
        )
    return markers


def _run_once(rng: random.Random, rows: int, marker_count: int, profile: str) -> Tuple[int, int, int]:
    base, anchor_pool = _build_base_section(profile, rows)
    anchors = anchor_pool[: min(marker_count, len(anchor_pool))]
    refs = [f"stress-ref-{i}" for i in range(len(anchors))]
    seeded = _inject_seed_markers(base, refs, anchors)

    markers = _capture_markers(seeded)
    stripped_base = base  # target storage has no markers before reinjection
    variant = _make_variant(profile, stripped_base, rng)

    updated, reanchored, skipped, _deleted_icons = _inject_inline_markers(
        variant,
        markers,
        open_ref_ids=set(),
        section_span=(0, len(variant)),
    )
    after = _extract_inline_markers(updated)

    total = len(markers)
    visible = len(after)
    orphaned = sum(1 for item in after if not str(item.get("anchor_html") or "").strip())
    return total, visible, orphaned


def main() -> int:
    parser = argparse.ArgumentParser(description="Local stress harness for comment re-anchor behavior")
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--rows", type=int, default=25)
    parser.add_argument("--markers", type=int, default=12)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--profile", choices=("all", *PROFILES), default="all")
    parser.add_argument("--min-visible-rate", type=float, default=95.0)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    total_markers = 0
    total_visible = 0
    total_orphaned = 0

    profiles = list(PROFILES) if args.profile == "all" else [args.profile]
    per_profile: Dict[str, Dict[str, int]] = {
        name: {"total": 0, "visible": 0, "orphaned": 0}
        for name in profiles
    }

    for _ in range(args.iterations):
        profile = profiles[_ % len(profiles)]
        total, visible, orphaned = _run_once(rng, args.rows, args.markers, profile)
        total_markers += total
        total_visible += visible
        total_orphaned += orphaned
        per_profile[profile]["total"] += total
        per_profile[profile]["visible"] += visible
        per_profile[profile]["orphaned"] += orphaned

    visible_rate = (100.0 * total_visible / total_markers) if total_markers else 0.0
    orphan_rate = (100.0 * total_orphaned / total_markers) if total_markers else 0.0

    print("=== STRESS HARNESS SUMMARY ===")
    print(f"iterations={args.iterations}")
    print(f"total_markers={total_markers}")
    print(f"visible_after_reanchor={total_visible}")
    print(f"orphaned_after_reanchor={total_orphaned}")
    print(f"visible_rate_percent={visible_rate:.2f}")
    print(f"orphan_rate_percent={orphan_rate:.2f}")
    print("profiles=")
    for name in profiles:
        stats = per_profile[name]
        p_total = stats["total"]
        p_visible_rate = (100.0 * stats["visible"] / p_total) if p_total else 0.0
        p_orphan_rate = (100.0 * stats["orphaned"] / p_total) if p_total else 0.0
        print(f"  {name}: visible_rate={p_visible_rate:.2f}% orphan_rate={p_orphan_rate:.2f}%")

    # Non-zero only on severe visibility failure; orphaning is expected in fail-closed strategy.
    if visible_rate < float(args.min_visible_rate):
        print("HARNESS_STATUS=FAILED")
        return 2

    print("HARNESS_STATUS=OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
