"""
Generate beautiful HTML reports for SCDP compare results.
Shows added (green) and deleted (red) content with proper highlighting.
"""

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _colorize_diff_lines(diff_lines: List[str], style: str = "normal") -> str:
    """Convert unified diff lines to colorized HTML.

    style="normal": + green, - red strikethrough
    style="server": + / - blue (manual SCDP edits since last publish)
    """
    html_lines = []
    
    for line in diff_lines:
        if not line:
            continue
        
        escaped = _escape_html(line)
        
        # Header lines (@@)
        if line.startswith("@@"):
            html_lines.append(f'<tr class="hunk-header"><td colspan="2"><code>{escaped}</code></td></tr>')
        # Removed/SCDP-edit lines
        elif line.startswith("-"):
            if style == "server":
                html_lines.append(
                    f'<tr class="diff-scdp-edit"><td class="line-marker">✎</td>'
                    f'<td><code>{escaped}</code></td></tr>'
                )
            else:
                html_lines.append(
                    f'<tr class="diff-removed"><td class="line-marker">−</td>'
                    f'<td><code>{escaped}</code></td></tr>'
                )
        # Added lines
        elif line.startswith("+"):
            if style == "server":
                html_lines.append(
                    f'<tr class="diff-scdp-edit"><td class="line-marker">✎</td>'
                    f'<td><code>{escaped}</code></td></tr>'
                )
            else:
                html_lines.append(
                    f'<tr class="diff-added"><td class="line-marker">+</td>'
                    f'<td><code>{escaped}</code></td></tr>'
                )
        # Unchanged lines
        elif line.startswith(" "):
            html_lines.append(
                f'<tr class="diff-context"><td class="line-marker"> </td>'
                f'<td><code>{escaped}</code></td></tr>'
            )
        # Other headers
        else:
            html_lines.append(
                f'<tr class="diff-header"><td colspan="2"><code>{escaped}</code></td></tr>'
            )
    
    return "\n".join(html_lines)


def _render_human_readable_preview(preview_items: List[Dict[str, Any]], empty_message: str) -> str:
    """Render semantic diff preview items as HTML table rows."""
    html_lines = []

    for item in preview_items or []:
        if isinstance(item, dict):
            item_type = str(item.get("type") or "context").lower()
            text = str(item.get("text") or "").strip()
        else:
            item_type = "context"
            text = str(item or "").strip()

        if not text:
            continue

        escaped = _escape_html(text)

        if item_type == "added":
            row_class = "diff-added"
            marker = "+"
        elif item_type == "deleted":
            row_class = "diff-removed"
            marker = "−"
        else:
            row_class = "diff-context"
            marker = "•"

        html_lines.append(
            f'<tr class="{row_class}"><td class="line-marker">{marker}</td>'
            f'<td><code>{escaped}</code></td></tr>'
        )

    if not html_lines:
        return f'<tr><td colspan="2" class="no-changes">{_escape_html(empty_message)}</td></tr>'

    return "\n".join(html_lines)


def _infer_change_kind(fragment: str) -> str:
    sample = str(fragment or "").lower()
    if "#e53935" in sample or "#ffebee" in sample or "line-through" in sample:
        return "deleted"
    if "#1e88e5" in sample or "#e3f2fd" in sample:
        return "replaced"
    return "added"


def _badge_label(kind: str) -> str:
    if kind == "deleted":
        return "-1"
    if kind == "replaced":
        return "MARK"
    return "+1"


