# Project Flow Summary (Attach Ready)

## Short Description
This project provides a safe publish flow from local Markdown to Confluence, with focus on preserving active inline comments during page overwrite and giving clear before/after audit visibility.

## What We Need
- Python 3.12+
- Dependencies from `requirements.txt`
- Confluence page access (`base-url`, `page-id`)
- Local markdown source (`md-path`)
- One auth method: bearer token or username/token or session cookie

## What We Used
- Main orchestration script: `comment_preserve_publish.py`
- Compare and safety guard: `standalone_clone/scdp_compare_guard.py`
- Confluence REST APIs (page content, storage format, comments)
- Local standalone bundle in `standalone_clone/` to avoid external runtime dependencies
- Run artifacts in `output/` (JSON + HTML)

## End-to-End Flow
1. Fetch current page comments and create a **before snapshot**.
2. Run compare/guard checks to detect drift and require safe overwrite decision.
3. If approved, publish markdown content to the target Confluence page.
4. Re-inject inline comment markers for active comments when anchor text is still present.
5. Fetch comments again and create an **after snapshot**.
6. Build preservation metrics for active comments (preserved, missing, new, auto-resolved).
7. Save final artifacts for audit and team review.

## Outputs Generated
- `<page>_<timestamp>_comments_before.json`
- `<page>_<timestamp>_comments_after.json`
- `<page>_<timestamp>_compare_guard.json`
- `<page>_<timestamp>_compare_guard.html`
- `<page>_<timestamp>_comment_preservation_report.json`

## Highlights
- Safe publish with drift detection and overwrite guard
- Inline comment preservation using marker re-injection
- Clear reporting for verification and traceability
- Standalone execution with bundled runtime files

## Known Limitation
If anchor text is heavily changed or removed, some inline comments cannot be automatically re-attached and may require manual follow-up.

## Current Focus
- End-to-end validation on real pages
- Edge-case refinement for anchor matching and re-injection

## Ultra-Short Manager Summary (5 Bullets)
- We safely publish local Markdown updates to Confluence without blind overwrite.
- We take before/after comment snapshots to measure impact on active comments.
- We restore inline comment anchors after publish when anchor text still exists.
- We generate audit-ready JSON/HTML outputs for team review and traceability.
- If anchor text is heavily changed/removed, a small set of comments may need manual re-attachment.
