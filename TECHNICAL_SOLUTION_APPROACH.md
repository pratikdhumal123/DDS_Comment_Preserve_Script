# Technical Solution Approach

## Problem Statement
When publishing updated content to Confluence pages, inline comments attached to page content were being auto-resolved by Confluence because the inline anchor marker wrapper tags (`<ac:inline-comment-marker>`) were lost during the page storage update process. This resulted in loss of discussion context and required manual re-attachment or re-creation of comments by team members.

---

## Technical Solution Approach

### APIs Used

```
GET /rest/api/content/{pageId}?expand=children.comment,children.comment.body.storage,history,body.storage,version,space
├─ Purpose: Fetch current page comments and storage HTML format
├─ Returns: Comment metadata, status, anchor markers, and full page storage
└─ Used for: Before and after snapshots

PUT /rest/api/content/{pageId}
├─ Purpose: Update page storage with restored inline markers
├─ Payload: Storage HTML with re-injected <ac:inline-comment-marker ac:ref="UUID">text</ac:inline-comment-marker>
└─ Used for: Post-overwrite marker restoration
```

### Authentication Handling

```
Fallback Strategy (Attempt in order):
1. Bearer Token Authentication
   ├─ Header: Authorization: Bearer <access-token>
   └─ Use case: API-first, preferred for scripted access

2. Basic Authentication
   ├─ Header: Authorization: Basic base64(username:token)
   └─ Use case: Legacy systems, credential-based access

3. Session Cookie Authentication
   ├─ Header: Cookie: <session-cookie>
   └─ Use case: Web session fallback
```

### Comparison & Safety Logic

```
Pre-Overwrite Checks:
├─ Detect drift between local markdown and current page storage
├─ Identify manual online edits not reflected locally
├─ Compare markdown and storage format changes
└─ Require explicit override flag (--force-scdp-override --yes-override) to proceed if drift detected

Purpose: Prevent blind overwrite of unsynced page edits
```

### Comment Preservation Process

```
Step 1: Before Snapshot
├─ Fetch all comments for target page
├─ Filter to active/current status only (exclude resolved)
└─ Extract inline marker refs: <ac:inline-comment-marker ac:ref="UUID">anchor_text</ac:inline-comment-marker>

Step 2: Content Overwrite
├─ Run guard/compare validation
├─ Publish markdown content to page storage (via PUT API)
└─ Page storage updated; markers temporarily lost

Step 3: Anchor Re-injection
├─ For each active comment ref extracted in Step 1:
│  ├─ Search new storage for unchanged anchor text
│  ├─ If found: re-wrap with <ac:inline-comment-marker ac:ref="UUID">text</ac:inline-comment-marker>
│  └─ If not found: skip (text was modified/removed)
├─ Send follow-up PUT to restore markers
└─ Comments remain open and linked

Step 4: After Snapshot
├─ Fetch comments again post-restoration
├─ Compare with before snapshot
└─ Measure preserved, missing, new, and auto-resolved counts

Step 5: Report Generation
├─ Build delta metrics (active/preserved/missing/new/auto-resolved)
├─ Log comment preview for missing/auto-resolved
└─ Save JSON + HTML artifacts for audit
```

### Outputs Generated

```
Artifacts saved to output/:

1. <page>_<timestamp>_comments_before.json
   └─ All comments + active-only breakdown before update

2. <page>_<timestamp>_comments_after.json
   └─ All comments + active-only breakdown after update

3. <page>_<timestamp>_compare_guard.json
   └─ Drift detection, safe-to-publish flag, compare summary

4. <page>_<timestamp>_compare_guard.html
   └─ Visual side-by-side diff for manual review

5. <page>_<timestamp>_comment_preservation_report.json
   ├─ Preservation metrics (preserved_count, missing_count, etc.)
   ├─ Auto-resolved preview (which comments got auto-resolved + why)
   ├─ Anchor re-injection status
   └─ Recommendation for team action
```

---

## Key Metrics in Report

```json
{
  "comment_preservation": {
    "before_active_count": "N",              // Active comments before update
    "after_active_count": "N",               // Active comments after update
    "active_preserved_count": "N",           // Successfully preserved
    "active_missing_count": "N",             // Disappeared entirely
    "active_auto_resolved_count": "N",       // Were active, now resolved (anchor changed)
    "active_new_count": "N"                  // New comments added during update
  },
  "anchor_reinjection": {
    "status": "ok|skipped|error",
    "reanchored": "N",                       // Markers successfully restored
    "skipped": "N"                           // Markers skipped (anchor text not found)
  }
}
```

---

## Known Limitations

- **Heavy content modification:** If anchor text is heavily modified or removed during update, inline comment cannot be automatically re-attached → **requires manual re-anchor or re-comment by team**.
- **Resolved comments:** Intentionally excluded from preservation tracking (already closed by users).
- **Storage format dependency:** Solution works with Confluence storage format; page macro changes may affect marker detection.

---

## Implementation Details

### Inline Marker Format
Confluence stores inline comments using this format in page storage HTML:
```xml
<ac:inline-comment-marker ac:ref="comment-uuid-string">
  anchor_text_here
</ac:inline-comment-marker>
```

When page is updated without preserving these tags, Confluence auto-resolves the comment because it cannot find the anchor reference.

### Re-injection Logic
1. Extract all `ac:ref` values and corresponding anchor text from storage before update
2. After update, search new storage for exact anchor text match
3. When found, wrap text with `<ac:inline-comment-marker ac:ref="UUID">text</ac:inline-comment-marker>`
4. Push updated storage back via PUT API

### Safety Gates
- Guard script detects drift between published baseline and current online page
- Requires explicit override flags to bypass safety checks
- Prevents accidental overwrite of unsynced edits

---

## Dependencies

- Python 3.12+
- `requests` library (HTTP API calls)
- `markdownify` (for markdown diff mode)
- Confluence REST API access
- Valid authentication method

---

## Execution Command

```powershell
cd "C:\Task 2\dds_comment_preserve_solution"
python comment_preserve_publish.py `
  --base-url "https://your-confluence-url/conf" `
  --page-id "your-page-id" `
  --md-path "path/to/local/markdown.md" `
  --heading-title "Section Title" `
  --apply --yes --force-scdp-override --yes-override `
  --access-token "your-bearer-token"
```

---

## Expected Output (Console)

```
=== ACTIVE COMMENTS ===
ACTIVE_COMMENTS_BEFORE=N
ACTIVE_COMMENTS_AFTER=N
ACTIVE_PRESERVED=N
ACTIVE_MISSING=0
ACTIVE_AUTO_RESOLVED=0
ACTIVE_NEW=0

[anchor-preserve] Found N inline marker(s) in page before overwrite.
[anchor-preserve] ✅ Re-anchored M inline comment(s). X could not be re-anchored.
REPORT_PATH=/path/to/comment_preservation_report.json
```

---

## Success Criteria

- ✅ All active comments before update are still active after update
- ✅ Inline marker anchors are restored and viewable in Confluence UI
- ✅ JSON report shows `ACTIVE_PRESERVED == ACTIVE_COMMENTS_BEFORE`
- ✅ No console errors or API failures
- ✅ Audit artifacts generated for team review
