# Commands

## One-File Attach Summary (Short)

### What this project does
- Safely publishes local Markdown updates to Confluence.
- Preserves active inline comments as much as possible during overwrite.
- Produces before/after audit artifacts so the team can verify impact.

### What we need
- Python 3.12+ and required packages (from `requirements.txt`).
- Confluence access to target page (`base-url`, `page-id`).
- Local markdown source file (`md-path`).
- Auth via one of: bearer token, username/token, or session cookie.

### What we used
- Main wrapper: `comment_preserve_publish.py`
- Guard/compare engine: bundled `standalone_clone/scdp_compare_guard.py`
- Confluence REST API (content + comments + storage HTML)
- Output artifacts: JSON reports + HTML compare report in `output/`

### End-to-end flow
1. Read current page comments and create **before snapshot**.
2. Run compare guard to detect drift and enforce safe overwrite decision.
3. If approved, publish markdown content to Confluence.
4. Re-inject inline comment markers for active comments (when anchor text still exists).
5. Read comments again and create **after snapshot**.
6. Generate report with active preserved/missing/new/auto-resolved status.
7. Save audit files (`comments_before`, `comments_after`, `compare_guard`, `final_report`).

### Important note
- If anchor text is heavily changed or removed, some inline comments cannot be re-attached automatically and may require manual follow-up.

## Project Summary (Jira Ready)

- Build a safe publish flow from local Markdown to Confluence while preserving inline comments.
- Take a comment snapshot before overwrite and compare again after overwrite to detect what changed.
- Preserve active inline comments by re-injecting inline marker anchors after page update.
- Generate clear run outputs and reports: active preserved, missing, new, and auto-resolved comments.
- Keep the solution standalone (bundled local scripts/config) so it runs without external project dependencies.
- Improve reliability with fallback authentication handling (bearer/basic/cookie strategies).
- Add guard checks before overwrite to prevent accidental loss when page drift is detected.
- Support team visibility with JSON + HTML artifacts for audit/review after each run.

## Highlights

- **Safety first:** compare + drift detection + explicit overwrite confirmation.
- **Comment-aware publish:** before/after snapshots and inline-marker re-anchor logic.
- **Clear reporting:** console summary + machine-readable JSON report + HTML compare report.
- **Standalone execution:** local bundled clone in `standalone_clone` for reproducible runs.
- **Known limitation:** if anchor text is heavily changed/removed, some inline comments cannot be re-attached automatically.

## Current Focus

- End-to-end validation on real Confluence pages.
- Refining edge cases around anchor matching and re-injection behavior.

## 1) Compare + Comment Audit (No overwrite)

```powershell
cd "C:/Task 3/dds_comment_preserve_solution"
& "C:/Task 3/dds_comment_preserve_solution/.venv/Scripts/python.exe" .\comment_preserve_publish.py `
  --base-url "https://scdp-dev.cisco.com/conf" `
  --page-id 381463512 `
  --md-path "C:/Task 3/dds_comment_preserve_solution/standalone_clone/input/sdd.md" `
  --heading-title "Logical Design" `
  --compare-mode both `
  --no-prompt-override
```

## 2) Overwrite + Comment Preservation Audit

```powershell
cd "C:/Task 3/dds_comment_preserve_solution"
& "C:/Task 3/dds_comment_preserve_solution/.venv/Scripts/python.exe" .\comment_preserve_publish.py `
  --base-url "https://scdp-dev.cisco.com/conf" `
  --page-id 381463512 `
  --md-path "C:/Task 3/dds_comment_preserve_solution/standalone_clone/input/sdd.md" `
  --heading-title "Logical Design" `
  --compare-mode both `
  --apply --yes --force-scdp-override --yes-override `
  --reflect-on-page --reflect-mode markdown `
  --reflect-persist-manual --reflect-keep-after-refresh `
  --reflect-auto-clear-seconds 0
```

## 3) Force an external project root (optional)

Add:

```powershell
--project-root "C:/confluence-api-project"
```

## 4) With bearer token authentication

Add:

```powershell
--access-token "<TOKEN>"
```

## Output

Look for `REPORT_PATH=` in console. The report includes:
- preserved/missing/new comment counts,
- missing comment previews,
- compare/guard summary from bundled `scdp_compare_guard.py`.


compare only :

cd "C:\Task 3\dds_comment_preserve_solution"
& "C:/Task 3/dds_comment_preserve_solution/.venv/Scripts/python.exe" .\comment_preserve_publish.py `
  --base-url "https://scdp.cisco.com/conf" `
  --page-id "467033120" `
  --md-path "standalone_clone\input\SDD-ACI (1).md" `
  --heading-title "Physical Design" `
  --compare-mode both

  Apply test : 

  cd "C:\Task 3\dds_comment_preserve_solution"
& "C:/Task 3/dds_comment_preserve_solution/.venv/Scripts/python.exe" .\comment_preserve_publish.py `
  --base-url "https://scdp.cisco.com/conf" `
  --page-id "467033120" `
  --md-path "standalone_clone\input\SDD-ACI (1).md" `
  --heading-title "Physical Design" `
  --compare-mode both `
  --apply --yes --force-scdp-override --yes-override


  Automatic Section select

  Set-Location "c:\Task 3\dds_comment_preserve_solution"
.\.venv\Scripts\python.exe .\comment_preserve_publish.py `
  --base-url "https://scdp.cisco.com/conf" `
  --page-id "470213898" `
  --md-path "standalone_clone\input\SDD-ACI (4).md" `
  --heading-title auto `
  --compare-mode both `
  --apply `
  --yes `
  --force-scdp-override `
  --yes-override

  standalone_clone\input\SDD-ACI 9 June demo 01.md

    Set-Location "c:\Task 3\dds_comment_preserve_solution"
.\.venv\Scripts\python.exe .\comment_preserve_publish.py `
  --base-url "https://scdp.cisco.com/conf" `
  --page-id "472154240" `
  --md-path "standalone_clone\input\SDD-ACI 9 June demo 01.md" `
  --heading-title auto `
  --compare-mode both `
  --apply `
  --yes `
  --force-scdp-override `
  --yes-override

  Set-Location "c:\Task 3\dds_comment_preserve_solution"; .\.venv\Scripts\python.exe .\comment_preserve_publish.py --base-url "https://scdp.cisco.com/conf" --page-id "470213898" --md-path "c:\Task 3\dds_comment_preserve_solution\standalone_clone\input\SDD-ACI (4).md" --heading-title auto --compare-mode both --apply --yes --force-scdp-override --yes-override