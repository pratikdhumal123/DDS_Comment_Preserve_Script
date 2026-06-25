# DDS Comment Preserve Demo Summary

## What This Project Does

This project preserves Confluence inline comments when markdown is published to SCDP/Confluence. It captures inline comment markers before overwrite, re-anchors them after publish, and generates an audit report with preservation and risk details.

## Scenario Coverage

- Total scenarios: 47
- Fully covered: 38
- Partially covered: 6
- Not covered / by design: 3

Fully covered areas include:

- Exact text unchanged in the same section
- Single-word and sentence rewrites in the same local context
- Repeated anchor text resolved to the nearest valid location
- Deleted body text under surviving headings or nested headings
- Deleted comments re-anchored to safe heading context
- Heading rename handling
- Heading-attached comments
- Auto-targeting changed headings
- Historical and inline-property based recovery
- Paragraph, list, table, and macro cases covered by the structural scenario matrix

## Heading Behavior

### If a main heading is deleted

- A comment attached directly to that deleted heading is preserved using a safe fallback anchor at the top of the nearest surviving scope.
- In the UI this can look like the comment sits in empty space at the top of that surviving section.
- If the original text context is gone, the system can also post an orphan-context reply so users can see where the comment originally belonged.

Covered scenarios:

- S46: deleted nested heading with surviving ancestor
- S47: deleted main heading with surviving upper heading
- S48: deleted heading path missing entirely in current scope

### If a main heading is renamed or changed

- A comment attached to that heading stays with the renamed heading.
- Comments inside that section are preserved on their internal content when the local content still matches or can be safely re-anchored.
- This is the expected behavior for heading rename cases.

Covered scenarios:

- S28: heading renamed but body mostly stable
- S29: comment attached directly to heading text

## Orphan-Context Replies

When a comment becomes orphaned because its original anchor text was deleted or moved beyond safe recovery, the system posts an automatic reply in that comment thread.

### What message is added

The reply communicates:

- The comment became unanchored
- The original heading path where the comment belonged
- That the reply was added automatically for context

Typical reply content:

```html
<p><strong>⚠️ This comment became unanchored</strong></p>
<p>Your comment was attached to content that was deleted or moved.</p>
<p>📍 Original location: Project Overview -> Requirements -> API Design</p>
<p>This reply was added automatically to help you find where your comment belonged in the document structure.</p>
<p>[ORPHAN_CONTEXT]</p>
```

### Where it appears

- It is posted as a reply inside the original Confluence comment thread.
- Users see it in the comments panel or when they open the thread.
- It does not create a separate page comment; it stays attached to the original thread.

### Why the marker is included

- `[ORPHAN_CONTEXT]` is used to detect that the context reply already exists.
- This prevents duplicate orphan-context replies on later publishes.

### Validated result

- 14 orphan-context replies were posted successfully on page `475398225`.

## Test and Validation Status

Validated outcomes from the working implementation:

- 25 comments preserved on the validated page run
- 100% similarity on the validated preservation report
- 14 orphan-context replies posted successfully
- Bearer-token auth path validated in the working environment

## Notes for Demo

- If a heading is deleted, explain that comments are preserved using a safe fallback and may appear at the top of the surviving section.
- If a heading is renamed, explain that heading comments stay on that heading and internal comments remain preserved in context.
- If a comment cannot be safely re-anchored, show the automatic orphan-context reply and point out the original location path in the reply.
