import argparse
import difflib
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import SPACE_KEY
from confluence_client import ConfluenceClient
from markdown_h1_splitter import MarkdownH1Splitter


# Shared Confluence content-property key used to remember the last trusted
# Doc-as-Code publish state for a page.
DEFAULT_MARKER_KEY = "docAsCode.lastPublishMarker"


def normalize_storage_html(html_text: str) -> str:
    # Normalize line endings + trailing whitespace so harmless formatting noise
    # does not create false diffs or false hash mismatches.
    text = (html_text or "").replace("\r\n", "\n").strip()
    lines = [line.rstrip() for line in text.split("\n")]
    return "\n".join(lines).strip()


def content_hash(text: str) -> str:
    # Hash is the core of direct-edit detection:
    # same normalized content => same hash, changed content => different hash.
    normalized = normalize_storage_html(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def normalize_markdown(markdown_text: str) -> str:
    # Same normalization idea as HTML normalization, but for plain markdown.
    # This keeps line-ending or trailing-space noise from looking like real edits.
    text = (markdown_text or "").replace("\r\n", "\n").strip()
    lines = [line.rstrip() for line in text.split("\n")]
    return "\n".join(lines).strip()


def strip_div_wrappers(text: str) -> str:
    # Optional cleanup helper for noisy wrapper-only diffs.
    # Some Confluence/rendering flows wrap content in <div> tags even when
    # business content is effectively the same.
    cleaned = text or ""
    cleaned = re.sub(r"<\s*/?\s*div\b[^>]*>", "", cleaned, flags=re.IGNORECASE)
    return cleaned


def contains_div_tag(text: str) -> bool:
    # Fast visibility check used in debug output / API response.
    # It does not change content; it only tells the user whether div tags exist.
    return bool(re.search(r"<\s*/?\s*div\b", text or "", flags=re.IGNORECASE))


def slugify(value: str) -> str:
    # Used only for filesystem-safe patch filenames when diff output is saved.
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", value.strip())
    return cleaned.strip("_") or "untitled"


def get_existing_page(
    client: ConfluenceClient,
    title: str,
    parent_page_id: str,
    space_key: str,
    allow_space_fallback: bool,
):
    # First try the strict parent-child lookup because split publish flow is
    # hierarchy-based. Optional space fallback supports spaces where titles are
    # unique beyond a single parent.
    existing = client.get_child_page_by_title(parent_page_id, title)
    if existing:
        return existing

    if allow_space_fallback:
        return client.get_page_by_title(title, space_key)

    return None


def build_diff(
    before_text: str,
    after_text: str,
    title: str,
    context: int,
    mode: str,
) -> List[str]:
    # Produce a unified diff in either markdown-view or storage-html-view.
    # This helper is reused by both CLI and FastAPI so both surfaces report
    # the same kind of diff output.
    if mode == "markdown":
        before = normalize_markdown(before_text).splitlines(keepends=True)
        after = normalize_markdown(after_text).splitlines(keepends=True)
        from_name = f"confluence-md:{title}"
        to_name = f"local-md:{title}"
    else:
        before = normalize_storage_html(before_text).splitlines(keepends=True)
        after = normalize_storage_html(after_text).splitlines(keepends=True)
        from_name = f"confluence-storage:{title}"
        to_name = f"local-storage:{title}"

    return list(
        difflib.unified_diff(
            before,
            after,
            fromfile=from_name,
            tofile=to_name,
            n=context,
            lineterm="",
        )
    )


def convert_storage_to_markdown(storage_html: str) -> str:
    # Used only for human-readable diff mode.
    # Publish itself still uses HTML/storage format when sending content back.
    try:
        from markdownify import markdownify as to_markdown
    except Exception as exc:
        raise RuntimeError(
            "markdown diff mode requires 'markdownify'. Install with: pip install markdownify"
        ) from exc
    return to_markdown(storage_html or "")


def maybe_prompt_for_update(title: str) -> bool:
    # Final human approval before pushing a content change.
    # This keeps CLI mode interactive and safe by default.
    answer = input(f"Approve update for '{title}'? (y/n): ").strip().lower()
    return answer in {"y", "yes"}


def maybe_prompt_for_override(title: str) -> bool:
    # Separate prompt for the risky path:
    # user is explicitly deciding to overwrite manual SCDP edits.
    answer = input(
        f"⚠️ Direct SCDP edits detected for '{title}'. Override SCDP changes and publish anyway? (y/n): "
    ).strip().lower()
    return answer in {"y", "yes"}


def get_page_marker(client: ConfluenceClient, page_id: str, marker_key: str) -> Optional[Dict[str, Any]]:
    # Marker is stored as a Confluence content property on the page.
    # We read it directly so we can compare current live content against the
    # last published Doc-as-Code snapshot.
    url = f"{client.base_url}/content/{page_id}/property/{marker_key}"
    # We use the client's auth strategies directly so this helper works with
    # cookie/bearer/basic auth the same way as the rest of the project.
    for index, strategy in enumerate(client.auth_strategies):
        headers = dict(client.base_headers)
        headers.update(strategy["headers"])
        headers["Accept"] = "application/json"

        response = requests.request(
            "GET",
            url,
            headers=headers,
            auth=strategy["auth"],
            timeout=30,
            allow_redirects=False,
        )

        # 404 here is normal for first-time pages: it simply means
        # no publish marker has been stored yet.
        if response.status_code == 404:
            return None

        if client._looks_like_auth_redirect(response) and index < len(client.auth_strategies) - 1:
            continue

        if response.status_code >= 400:
            print(
                f"Error while trying to get page property '{marker_key}' for {page_id}: "
                f"HTTP {response.status_code}"
            )
            preview = (response.text or "")[:300]
            if preview:
                print(preview)
            return None

        try:
            return response.json()
        except requests.exceptions.JSONDecodeError:
            print(
                f"Error while trying to get page property '{marker_key}' for {page_id}: "
                "response was not valid JSON"
            )
            return None

    return None


def upsert_page_marker(
    client: ConfluenceClient,
    page_id: str,
    marker_key: str,
    marker_value: Dict[str, Any],
) -> bool:
    # Upsert = update if marker already exists, otherwise create it.
    # This lets the first publish create a baseline and later publishes refresh it.
    existing = get_page_marker(client, page_id, marker_key)

    if existing:
        # Update existing marker version because Confluence content properties
        # are versioned resources just like pages.
        current_ver = ((existing.get("version") or {}).get("number") or 0)
        url = f"{client.base_url}/content/{page_id}/property/{marker_key}"
        payload = {
            "key": marker_key,
            "value": marker_value,
            "version": {"number": int(current_ver) + 1},
        }
        result = client._request_json(
            "PUT",
            url,
            f"update page property '{marker_key}' for {page_id}",
            json=payload,
        )
        return bool(result)

    # First-time publish path: create a new property on the page.
    url = f"{client.base_url}/content/{page_id}/property"
    payload = {
        "key": marker_key,
        "value": marker_value,
    }
    result = client._request_json(
        "POST",
        url,
        f"create page property '{marker_key}' for {page_id}",
        json=payload,
    )
    return bool(result)


def parse_marker_value(marker_obj: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    # Defensive parsing because Confluence property values may come back as a
    # dict or as a JSON string depending on server behavior.
    if not marker_obj:
        return None

    value = marker_obj.get("value")
    if isinstance(value, dict):
        return value

    # Some servers may serialize property values as JSON strings.
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return None

    return None


def build_publish_marker(title: str, body_html: str, page_version: Optional[int]) -> Dict[str, Any]:
    # Marker payload saved on the Confluence page.
    # FastAPI and CLI both use this exact shape.
    return {
        "published_content_hash": content_hash(body_html),
        "published_page_version": int(page_version) if page_version is not None else None,
        "published_at": datetime.now(timezone.utc).isoformat(),
        "published_by": os.getenv("DOC_AS_CODE_PUBLISHER", "doc-as-code"),
        "page_title": title,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Diff markdown Hx sections against existing Confluence pages before update"
    )
    parser.add_argument("md_path", help="Path to markdown file")
    parser.add_argument("parent_page_id", help="Confluence parent page id for split pages")
    parser.add_argument("--space-key", default=SPACE_KEY, help="Confluence space key")
    parser.add_argument(
        "--split-level",
        type=int,
        default=1,
        choices=range(1, 7),
        help="Heading level to split on (1-6)",
    )
    parser.add_argument("--heading-title", default=None, help="Only check this heading title")
    parser.add_argument("--context-lines", type=int, default=3, help="Unified diff context lines")
    parser.add_argument(
        "--diff-mode",
        choices=["storage", "markdown"],
        default="storage",
        help=(
            "storage: convert local markdown to storage HTML and compare with Confluence storage HTML; "
            "markdown: convert existing Confluence storage HTML to markdown and compare markdown"
        ),
    )
    parser.add_argument(
        "--ignore-div-wrappers",
        action="store_true",
        help="Strip <div>...</div> wrappers before diff to reduce wrapper-only noise",
    )
    parser.add_argument(
        "--show-div-check",
        action="store_true",
        help="Show whether existing/new content contains div tags",
    )
    parser.add_argument(
        "--allow-space-fallback",
        action="store_true",
        help="If not found under parent, also search by title in space",
    )
    parser.add_argument(
        "--show-unchanged",
        action="store_true",
        help="Print unchanged headings too",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional directory to save per-heading .patch files",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply updates after diff check (approval gated unless --yes)",
    )
    parser.add_argument("--yes", action="store_true", help="Skip prompts when --apply is used")
    parser.add_argument(
        "--create-missing",
        action="store_true",
        help="When --apply is used, create page if missing (default: skip missing)",
    )
    parser.add_argument(
        "--marker-key",
        default=DEFAULT_MARKER_KEY,
        help="Confluence page property key used to track last Doc-as-Code publish marker",
    )
    parser.add_argument(
        "--force-scdp-override",
        action="store_true",
        help="Publish even when direct edits are detected in SCDP since last Doc-as-Code publish marker",
    )

    args = parser.parse_args()

    if not os.path.exists(args.md_path):
        raise SystemExit(f"File not found: {args.md_path}")

    # Existing modules reused here:
    # - MarkdownH1Splitter: parses markdown into heading-based sections and renders HTML.
    # - ConfluenceClient: reads/writes live pages in SCDP/Confluence.
    splitter = MarkdownH1Splitter()
    client = ConfluenceClient()

    # Fail fast if parent page cannot be accessed. This avoids misleading
    # "missing page" output when the real issue is auth or wrong parent ID.
    parent_page = client.get_page(str(args.parent_page_id))
    if not parent_page:
        raise SystemExit(
            "Unable to access parent page. Aborting diff guard check to avoid false 'missing page' results. "
            "Verify auth in config.py (token/cookie/basic) and that parent_page_id is correct."
        )

    # Break the markdown document into the same heading-based sections that are
    # used for split publishing. This makes diff and publish decisions per page.
    sections = splitter.parse_sections(args.md_path, split_level=args.split_level)
    if args.heading_title:
        sections = [s for s in sections if (s.get("title", "").strip() == args.heading_title.strip())]

    if not sections:
        print("No matching sections found.")
        return

    if args.output_dir:
        os.makedirs(args.output_dir, exist_ok=True)

    summary: Dict[str, int] = {
        "total": len(sections),
        "missing": 0,
        "changed": 0,
        "unchanged": 0,
        "updated": 0,
        "created": 0,
        "skipped": 0,
        "failed": 0,
        "direct_edit_warnings": 0,
        "blocked_by_direct_edits": 0,
        "marker_updated": 0,
        "marker_failed": 0,
    }

    # Process each split section independently so one page can be checked,
    # blocked, updated, or skipped without hiding what happened to others.
    for section in sections:
        title = str(section.get("title", "")).strip() or "Untitled"
        section_markdown_body = section.get("markdown", "")

        # local_markdown is used only for markdown diff mode.
        # new_html is the actual content that would be published if apply happens.
        local_markdown = f"# {title}\n\n{section_markdown_body}".strip() + "\n"
        new_html = splitter.markdown_to_html(section_markdown_body, image_src_map={})

        # Resolve the target Confluence page for this heading.
        # Usually this is parent+title lookup, with optional space-wide fallback.
        existing = get_existing_page(
            client=client,
            title=title,
            parent_page_id=str(args.parent_page_id),
            space_key=str(args.space_key),
            allow_space_fallback=bool(args.allow_space_fallback),
        )

        if not existing:
            # Page does not exist yet. We can either report it as missing or,
            # if apply/create-missing are enabled, create it as a new page.
            summary["missing"] += 1
            print(f"🟡 MISSING: {title}")

            if args.apply and args.create_missing:
                if args.yes or maybe_prompt_for_update(title):
                    page, action = client.create_or_update_page(
                        title=title,
                        content=new_html,
                        parent_id=str(args.parent_page_id),
                        space_key=str(args.space_key),
                        existing_page=None,
                        fast_update=True,
                        allow_space_fallback=False,
                    )
                    if page:
                        if action == "created":
                            summary["created"] += 1
                        elif action == "updated":
                            summary["updated"] += 1
                        print(f"   ✅ {action.upper()}: {title}")

                        marker_page_id = str(page.get("id", "")).strip()
                        marker_page_version = ((page.get("version") or {}).get("number"))
                        if marker_page_id:
                            stored_page = client.get_page(marker_page_id) or page
                            stored_html = ((stored_page.get("body") or {}).get("storage") or {}).get("value", new_html)
                            stored_page_version = ((stored_page.get("version") or {}).get("number")) or marker_page_version
                            marker_ok = upsert_page_marker(
                                client,
                                marker_page_id,
                                str(args.marker_key),
                                build_publish_marker(title, stored_html, stored_page_version),
                            )
                            if marker_ok:
                                summary["marker_updated"] += 1
                            else:
                                summary["marker_failed"] += 1
                                print(f"   ⚠️ Marker update failed: {title}")
                    else:
                        summary["failed"] += 1
                        print(f"   ❌ FAILED create: {title}")
                else:
                    summary["skipped"] += 1
                    print(f"   ⏭️ Skipped by approval: {title}")
            continue

        page_id = str(existing.get("id"))
        # Fetch full page body/storage content because child-page lookup may not
        # include everything needed for diff/hash comparison.
        full_page = client.get_page(page_id) or existing
        existing_html = ((full_page.get("body") or {}).get("storage") or {}).get("value", "")

        # Direct-edit detection compares the current live page content with the
        # last recorded Doc-as-Code marker on that page.
        direct_edit_detected = False
        marker_info = get_page_marker(client, page_id, str(args.marker_key))
        marker_value = parse_marker_value(marker_info)
        if marker_value and marker_value.get("published_content_hash"):
            current_page_hash = content_hash(existing_html)
            if str(marker_value.get("published_content_hash")) != current_page_hash:
                direct_edit_detected = True
                summary["direct_edit_warnings"] += 1
                print(f"⚠️ DIRECT EDIT DETECTED: {title} (page_id={page_id})")
                print(
                    "   SCDP content changed since last Doc-as-Code publish marker. "
                    "Review before publish or use explicit override."
                )
        elif args.apply:
            print(f"ℹ️ No publish marker found: {title} (first guarded publish for this page)")

        if args.show_div_check:
            # Visibility-only diagnostic: lets the user know whether wrapper divs
            # are present before they decide how to interpret the diff.
            existing_has_div = contains_div_tag(existing_html)
            new_has_div = contains_div_tag(new_html)
            print(
                f"🔍 DIV CHECK: {title} | existing_div={existing_has_div} | new_div={new_has_div}"
            )

        compare_existing = existing_html
        compare_new = new_html

        if args.ignore_div_wrappers:
            # Optional normalization path for cases where outer div wrappers are
            # the only meaningful difference and user wants a cleaner diff.
            compare_existing = strip_div_wrappers(compare_existing)
            compare_new = strip_div_wrappers(compare_new)

        if args.diff_mode == "markdown":
            # Human-readable mode:
            # convert existing Confluence HTML back to markdown, then compare
            # with local markdown text.
            compare_existing = convert_storage_to_markdown(compare_existing)
            compare_new = local_markdown

        diff_lines = build_diff(
            compare_existing,
            compare_new,
            title=title,
            context=int(args.context_lines),
            mode=str(args.diff_mode),
        )

        if not diff_lines:
            # No content change means nothing to publish for this section.
            summary["unchanged"] += 1
            if args.show_unchanged:
                print(f"✅ UNCHANGED: {title}")
            continue

        summary["changed"] += 1
        print(f"\n📝 DIFF FOUND: {title} (page_id={page_id})")
        print("\n".join(diff_lines))

        if args.output_dir:
            patch_path = os.path.join(args.output_dir, f"{slugify(title)}.patch")
            with open(patch_path, "w", encoding="utf-8") as patch_file:
                patch_file.write("\n".join(diff_lines) + "\n")
            print(f"💾 Saved diff: {patch_path}")

        if args.apply:
            # Apply path starts only after a real diff was found.
            allow_update = True
            if direct_edit_detected and not args.force_scdp_override:
                # In safe mode we stop here unless user explicitly confirms
                # overwrite (interactive) or passes force override (non-interactive).
                if args.yes:
                    allow_update = False
                else:
                    allow_update = maybe_prompt_for_override(title)

                if not allow_update:
                    summary["blocked_by_direct_edits"] += 1
                    summary["skipped"] += 1
                    print(f"⛔ BLOCKED by direct-edit guard: {title}")
                    continue

            if args.yes or maybe_prompt_for_update(title):
                # Reuse existing create/update logic from ConfluenceClient so we
                # do not duplicate page-write behavior here.
                page, action = client.create_or_update_page(
                    title=title,
                    content=new_html,
                    parent_id=str(args.parent_page_id),
                    space_key=str(args.space_key),
                    existing_page=existing,
                    fast_update=True,
                    allow_space_fallback=False,
                )
                if page:
                    if action == "updated":
                        summary["updated"] += 1
                    elif action == "created":
                        summary["created"] += 1
                    print(f"✅ {action.upper()}: {title}")

                    marker_page_id = str(page.get("id", "")).strip()
                    marker_page_version = ((page.get("version") or {}).get("number"))
                    if marker_page_id:
                        # Re-read stored page content after publish so the marker
                        # uses the exact HTML Confluence saved, not only the
                        # pre-submit local HTML.
                        stored_page = client.get_page(marker_page_id) or page
                        stored_html = ((stored_page.get("body") or {}).get("storage") or {}).get("value", new_html)
                        stored_page_version = ((stored_page.get("version") or {}).get("number")) or marker_page_version
                        # Refresh page marker after successful publish so the
                        # next run compares against the newly published content.
                        marker_ok = upsert_page_marker(
                            client,
                            marker_page_id,
                            str(args.marker_key),
                            build_publish_marker(title, stored_html, stored_page_version),
                        )
                        if marker_ok:
                            summary["marker_updated"] += 1
                        else:
                            summary["marker_failed"] += 1
                            print(f"⚠️ Marker update failed: {title}")
                else:
                    summary["failed"] += 1
                    print(f"❌ FAILED update: {title}")
            else:
                summary["skipped"] += 1
                print(f"⏭️ Skipped by approval: {title}")

    # Final summary gives one compact report after all sections are processed.
    print("\n" + "=" * 80)
    print("DIFF SUMMARY")
    print("=" * 80)
    print(f"Total sections: {summary['total']}")
    print(f"Changed: {summary['changed']}")
    print(f"Unchanged: {summary['unchanged']}")
    print(f"Missing pages: {summary['missing']}")
    if args.apply:
        print(f"Updated: {summary['updated']}")
        print(f"Created: {summary['created']}")
        print(f"Skipped: {summary['skipped']}")
        print(f"Failed: {summary['failed']}")
        print(f"Direct-edit warnings: {summary['direct_edit_warnings']}")
        print(f"Blocked by direct-edit guard: {summary['blocked_by_direct_edits']}")
        print(f"Marker updated: {summary['marker_updated']}")
        print(f"Marker failed: {summary['marker_failed']}")


if __name__ == "__main__":
    main()
