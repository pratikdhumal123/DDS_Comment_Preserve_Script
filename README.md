# DDS Comment-Preserving Overwrite (Isolated Package)

This folder now contains a bundled standalone clone in [standalone_clone](standalone_clone), so day-to-day runs no longer need runtime files from outside this folder.

It provides a wrapper flow to support your ask:
- overwrite content from Doc Engine to SCDP page,
- capture inline comments before and after,
- produce a preservation audit report,
- keep compare/diff behavior through the bundled `scdp_compare_guard.py` clone.

## What it does

`comment_preserve_publish.py` runs these steps:
1. Fetch inline comments from target page (pre-snapshot)
2. Run bundled `scdp_compare_guard.py` compare/apply
3. Fetch inline comments again (post-snapshot)
4. Generate JSON report with preserved/missing/new comments and guard summary

## Files generated

In `output/`:
- `<page>_<timestamp>_comments_before.json`
- `<page>_<timestamp>_comments_after.json`
- `<page>_<timestamp>_compare_guard.json`
- `<page>_<timestamp>_comment_preservation_report.json`

## Bundled standalone clone

[standalone_clone](standalone_clone) contains local copies of the runtime files that were previously loaded from outside this folder, including:
- `scdp_compare_guard.py`
- `confluence_client.py`
- `markdown_h1_splitter.py`
- `confluence_h1_client_core.py`
- `tools/h1_diff_before_push.py`
- support helper files and `config.py`

The wrapper now defaults `--project-root` and `--guard-script` to that bundled clone.
A local markdown copy is also available at [standalone_clone/input/sdd.md](standalone_clone/input/sdd.md).

## Key output fields

From final report:
- `comment_preservation.preserved_count`
- `comment_preservation.missing_count`
- `comment_preservation.missing_preview`
- `guard.markdown_summary`
- `guard.storage_summary`

## Prerequisites

- Python with `requests`
- Access to SCDP/Confluence REST API
- Credentials via CLI args or bundled `config.py`

## Note on true inline-comment retention

Confluence may auto-resolve inline comments when the exact anchor text is replaced.  
This package adds **safe audit + diff visibility + missing-comment detection** so teams can decide whether to proceed and quickly recover unresolved anchors.

For strict retention, next phase is section-scoped publish (only update changed blocks) to avoid touching unchanged anchored text.
