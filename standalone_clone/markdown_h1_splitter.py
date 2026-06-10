"""
Markdown H1 Splitter for Confluence (separate utility)
------------------------------------------------------
Creates one Confluence page per H1 heading only.
All internal headings/content (H2/H3/...) stay in the same page.

This file is intentionally separate so existing splitter behavior is unchanged.
"""

import argparse
import concurrent.futures
import hashlib
import html as html_module
import mimetypes
import os
import re
import sys
from typing import Any, List, Dict, Optional, Tuple
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

from confluence_h1_client_core import ConfluenceClient
from config import SPACE_KEY


class MarkdownH1Splitter:
    def __init__(self):
        self.client = ConfluenceClient()
        self.supported_image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg"}
        self.max_image_size_bytes = 25 * 1024 * 1024

    def _default_index_title(self, md_path: str) -> str:
        filename = os.path.splitext(os.path.basename(md_path))[0].strip()
        return f"{filename or 'Document'} - Index"

    def parse_sections(self, md_path: str, split_level: int = 1) -> List[Dict[str, str]]:
        # FLOW STAGE 1 (local file -> in-memory sections):
        # Read markdown from disk and split only on the selected heading level.
        # Everything between two same-level headings stays inside one section body.
        if split_level < 1 or split_level > 6:
            raise ValueError("split_level must be between 1 and 6")

        with open(md_path, "r", encoding="utf-8") as file:
            lines = file.read().splitlines()

        sections: List[Dict[str, str]] = []
        current_title = None
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
                    heading_level = len(heading_match.group(1))

                    # Split ONLY on the selected heading level; keep other levels inside same page.
                    if heading_level != split_level:
                        if current_title is not None:
                            current_lines.append(line)
                        else:
                            preface.append(line)
                        continue

                    if current_title is not None:
                        sections.append(
                            {
                                "title": current_title,
                                "markdown": "\n".join(current_lines).strip(),
                            }
                        )

                    current_title = heading_match.group(2).strip() or f"Section {len(sections) + 1}"
                    current_lines = []
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
                }
            )

        if preface and sections:
            sections[0]["markdown"] = ("\n".join(preface).strip() + "\n\n" + sections[0]["markdown"]).strip()

        if not sections:
            sections.append(
                {
                    "title": os.path.splitext(os.path.basename(md_path))[0] or "Document",
                    "markdown": "\n".join(preface).strip(),
                }
            )

        return sections

    def parse_h1_sections(self, md_path: str) -> List[Dict[str, str]]:
        return self.parse_sections(md_path, split_level=1)

    def _inline_to_html(self, text: str) -> str:
        escaped = html_module.escape(text)

        def safe_link_repl(match):
            label = match.group(1)
            raw_url = (match.group(2) or "").strip()
            if raw_url.startswith("&lt;") and raw_url.endswith("&gt;"):
                raw_url = raw_url[4:-4].strip()
            safe_url = html_module.escape(raw_url, quote=True)
            return f'<a href="{safe_url}">{label}</a>'

        escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
        escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
        escaped = re.sub(r"__([^_]+)__", r"<strong>\1</strong>", escaped)
        escaped = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", escaped)
        escaped = re.sub(r"_([^_]+)_", r"<em>\1</em>", escaped)
        escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", safe_link_repl, escaped)
        return escaped

    def _normalize_markdown_image_target(self, raw_target: str) -> str:
        target = (raw_target or "").strip()
        if target.startswith("<") and target.endswith(">"):
            target = target[1:-1].strip()

        while len(target) >= 2:
            if (target.startswith('"') and target.endswith('"')) or (target.startswith("'") and target.endswith("'")):
                target = target[1:-1].strip()
                continue
            break

        if ' "' in target and target.endswith('"'):
            target = target.rsplit(' "', 1)[0].strip()
        elif " '" in target and target.endswith("'"):
            target = target.rsplit(" '", 1)[0].strip()

        return target

    def _is_remote_image_target(self, target: str) -> bool:
        lowered = target.lower()
        return (
            lowered.startswith("http://")
            or lowered.startswith("https://")
            or lowered.startswith("data:")
            or lowered.startswith("/")
            or lowered.startswith("#")
        )

    def _extract_markdown_images(self, markdown_text: str) -> List[Dict[str, str]]:
        image_pattern = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
        images: List[Dict[str, str]] = []
        for match in image_pattern.finditer(markdown_text):
            alt_text = (match.group(1) or "").strip()
            raw_target = (match.group(2) or "").strip()
            normalized_target = self._normalize_markdown_image_target(raw_target)
            images.append(
                {
                    "alt": alt_text,
                    "raw": raw_target,
                    "target": normalized_target,
                }
            )
        return images

    def _resolve_local_image_path(self, source_dir: str, target: str) -> Optional[str]:
        if not target or self._is_remote_image_target(target):
            return None

        decoded_target = unquote(target)
        normalized_target = decoded_target.replace("\\", os.sep)

        if re.match(r"^[a-zA-Z]:[\\/]", normalized_target):
            candidate = normalized_target
        else:
            candidate = os.path.join(source_dir, normalized_target)

        candidate = os.path.normpath(candidate)
        if os.path.isfile(candidate):
            return candidate
        return None

    def _validate_local_image_for_upload(self, local_path: str) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        extension = os.path.splitext(local_path)[1].lower()
        size_bytes = 0
        try:
            size_bytes = int(os.path.getsize(local_path))
        except Exception:
            size_bytes = 0

        metadata = {
            "extension": extension,
            "size_bytes": size_bytes,
            "max_size_bytes": self.max_image_size_bytes,
        }

        if extension not in self.supported_image_extensions:
            return False, "unsupported_type", metadata

        if size_bytes > self.max_image_size_bytes:
            return False, "file_too_large", metadata

        return True, None, metadata

    def _build_image_html(self, alt_text: str, src: str) -> str:
        safe_alt = html_module.escape(alt_text or "")
        safe_src = html_module.escape(src or "", quote=True)
        return f'<img src="{safe_src}" alt="{safe_alt}" />'

    def _filename_from_image_target(self, target: str, content_type: Optional[str] = None) -> str:
        parsed = urlparse(target or "")
        base_name = os.path.basename(parsed.path or "")
        base_name = unquote(base_name).strip()

        if not base_name:
            digest = hashlib.sha1((target or "").encode("utf-8")).hexdigest()[:12]
            extension = ""
            if content_type:
                guessed_ext = mimetypes.guess_extension(content_type.split(";")[0].strip().lower())
                if guessed_ext:
                    extension = guessed_ext
            if not extension:
                extension = ".img"
            base_name = f"remote_image_{digest}{extension}"

        return base_name

    def _download_remote_image(self, target: str) -> Tuple[Optional[bytes], Optional[str], Optional[str]]:
        try:
            request = Request(target, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(request, timeout=30) as response:
                body = response.read()
                content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower() or None
                return body, content_type, None
        except Exception as exc:
            return None, None, str(exc)

    def _build_attachment_image_html(self, alt_text: str, filename: str) -> str:
        safe_alt = html_module.escape(alt_text or "", quote=True)
        safe_filename = html_module.escape(filename or "", quote=True)
        return f'<ac:image ac:alt="{safe_alt}"><ri:attachment ri:filename="{safe_filename}" /></ac:image>'

    def _line_with_images_to_html(self, line: str, image_src_map: Optional[Dict[str, Any]] = None) -> str:
        image_pattern = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
        html_parts: List[str] = []
        cursor = 0

        for match in image_pattern.finditer(line):
            start, end = match.span()
            prefix = line[cursor:start]
            if prefix:
                html_parts.append(self._inline_to_html(prefix))

            alt_text = (match.group(1) or "").strip()
            raw_target = (match.group(2) or "").strip()
            normalized_target = self._normalize_markdown_image_target(raw_target)

            resolved_src: Any = normalized_target
            if image_src_map:
                resolved_src = image_src_map.get(normalized_target, image_src_map.get(raw_target, normalized_target))
            if isinstance(resolved_src, dict) and resolved_src.get("type") == "attachment":
                html_parts.append(self._build_attachment_image_html(alt_text, str(resolved_src.get("filename", ""))))
            else:
                html_parts.append(self._build_image_html(alt_text, str(resolved_src)))
            cursor = end

        suffix = line[cursor:]
        if suffix:
            html_parts.append(self._inline_to_html(suffix))

        if not html_parts:
            return self._inline_to_html(line)

        return "".join(html_parts)

    def _parse_table_cells(self, line: str) -> List[str]:
        candidate = (line or "").strip()
        if "|" not in candidate:
            return []
        if candidate.startswith("|"):
            candidate = candidate[1:]
        if candidate.endswith("|"):
            candidate = candidate[:-1]
        cells = [cell.strip() for cell in candidate.split("|")]
        if not cells or all(cell == "" for cell in cells):
            return []
        return cells

    def _is_table_divider_cell(self, cell: str) -> bool:
        return bool(re.match(r"^:?-{3,}:?$", (cell or "").strip()))

    def markdown_to_html(self, markdown_text: str, image_src_map: Optional[Dict[str, str]] = None) -> str:
        if not markdown_text.strip():
            return "<p></p>"

        lines = markdown_text.split("\n")
        result: List[str] = []
        in_ul = False
        in_ol = False
        in_code = False

        def close_lists():
            nonlocal in_ul, in_ol
            if in_ul:
                result.append("</ul>")
                in_ul = False
            if in_ol:
                result.append("</ol>")
                in_ol = False

        # Supported AC macro shorthand tags used in SDD markdown files
        _ac_open_re = re.compile(
            r"^\s*<(info|note|warning|tip)(?:\s[^>]*)?>(.*)$", re.IGNORECASE
        )
        _ac_close_re = re.compile(r"^\s*</(info|note|warning|tip)\s*>", re.IGNORECASE)

        i = 0
        while i < len(lines):
            line = lines[i]

            # Convert <info>/<note>/<warning>/<tip> shorthand to AC structured macros.
            ac_open_m = _ac_open_re.match(line)
            if ac_open_m and not in_code:
                close_lists()
                macro_name = ac_open_m.group(1).lower()
                first_line_content = ac_open_m.group(2)
                body_lines: List[str] = []
                if first_line_content.strip():
                    body_lines.append(first_line_content)
                i += 1
                while i < len(lines):
                    inner = lines[i]
                    if _ac_close_re.match(inner):
                        i += 1
                        break
                    body_lines.append(inner)
                    i += 1
                body_md = "\n".join(body_lines).strip()
                inner_html = self.markdown_to_html(body_md, image_src_map=image_src_map) if body_md else "<p></p>"
                result.append(
                    f'<ac:structured-macro ac:name="{html_module.escape(macro_name)}" ac:schema-version="1">'
                    f"<ac:rich-text-body>{inner_html}</ac:rich-text-body>"
                    f"</ac:structured-macro>"
                )
                continue

            if re.match(r"^\s*```", line):
                close_lists()
                if in_code:
                    result.append("</code></pre>")
                    in_code = False
                else:
                    result.append("<pre><code>")
                    in_code = True
                i += 1
                continue

            if in_code:
                result.append(html_module.escape(line))
                i += 1
                continue

            if i + 1 < len(lines):
                header_cells = self._parse_table_cells(line)
                divider_cells = self._parse_table_cells(lines[i + 1])
                if (
                    header_cells
                    and divider_cells
                    and len(header_cells) == len(divider_cells)
                    and all(self._is_table_divider_cell(cell) for cell in divider_cells)
                ):
                    close_lists()
                    result.append("<table>")
                    header_html = "".join(
                        f"<th>{self._line_with_images_to_html(cell, image_src_map=image_src_map)}</th>"
                        for cell in header_cells
                    )
                    result.append(f"<thead><tr>{header_html}</tr></thead>")
                    result.append("<tbody>")

                    i += 2
                    while i < len(lines):
                        row_line = lines[i]
                        if not row_line.strip():
                            break

                        row_cells = self._parse_table_cells(row_line)
                        if not row_cells or len(row_cells) != len(header_cells):
                            break
                        if all(self._is_table_divider_cell(cell) for cell in row_cells):
                            i += 1
                            continue

                        row_html = "".join(
                            f"<td>{self._line_with_images_to_html(cell, image_src_map=image_src_map)}</td>"
                            for cell in row_cells
                        )
                        result.append(f"<tr>{row_html}</tr>")
                        i += 1

                    result.append("</tbody></table>")
                    continue

            h = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
            if h:
                close_lists()
                level = len(h.group(1))
                title = self._line_with_images_to_html(h.group(2).strip(), image_src_map=image_src_map)
                result.append(f"<h{level}>{title}</h{level}>")
                i += 1
                continue

            if re.match(r"^\s*[\*\-\+]\s+", line):
                if in_ol:
                    result.append("</ol>")
                    in_ol = False
                if not in_ul:
                    result.append("<ul>")
                    in_ul = True
                item = re.sub(r"^\s*[\*\-\+]\s+", "", line)
                result.append(f"<li>{self._line_with_images_to_html(item, image_src_map=image_src_map)}</li>")
                i += 1
                continue

            if re.match(r"^\s*\d+\.\s+", line):
                if in_ul:
                    result.append("</ul>")
                    in_ul = False
                if not in_ol:
                    result.append("<ol>")
                    in_ol = True
                item = re.sub(r"^\s*\d+\.\s+", "", line)
                result.append(f"<li>{self._line_with_images_to_html(item, image_src_map=image_src_map)}</li>")
                i += 1
                continue

            close_lists()
            if line.strip():
                result.append(f"<p>{self._line_with_images_to_html(line, image_src_map=image_src_map)}</p>")
            i += 1

        close_lists()
        if in_code:
            result.append("</code></pre>")

        return "\n".join(result)

    def build_index_html(self, pages: List[Dict[str, str]], heading: str) -> str:
        items = [f'<li><a href="{html_module.escape(p["url"], quote=True)}">{html_module.escape(p["title"])}</a></li>' for p in pages]
        return "\n".join(
            [
                # f"<h1>{html_module.escape(heading)}</h1>",
                # "<p>Click a section to open that page.</p>",
                "<h2>Index</h2>",
                "<ul>",
                *items,
                "</ul>",
            ]
        )

    def _upload_single_h1_section(self, section: Dict[str, str], upload_root: str, space_key: str, source_dir: str):
        # FLOW STAGE 2 (section -> server page):
        # Convert one section to Confluence storage HTML and upsert that page.
        worker_client = ConfluenceClient()
        image_src_map: Dict[str, str] = {}

        content_html = self.markdown_to_html(section["markdown"], image_src_map=image_src_map)
        page, action = worker_client.create_or_update_page(
            title=section["title"],
            content=content_html,
            parent_id=upload_root,
            space_key=space_key,
            fast_update=True,
        )

        if not page:
            return (page, action, 0, 0, [], [])

        images = self._extract_markdown_images(section["markdown"])
        local_targets: Dict[str, str] = {}
        remote_targets: Dict[str, str] = {}
        unresolved_targets: List[str] = []
        image_precheck_warnings: List[Dict[str, Any]] = []
        unresolved_seen = set()
        skipped_seen = set()
        for image in images:
            target = image["target"]
            if target in local_targets or target in remote_targets:
                continue

            if self._is_remote_image_target(target):
                lowered = (target or "").lower()
                if lowered.startswith("http://") or lowered.startswith("https://"):
                    remote_targets[target] = target
                continue

            local_path = self._resolve_local_image_path(source_dir, target)
            if local_path:
                is_valid, reason, metadata = self._validate_local_image_for_upload(local_path)
                if is_valid:
                    local_targets[target] = local_path
                elif target not in skipped_seen:
                    skipped_seen.add(target)
                    image_precheck_warnings.append(
                        {
                            "target": target,
                            "path": local_path,
                            "reason": reason,
                            "extension": metadata.get("extension", ""),
                            "size_bytes": int(metadata.get("size_bytes", 0) or 0),
                            "max_size_bytes": int(metadata.get("max_size_bytes", 0) or 0),
                        }
                    )
            elif target and (not self._is_remote_image_target(target)) and target not in unresolved_seen:
                unresolved_seen.add(target)
                unresolved_targets.append(target)

        if not local_targets and not remote_targets:
            return (page, action, 0, 0, unresolved_targets, image_precheck_warnings)

        page_id = str(page.get("id"))
        attachments_uploaded = 0
        attachments_unchanged = 0
        for target, local_path in local_targets.items():
            filename = os.path.basename(local_path)
            content_type, _ = mimetypes.guess_type(local_path)
            if not content_type:
                content_type = "application/octet-stream"

            try:
                with open(local_path, "rb") as image_file:
                    file_bytes = image_file.read()
            except Exception as exc:
                print(f"⚠️ Could not read image '{local_path}' for page '{section['title']}': {exc}")
                continue

            upload_result = worker_client.upload_attachment(
                page_id=page_id,
                filename=filename,
                file_bytes=file_bytes,
                content_type=content_type,
            )
            if not upload_result:
                print(f"⚠️ Failed to upload image '{filename}' for page '{section['title']}'")
                continue

            status = str(upload_result.get("status", "")).lower() if isinstance(upload_result, dict) else ""
            if status == "unchanged":
                attachments_unchanged += 1
            else:
                attachments_uploaded += 1

            image_src_map[target] = {"type": "attachment", "filename": filename}

        for target in remote_targets:
            file_bytes, remote_content_type, download_error = self._download_remote_image(target)
            if not file_bytes:
                image_precheck_warnings.append(
                    {
                        "target": target,
                        "path": target,
                        "reason": "remote_download_failed",
                        "extension": "",
                        "size_bytes": 0,
                        "max_size_bytes": int(self.max_image_size_bytes),
                        "detail": download_error or "download failed",
                    }
                )
                continue

            if len(file_bytes) > self.max_image_size_bytes:
                image_precheck_warnings.append(
                    {
                        "target": target,
                        "path": target,
                        "reason": "file_too_large",
                        "extension": "",
                        "size_bytes": len(file_bytes),
                        "max_size_bytes": int(self.max_image_size_bytes),
                    }
                )
                continue

            filename = self._filename_from_image_target(target, content_type=remote_content_type)
            content_type = remote_content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
            extension = os.path.splitext(filename)[1].lower()
            if extension and extension not in self.supported_image_extensions:
                image_precheck_warnings.append(
                    {
                        "target": target,
                        "path": target,
                        "reason": "unsupported_type",
                        "extension": extension,
                        "size_bytes": len(file_bytes),
                        "max_size_bytes": int(self.max_image_size_bytes),
                    }
                )
                continue

            upload_result = worker_client.upload_attachment(
                page_id=page_id,
                filename=filename,
                file_bytes=file_bytes,
                content_type=content_type,
            )
            if not upload_result:
                image_precheck_warnings.append(
                    {
                        "target": target,
                        "path": target,
                        "reason": "remote_upload_failed",
                        "extension": extension,
                        "size_bytes": len(file_bytes),
                        "max_size_bytes": int(self.max_image_size_bytes),
                    }
                )
                continue

            status = str(upload_result.get("status", "")).lower() if isinstance(upload_result, dict) else ""
            if status == "unchanged":
                attachments_unchanged += 1
            else:
                attachments_uploaded += 1

            image_src_map[target] = {"type": "attachment", "filename": filename}

        if image_src_map:
            # If local images were uploaded as attachments, re-render HTML so
            # markdown image targets now point to Confluence attachment URLs.
            final_html = self.markdown_to_html(section["markdown"], image_src_map=image_src_map)
            if final_html != content_html:
                updated_page, updated_action = worker_client.create_or_update_page(
                    title=section["title"],
                    content=final_html,
                    parent_id=upload_root,
                    space_key=space_key,
                    existing_page=page,
                    fast_update=True,
                )
                if updated_page:
                    return (
                        updated_page,
                        updated_action,
                        attachments_uploaded,
                        attachments_unchanged,
                        unresolved_targets,
                        image_precheck_warnings,
                    )

        return (page, action, attachments_uploaded, attachments_unchanged, unresolved_targets, image_precheck_warnings)

    def _delete_descendant_pages(self, client: ConfluenceClient, page_id: str) -> int:
        deleted_count = 0
        children = client.list_child_pages(page_id)
        for child in children:
            child_id = str(child.get("id"))
            deleted_count += self._delete_descendant_pages(client, child_id)
            if client.delete_page(child_id, suppress_not_found=True):
                deleted_count += 1
        return deleted_count

    def _prune_children_for_page(self, page: Dict[str, str]) -> int:
        if not page or not page.get("id"):
            return 0
        worker_client = ConfluenceClient()
        return self._delete_descendant_pages(worker_client, str(page["id"]))

    def _prune_children_for_page_safe(self, page: Dict[str, str], title: str) -> Tuple[int, Optional[str]]:
        try:
            return self._prune_children_for_page(page), None
        except Exception as exc:
            return 0, str(exc)

    def split_and_upload_h1(
        self,
        md_path: str,
        root_page_id: str,
        space_key: str = None,
        create_index: bool = True,
        index_title: str = None,
        index_as_root: bool = True,
        prune_children: bool = False,
        split_level: int = 1,
        preview_only: bool = False,
        max_workers: Optional[int] = None,
    ):
        # FLOW STAGE 0 (CLI input -> pipeline setup):
        # - validate path and options
        # - parse markdown into selected-level sections
        # - optionally create index page as upload root
        if not os.path.exists(md_path):
            print(f"❌ File not found: {md_path}")
            return None

        if space_key is None:
            space_key = SPACE_KEY

        sections = self.parse_sections(md_path, split_level=split_level)
        source_dir = os.path.dirname(os.path.abspath(md_path))
        print(f"📄 H{split_level} sections found: {len(sections)}")
        for section in sections:
            print(f"  - {section['title']}")

        if preview_only:
            print("\n👁️ Preview mode complete. No changes made.")
            return sections

        upload_root = root_page_id
        final_index_title = index_title or self._default_index_title(md_path)

        if create_index and index_as_root and root_page_id:
            bootstrap = "<p>Preparing index...</p>"
            index_page, _ = self.client.create_or_update_page(
                title=final_index_title,
                content=bootstrap,
                parent_id=root_page_id,
                space_key=space_key,
            )
            if index_page:
                upload_root = str(index_page["id"])
                print(f"📌 Using index page as hierarchy root: {upload_root}")

        worker_count = max_workers
        if worker_count is None:
            worker_count = min(10, max(1, len(sections)))
        else:
            worker_count = max(1, min(int(worker_count), len(sections) if sections else 1))

        print(f"⚙️ Upload workers: {worker_count}")

        created = []
        upload_results = [None] * len(sections)

        with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
            # FLOW STAGE 3 (parallel upload):
            # Each section is uploaded independently for faster large-document runs.
            future_to_index = {
                executor.submit(self._upload_single_h1_section, section, upload_root, space_key, source_dir): idx
                for idx, section in enumerate(sections)
            }

            for future in concurrent.futures.as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    future_result = future.result()
                    if isinstance(future_result, tuple) and len(future_result) == 6:
                        (
                            page,
                            action,
                            attachments_uploaded,
                            attachments_unchanged,
                            unresolved_images,
                            image_precheck_warnings,
                        ) = future_result
                    elif isinstance(future_result, tuple) and len(future_result) == 5:
                        page, action, attachments_uploaded, attachments_unchanged, unresolved_images = future_result
                        image_precheck_warnings = []
                    elif isinstance(future_result, tuple) and len(future_result) == 4:
                        page, action, attachments_uploaded, attachments_unchanged = future_result
                        unresolved_images = []
                        image_precheck_warnings = []
                    else:
                        page, action = future_result
                        attachments_uploaded, attachments_unchanged, unresolved_images, image_precheck_warnings = 0, 0, [], []
                    upload_results[idx] = (
                        page,
                        action,
                        attachments_uploaded,
                        attachments_unchanged,
                        unresolved_images,
                        image_precheck_warnings,
                    )
                except Exception as exc:
                    upload_results[idx] = (None, f"error: {exc}", 0, 0, [], [])

        prune_counts: Dict[int, int] = {}
        prune_errors: Dict[int, str] = {}
        if prune_children:
            prune_candidates = []
            for idx, section in enumerate(sections):
                page, action, _, _, _, _ = upload_results[idx] if upload_results[idx] else (None, "error", 0, 0, [], [])
                if page and action != "created":
                    prune_candidates.append((idx, page, section["title"]))

            if prune_candidates:
                cleanup_workers = min(4, max(1, worker_count), len(prune_candidates))
                print(f"⚙️ Cleanup workers: {cleanup_workers}")
                with concurrent.futures.ThreadPoolExecutor(max_workers=cleanup_workers) as cleanup_executor:
                    future_to_idx = {
                        cleanup_executor.submit(self._prune_children_for_page_safe, page, title): idx
                        for idx, page, title in prune_candidates
                    }
                    for future in concurrent.futures.as_completed(future_to_idx):
                        idx = future_to_idx[future]
                        try:
                            pruned_count, error_text = future.result()
                            prune_counts[idx] = pruned_count
                            if error_text:
                                prune_errors[idx] = error_text
                        except Exception as exc:
                            prune_counts[idx] = 0
                            prune_errors[idx] = str(exc)

        for idx, section in enumerate(sections):
            # FLOW STAGE 4 (server result -> CLI feedback):
            # Collect per-page action and optionally prune legacy child hierarchy.
            page, action, attachments_uploaded, attachments_unchanged, unresolved_images, image_precheck_warnings = upload_results[idx] if upload_results[idx] else (None, "error", 0, 0, [], [])
            if page:
                pruned_count = 0
                if prune_children:
                    pruned_count = prune_counts.get(idx, 0)
                page_url = f"https://scdp-dev.cisco.com/conf{page['_links']['webui']}"
                created.append(
                    {
                        "title": section["title"],
                        "url": page_url,
                        "action": action,
                        "attachments_uploaded": attachments_uploaded,
                        "attachments_unchanged": attachments_unchanged,
                        "unresolved_images": unresolved_images,
                        "image_precheck_warnings": image_precheck_warnings,
                    }
                )
                icon = "✅" if action == "created" else "🔄"
                print(f"{icon} {section['title']} -> {page_url}")
                if attachments_uploaded or attachments_unchanged:
                    print(
                        f"   📎 Attachments uploaded: {attachments_uploaded}"
                        + (f" (unchanged: {attachments_unchanged})" if attachments_unchanged else "")
                    )
                if unresolved_images:
                    print(f"   ⚠️ Unresolved local images: {len(unresolved_images)}")
                if image_precheck_warnings:
                    print(f"   ⚠️ Image precheck warnings: {len(image_precheck_warnings)}")
                if prune_children:
                    print(f"   🧹 Removed child pages: {pruned_count}")
                    if idx in prune_errors:
                        print(f"   ⚠️ Child-page cleanup failed: {prune_errors[idx]}")
            else:
                print(f"❌ Failed: {section['title']} ({action})")

        if create_index and created and root_page_id:
            # FLOW STAGE 5 (final navigation page):
            # Update index content with clickable links to uploaded pages.
            index_html = self.build_index_html(created, final_index_title)
            index_page, action = self.client.create_or_update_page(
                title=final_index_title,
                content=index_html,
                parent_id=root_page_id,
                space_key=space_key,
            )
            if index_page:
                index_url = f"https://scdp-dev.cisco.com/conf{index_page['_links']['webui']}"
                print(f"\n📚 Index page {action}: {index_url}")

        print(f"\n✅ H{split_level} markdown upload complete: {len(created)} pages")
        return created


def main():
    # CLI FLOW:
    # 1) Parse command arguments
    # 2) Normalize compatibility args (build-tree-fixed / --parent-id)
    # 3) Run preview or upload pipeline
    parser = argparse.ArgumentParser(description="Split Markdown by selected heading level and upload to Confluence")
    parser.add_argument("md_path", help="Path to markdown file")
    parser.add_argument("parent_page_id", nargs="?", help="Confluence parent page ID")
    parser.add_argument("--parent-id", dest="parent_id", default=None, help="Alias for parent_page_id")
    parser.add_argument("--space-key", default=SPACE_KEY, help="Confluence space key")
    parser.add_argument("--preview", action="store_true", help="Preview only, no upload")
    parser.add_argument("--yes", action="store_true", help="Run without confirmation prompt")
    parser.add_argument("--index-title", default=None, help="Custom index page title")
    parser.add_argument("--no-index", action="store_true", help="Do not create index page")
    parser.add_argument(
        "--index-as-root",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Create H1 pages under the index page (default: on). Use --no-index-as-root for flat upload.",
    )
    parser.add_argument(
        "--prune-children",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Delete existing descendant child pages under each split page after upload (default: off). Enable only for one-time cleanup.",
    )
    parser.add_argument(
        "--split-level",
        type=int,
        choices=range(1, 7),
        default=1,
        help="Heading level to split by (1-6). Example: 2 means split by ## headings.",
    )
    parser.add_argument("--workers", type=int, default=None, help="Parallel workers for H1 page upload")
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Fast mode for larger markdown files (uses higher worker count when --workers is not set).",
    )

    cli_args = sys.argv[1:]
    if cli_args and cli_args[0].strip().lower() == "build-tree-fixed":
        cli_args = cli_args[1:]

    args = parser.parse_args(cli_args)

    if args.parent_page_id is None and args.parent_id is not None:
        args.parent_page_id = args.parent_id

    if not args.parent_page_id:
        parser.error("parent_page_id is required (positional or --parent-id).")

    if args.fast and args.workers is None:
        args.workers = 10

    splitter = MarkdownH1Splitter()

    if args.preview:
        splitter.split_and_upload_h1(
            md_path=args.md_path,
            root_page_id=args.parent_page_id,
            space_key=args.space_key,
            create_index=not args.no_index,
            index_title=args.index_title,
            index_as_root=args.index_as_root,
            prune_children=args.prune_children,
            split_level=args.split_level,
            preview_only=True,
            max_workers=args.workers,
        )
        return

    if not args.yes:
        confirm = input(
            f"\n⚠️  This will create/update H1 pages in Confluence space '{args.space_key}' under '{args.parent_page_id}'.\n   Continue? (y/n): "
        )
        if confirm.strip().lower() not in {"y", "yes"}:
            print("Cancelled.")
            return

    splitter.split_and_upload_h1(
        md_path=args.md_path,
        root_page_id=args.parent_page_id,
        space_key=args.space_key,
        create_index=not args.no_index,
        index_title=args.index_title,
        index_as_root=args.index_as_root,
        prune_children=args.prune_children,
        split_level=args.split_level,
        preview_only=False,
        max_workers=args.workers,
    )


if __name__ == "__main__":
    main()