def _decorate_page_copy_html(page_html: str) -> str:
    html = str(page_html or "")
    html = re.sub(
        r"<!-- DOC_AS_CODE_HIGHLIGHT_CLEANUP_START -->.*?<!-- DOC_AS_CODE_HIGHLIGHT_CLEANUP_END -->",
        "",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    def _decorate_img(match: re.Match) -> str:
        full = match.group(0)
        kind = _infer_change_kind(full)
        label = _badge_label(kind)
        return f"<span class='dac-badge-wrap dac-{kind}'><span class='dac-badge dac-{kind}'>{label}</span>{full}</span>"

    html = re.sub(
        r"<img\b[^>]*data-dac=['\"]hl['\"][^>]*?/?>",
        _decorate_img,
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    def _decorate_tr(match: re.Match) -> str:
        opening = match.group(1)
        inner = match.group(2)
        closing = match.group(3)
        kind = _infer_change_kind(match.group(0))
        label = _badge_label(kind)

        def _inject_into_first_cell(cell_match: re.Match) -> str:
            tag = cell_match.group(1)
            attrs = cell_match.group(2)
            content = cell_match.group(3)
            badge = f"<span class='dac-inline-badge dac-{kind}'>{label}</span>"
            return f"<{tag}{attrs}>{badge}{content}</{tag}>"

        updated_inner, count = re.subn(
            r"<((?:td|th))\b([^>]*)>(.*?)</\1>",
            _inject_into_first_cell,
            inner,
            count=1,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if count == 0:
            updated_inner = f"<td><span class='dac-inline-badge dac-{kind}'>{label}</span></td>{inner}"
        return f"{opening}{updated_inner}{closing}"

    html = re.sub(
        r"(<tr\b[^>]*data-dac=['\"]hl['\"][^>]*>)(.*?)(</tr>)",
        _decorate_tr,
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    def _decorate_block(match: re.Match) -> str:
        tag = match.group(1)
        attrs = match.group(2)
        inner = match.group(3)
        if tag.lower() == "tr":
            return match.group(0)
        kind = _infer_change_kind(match.group(0))
        label = _badge_label(kind)
        return f"<{tag}{attrs}><span class='dac-badge dac-{kind}'>{label}</span>{inner}</{tag}>"

    html = re.sub(
        r"<([a-zA-Z0-9:_-]+)\b([^>]*data-dac=['\"]hl['\"][^>]*)>(.*?)</\1>",
        _decorate_block,
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    return html


def _render_preview_stats(counts: Dict[str, Any]) -> str:
    counts = counts or {}
    return (
        "<div class='preview-stats'>"
        f"<span class='preview-chip preview-added'>+1 × {int(counts.get('added') or 0)}</span>"
        f"<span class='preview-chip preview-deleted'>-1 × {int(counts.get('deleted') or 0)}</span>"
        f"<span class='preview-chip preview-replaced'>MARK × {int(counts.get('replaced') or 0)}</span>"
        "</div>"
    )


def _build_page_copy_sections(result_data: Dict[str, Any]) -> str:
    preview_payload = result_data.get("page_copy_preview") or {}
    if not preview_payload:
        return ""

    sections: List[str] = []
    for variant_name in preview_payload.get("variants") or []:
        variant = preview_payload.get(variant_name) or {}
        raw_html = str(variant.get("html") or "").strip()
        if not raw_html:
            continue
        title = _escape_html(str(variant.get("title") or variant_name.replace("_", " ").title()))
        description = _escape_html(str(variant.get("description") or ""))
        counts_html = _render_preview_stats(variant.get("counts") or {})
        decorated_html = _decorate_page_copy_html(raw_html)
        sections.append(
            "<div class='diff-section page-copy-section'>"
            f"<div class='diff-header'>{title}</div>"
            f"<div class='page-copy-meta'><p>{description}</p>{counts_html}</div>"
            f"<div class='page-copy-canvas'>{decorated_html}</div>"
            "</div>"
        )
    return "\n".join(sections)


def _build_page_copy_document(result_data: Dict[str, Any]) -> str:
    sections = _build_page_copy_sections(result_data)
    if not sections:
        return ""

    page_title = _escape_html(str(result_data.get("page_title") or "Unknown Page"))
    page_id = _escape_html(str(result_data.get("page_id") or "unknown"))
    page_url = _escape_html(str(result_data.get("page_url") or "#"))

    return f"""<!DOCTYPE html>
<html lang=\"en\"><head><meta charset=\"UTF-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\"><title>Page Copy Preview - {page_title}</title>
<style>body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;margin:0;background:#f5f7fb;color:#223}}.container{{max-width:1500px;margin:0 auto;padding:24px}}.hero{{background:white;border-radius:12px;padding:24px;box-shadow:0 8px 24px rgba(0,0,0,.08);margin-bottom:24px}}.hero h1{{margin:0 0 8px 0;color:#1976d2}}.hero p{{margin:6px 0;color:#566}}.hero a{{display:inline-block;margin-top:12px;text-decoration:none;color:white;background:#1976d2;padding:10px 18px;border-radius:8px;font-weight:600}}.legend{{background:white;border-radius:12px;padding:18px 22px;margin-bottom:24px;box-shadow:0 8px 24px rgba(0,0,0,.06)}}.legend span{{display:inline-block;margin-right:18px;margin-bottom:8px}}.page-copy-section{{background:white;border-radius:12px;box-shadow:0 8px 24px rgba(0,0,0,.06);margin-bottom:26px;overflow:hidden}}.diff-header{{background:#eef4ff;color:#0d47a1;font-weight:700;padding:14px 18px;border-bottom:1px solid #dbe5ff}}.page-copy-meta{{padding:16px 18px 8px 18px;border-bottom:1px solid #eef1f7}}.page-copy-meta p{{margin:0 0 12px 0;color:#566}}.preview-stats{{display:flex;flex-wrap:wrap;gap:10px}}.preview-chip{{font-size:12px;font-weight:700;border-radius:999px;padding:6px 10px}}.preview-added{{background:#e8f5e9;color:#1b5e20}}.preview-deleted{{background:#ffebee;color:#b71c1c}}.preview-replaced{{background:#e3f2fd;color:#0d47a1}}.page-copy-canvas{{padding:18px;overflow:auto}}.page-copy-canvas table{{border-collapse:collapse;max-width:100%}}.page-copy-canvas td,.page-copy-canvas th{{border:1px solid #d9dee8;padding:6px 8px;vertical-align:top}}.dac-badge-wrap{{position:relative;display:inline-block}}.dac-badge,.dac-inline-badge{{display:inline-block;font-size:11px;line-height:1;font-weight:800;letter-spacing:.3px;border-radius:999px;padding:5px 8px;margin-right:8px;vertical-align:middle}}.dac-added{{background:#e8f5e9;color:#1b5e20}}.dac-deleted{{background:#ffebee;color:#b71c1c}}.dac-replaced{{background:#e3f2fd;color:#0d47a1}}</style></head>
<body><div class=\"container\"><div class=\"hero\"><h1>Rendered Page Copy Preview</h1><p><strong>Page:</strong> {page_title}</p><p><strong>Page ID:</strong> {page_id}</p><p>This file is a review copy of the page with visible change badges: <strong>+1</strong> for add, <strong>-1</strong> for delete, <strong>MARK</strong> for replace/update.</p><a href=\"{page_url}\" target=\"_blank\">Open live page</a></div><div class=\"legend\"><span><strong style=\"color:#1b5e20;\">+1</strong> Added / will be added</span><span><strong style=\"color:#b71c1c;\">-1</strong> Deleted / will be removed</span><span><strong style=\"color:#0d47a1;\">MARK</strong> Replaced / updated</span></div>{sections}</div></body></html>"""


def generate_html_report(result_data: Dict[str, Any], output_html_path: str) -> None:
    """
    Generate a beautiful HTML report from compare results.
    
    Args:
        result_data: Result dictionary from scdp_compare_guard.py
        output_html_path: Path where to save the HTML report
    """
    page_title = result_data.get("page_title", "Unknown Page")
    page_id = result_data.get("page_id", "unknown")
    heading = result_data.get("heading_matched", "Unknown Heading")
    page_url = result_data.get("page_url", "#")
    
    guard_status = result_data.get("guard", {}).get("status", "unknown")
    drift = result_data.get("guard", {}).get("drift", False)
    
    compare_data = result_data.get("compare", {})
    storage_compare = compare_data.get("storage", {})
    markdown_compare = compare_data.get("markdown", {})

    storage_summary = storage_compare.get("summary", {})
    markdown_summary = markdown_compare.get("summary", {})
    storage_diff = storage_compare.get("diff_lines", [])
    markdown_diff = markdown_compare.get("diff_lines", [])
    markdown_preview = markdown_compare.get("human_readable_preview")
    local_knows = result_data.get("local_knows_changes", {})
    since_last_publish = result_data.get("since_last_publish", {})
    baseline_available = bool(since_last_publish.get("baseline_available"))
    page_copy_sections = _build_page_copy_sections(result_data)
    
    # Determine status color
    if guard_status == "drift":
        status_color = "#d32f2f"  # Red
        status_bg = "#ffebee"
    elif guard_status == "clean":
        status_color = "#388e3c"  # Green
        status_bg = "#e8f5e9"
    elif guard_status == "no_marker":
        status_color = "#f57c00"  # Orange
        status_bg = "#fff3e0"
    else:
        status_color = "#666"
        status_bg = "#f5f5f5"
    
    storage_html = _colorize_diff_lines(storage_diff, style="normal")
    if markdown_preview is None:
        markdown_html = _colorize_diff_lines(markdown_diff, style="normal")
    else:
        markdown_html = _render_human_readable_preview(
            markdown_preview,
            "✓ No meaningful content differences in markdown comparison",
        )
    server_markdown_html = _colorize_diff_lines(
        ((since_last_publish.get("server_edits") or {}).get("markdown") or {}).get("diff_lines", []),
        style="server",
    )
    local_markdown_html = _colorize_diff_lines(
        ((since_last_publish.get("local_changes") or {}).get("markdown") or {}).get("diff_lines", []),
        style="normal",
    )
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SCDP Compare Report - {page_title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            color: #333;
            background: #f5f5f5;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        header {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        
        header h1 {{
            color: #1976d2;
            margin-bottom: 10px;
            font-size: 28px;
        }}
        
        header p {{
            color: #666;
            margin: 5px 0;
        }}
        
        .header-meta {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        
        .meta-item {{
            background: #f9f9f9;
            padding: 12px;
            border-radius: 4px;
            border-left: 4px solid #1976d2;
        }}
        
        .meta-label {{
            font-size: 12px;
            color: #999;
            text-transform: uppercase;
            font-weight: 600;
            margin-bottom: 5px;
        }}
        
        .meta-value {{
            font-size: 14px;
            color: #333;
            word-break: break-all;
        }}
        
        .status-badge {{
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: 600;
            color: white;
            background: {status_color};
            margin: 10px 0;
        }}
        
        .status-box {{
            background: {status_bg};
            border-left: 4px solid {status_color};
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
        }}
        
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}
        
        .summary-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .summary-card h3 {{
            color: #1976d2;
            margin-bottom: 15px;
            font-size: 16px;
        }}
        
        .stat {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }}
        
        .stat:last-child {{
            border-bottom: none;
        }}
        
        .stat-label {{
            color: #666;
        }}
        
        .stat-value {{
            font-weight: 600;
            color: #333;
        }}
        
        .added {{
            color: #388e3c;
        }}
        
        .removed {{
            color: #d32f2f;
        }}
        
        .net-positive {{
            color: #388e3c;
        }}
        
        .net-negative {{
            color: #d32f2f;
        }}
        
        .diff-section {{
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 30px;
            overflow: hidden;
        }}
        
        .diff-header {{
            background: #f5f5f5;
            padding: 15px 20px;
            border-bottom: 2px solid #ddd;
            font-weight: 600;
            color: #333;
        }}
        
        .diff-table {{
            width: 100%;
            border-collapse: collapse;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }}
        
        .diff-table code {{
            padding: 2px 4px;
            word-break: break-all;
            white-space: pre-wrap;
        }}
        
        .diff-added {{
            background: #e8f5e9;
        }}
        
        .diff-added code {{
            color: #1b5e20;
        }}
        
        .diff-scdp-edit {{
            background: #e3f2fd;
        }}
        
        .diff-scdp-edit code {{
            color: #0d47a1;
            font-weight: 500;
        }}
        
        .diff-removed {{
            background: #ffebee;
        }}
        
        .diff-removed code {{
            color: #b71c1c;
            text-decoration: line-through;
            text-decoration-color: #b71c1c;
            text-decoration-thickness: 2px;
        }}
        
        .diff-header {{
            background: #e3f2fd;
        }}
        
        .diff-header code {{
            color: #0d47a1;
            font-weight: 600;
        }}
        
        .diff-context {{
            background: #fafafa;
        }}
        
        .diff-context code {{
            color: #666;
        }}
        
        .hunk-header {{
            background: #e3f2fd;
            font-weight: 600;
        }}
        
        .hunk-header code {{
            color: #0d47a1;
        }}
        
        .line-marker {{
            width: 30px;
            text-align: center;
            color: #999;
            font-weight: 600;
            padding: 4px 8px;
        }}
        
        .diff-table td {{
            padding: 4px 8px;
            border-bottom: 1px solid #eee;
        }}
        
        .diff-table tr:hover {{
            background-color: rgba(0,0,0,0.02);
        }}
        
        .no-changes {{
            padding: 30px;
            text-align: center;
            color: #999;
            font-size: 16px;
        }}
        
        .local-knows {{
            background: #f5f5f5;
            padding: 15px;
            border-radius: 4px;
            margin-top: 15px;
            font-size: 13px;
        }}
        
        .local-knows .item {{
            padding: 5px 0;
        }}
        
        .local-knows .match {{
            color: #388e3c;
        }}
        
        .local-knows .mismatch {{
            color: #d32f2f;
        }}
        
        footer {{
            text-align: center;
            padding: 20px;
            color: #999;
            font-size: 12px;
            margin-top: 40px;
        }}
        
        .legend {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .legend-item {{
            display: inline-block;
            margin-right: 30px;
            margin-bottom: 10px;
        }}

        .notice-box {{
            background: #fff8e1;
            border-left: 4px solid #f9a825;
            padding: 14px 16px;
            border-radius: 4px;
            margin-bottom: 24px;
        }}
        
        .legend-color {{
            display: inline-block;
            width: 20px;
            height: 20px;
            border-radius: 3px;
            margin-right: 8px;
            vertical-align: middle;
        }}

        .page-copy-section {{ overflow: visible; }}
        .page-copy-meta {{ padding: 16px 20px 6px 20px; border-bottom: 1px solid #eef1f7; }}
        .page-copy-meta p {{ margin: 0 0 12px 0; color: #566; }}
        .preview-stats {{ display: flex; flex-wrap: wrap; gap: 10px; }}
        .preview-chip {{ font-size: 12px; font-weight: 700; border-radius: 999px; padding: 6px 10px; }}
        .preview-added {{ background: #e8f5e9; color: #1b5e20; }}
        .preview-deleted {{ background: #ffebee; color: #b71c1c; }}
        .preview-replaced {{ background: #e3f2fd; color: #0d47a1; }}
        .page-copy-canvas {{ padding: 20px; overflow: auto; background: #fff; }}
        .page-copy-canvas table {{ border-collapse: collapse; max-width: 100%; }}
        .page-copy-canvas td, .page-copy-canvas th {{ border: 1px solid #d9dee8; padding: 6px 8px; vertical-align: top; }}
        .dac-badge-wrap {{ position: relative; display: inline-block; }}
        .dac-badge, .dac-inline-badge {{ display: inline-block; font-size: 11px; line-height: 1; font-weight: 800; letter-spacing: 0.3px; border-radius: 999px; padding: 5px 8px; margin-right: 8px; vertical-align: middle; }}
        .dac-added {{ background: #e8f5e9; color: #1b5e20; }}
        .dac-deleted {{ background: #ffebee; color: #b71c1c; }}
        .dac-replaced {{ background: #e3f2fd; color: #0d47a1; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 SCDP Compare & Guard Report</h1>
            <p>Detailed comparison of PREVIOUS (live Confluence) vs CURRENT (local markdown)</p>
            
            <div class="header-meta">
                <div class="meta-item">
                    <div class="meta-label">Page Title</div>
                    <div class="meta-value">{_escape_html(page_title)}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Page ID</div>
                    <div class="meta-value">{page_id}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Heading</div>
                    <div class="meta-value">{_escape_html(heading)}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Guard Status</div>
                    <div class="meta-value"><span class="status-badge">{guard_status.upper()}</span></div>
                </div>
            </div>
            
            {f'<div class="status-box">⚠️ <strong>Direct manual SCDP edits detected!</strong><br>Confluence page was edited after last Doc-as-Code publish marker.</div>' if drift else ''}
            
            <p style="margin-top: 20px; font-size: 12px; color: #999;">
                Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </p>
            <a href="{page_url}" target="_blank" style="
                display: inline-block;
                margin-top: 18px;
                padding: 10px 24px;
                background: #1976d2;
                color: white;
                text-decoration: none;
                border-radius: 6px;
                font-weight: 600;
                font-size: 14px;
                letter-spacing: 0.3px;
            ">🔗 Open Page in SCDP</a>
        </header>
        
        <div class="legend">
            <strong>Diff Legend:</strong><br>
            <div class="legend-item">
                <span class="legend-color" style="background: #e8f5e9;"></span>
                <strong style="color: #1b5e20;">Added (Green)</strong> = New in local markdown
            </div>
            <div class="legend-item">
                <span class="legend-color" style="background: #ffebee;"></span>
                <strong style="color: #b71c1c;">Removed (Red ~~strikethrough~~)</strong> = Was in Confluence, not in local
            </div>
            {'<div class="legend-item"><span class="legend-color" style="background: #e3f2fd;"></span><strong style="color: #0d47a1;">SCDP Manual Edit (Blue ✎)</strong> = Edited directly on server since last publish</div>' if drift else ''}
        </div>

        {f'<div class="notice-box"><strong>3-way compare note:</strong> {_escape_html(str(since_last_publish.get("message") or ""))}</div>' if drift else ''}
        
        <div class="summary-grid">
            <div class="summary-card">
                <h3>📝 Markdown Mode (Human-Readable)</h3>
                <div class="stat">
                    <span class="stat-label">Previous Lines</span>
                    <span class="stat-value">{markdown_summary.get('lines_previous', 0)}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Current Lines</span>
                    <span class="stat-value">{markdown_summary.get('lines_current', 0)}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Lines Added</span>
                    <span class="stat-value added">+{markdown_summary.get('lines_added', 0)}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Lines Removed</span>
                    <span class="stat-value removed">−{markdown_summary.get('lines_removed', 0)}</span>
                </div>
                <div class="stat" style="border-bottom: none; font-weight: 600; padding-top: 12px; border-top: 1px solid #eee;">
                    <span class="stat-label">Net Change</span>
                    <span class="stat-value {('net-positive' if markdown_summary.get('net_change', 0) >= 0 else 'net-negative')}">
                        {'+' if markdown_summary.get('net_change', 0) >= 0 else ''}{markdown_summary.get('net_change', 0)}
                    </span>
                </div>
                <div class="local-knows">
                    <div class="item">
                        Local matches live: 
                        <span class="{'match' if not markdown_summary.get('has_changes') else 'mismatch'}">
                            {'✓ Yes' if not markdown_summary.get('has_changes') else '✗ No (differences exist)'}
                        </span>
                    </div>
                </div>
            </div>
            
            <div class="summary-card">
                <h3>⚙️ Storage/HTML Mode (Technical)</h3>
                <div class="stat">
                    <span class="stat-label">Previous Lines</span>
                    <span class="stat-value">{storage_summary.get('lines_previous', 0)}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Current Lines</span>
                    <span class="stat-value">{storage_summary.get('lines_current', 0)}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Lines Added</span>
                    <span class="stat-value added">+{storage_summary.get('lines_added', 0)}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Lines Removed</span>
                    <span class="stat-value removed">−{storage_summary.get('lines_removed', 0)}</span>
                </div>
                <div class="stat" style="border-bottom: none; font-weight: 600; padding-top: 12px; border-top: 1px solid #eee;">
                    <span class="stat-label">Net Change</span>
                    <span class="stat-value {('net-positive' if storage_summary.get('net_change', 0) >= 0 else 'net-negative')}">
                        {'+' if storage_summary.get('net_change', 0) >= 0 else ''}{storage_summary.get('net_change', 0)}
                    </span>
                </div>
                <div class="local-knows">
                    <div class="item">
                        Local matches live: 
                        <span class="{'match' if not storage_summary.get('has_changes') else 'mismatch'}">
                            {'✓ Yes' if not storage_summary.get('has_changes') else '✗ No (differences exist)'}
                        </span>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- MARKDOWN DIFF -->
        <div class="diff-section">
            <div class="diff-header">
                Markdown Comparison (PREVIOUS → CURRENT)
            </div>
            {"<table class='diff-table'>" + (markdown_html if markdown_html else '<tr><td colspan="2" class="no-changes">✓ No changes in markdown comparison</td></tr>') + "</table>" if markdown_html or True else ""}
        </div>

        {f'''<div class="diff-section">
            <div class="diff-header">
                Manual SCDP Edits Since Last Publish (Blue)
            </div>
            {"<table class='diff-table'>" + (server_markdown_html if server_markdown_html else '<tr><td colspan="2" class="no-changes">No exact server-side edit breakdown available yet. Publish once with this tool to store baseline snapshot.</td></tr>') + "</table>"}
        </div>''' if drift else ''}

        {f'''<div class="diff-section">
            <div class="diff-header">
                Local Changes Since Last Publish (Green/Red)
            </div>
            {"<table class='diff-table'>" + (local_markdown_html if local_markdown_html else '<tr><td colspan="2" class="no-changes">No exact local change breakdown available yet. Publish once with this tool to store baseline snapshot.</td></tr>') + "</table>"}
        </div>''' if drift else ''}
        
        <!-- STORAGE DIFF -->
        <div class="diff-section">
            <div class="diff-header">
                Storage/HTML Comparison (PREVIOUS → CURRENT)
            </div>
            {"<table class='diff-table'>" + (storage_html if storage_html else '<tr><td colspan="2" class="no-changes">✓ No changes in storage comparison</td></tr>') + "</table>" if storage_html or True else ""}
        </div>

        {page_copy_sections}
        
        <footer>
            <p>SCDP Compare & Guard | Report generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </footer>
    </div>
</body>
</html>
"""
    
    os.makedirs(os.path.dirname(output_html_path), exist_ok=True)
    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"HTML report generated: {output_html_path}")

    page_copy_document = _build_page_copy_document(result_data)
    if page_copy_document:
        page_copy_output = output_html_path.replace(".html", "_page_copy.html")
        with open(page_copy_output, "w", encoding="utf-8") as f:
            f.write(page_copy_document)
        print(f"Page copy HTML generated: {page_copy_output}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate HTML report from SCDP compare JSON output")
    parser.add_argument("--json-file", required=True, help="Path to JSON result file from scdp_compare_guard.py")
    parser.add_argument("--output-html", default=None, help="Output HTML path (default: replace .json with .html)")
    args = parser.parse_args()
    
    if not os.path.exists(args.json_file):
        print(f"Error: JSON file not found: {args.json_file}")
        return
    
    with open(args.json_file, "r", encoding="utf-8") as f:
        result_data = json.load(f)
    
    output_html = args.output_html or args.json_file.replace(".json", ".html")
    generate_html_report(result_data, output_html)


if __name__ == "__main__":
    main()
