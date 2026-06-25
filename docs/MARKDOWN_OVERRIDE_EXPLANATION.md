# Markdown Override Mechanism Explained

## Overview
The markdown override mechanism is a **safety gate** that prevents accidental overwrites of Confluence page content when there's a mismatch between your local markdown and the current page on the server.

---

## The Core Problem It Solves

When publishing updated content to Confluence:
1. **Local Markdown** = Your edited version on your machine
2. **Page Storage** = Current version on Confluence server

**Scenario**: Someone else made manual edits on the Confluence page that aren't in your local markdown. If you publish without checking, you'll **lose their changes**.

**Solution**: The script detects this "drift" and refuses to overwrite until you explicitly confirm via the override flags.

---

## How It Works - The Flow

### Step 1: Pre-Publication Comparison (Always Happens)
```
┌─────────────────────────────────────────┐
│ Guard Script Compares:                  │
├─────────────────────────────────────────┤
│ • Local Markdown File                   │
│ • Current Page Storage on Server        │
│ • Detects "DRIFT" (differences)         │
│ • Generates comparison report           │
└─────────────────────────────────────────┘
```

The comparison checks:
- **Markdown format differences** (e.g., structure, links, formatting)
- **Storage format differences** (e.g., HTML conversion issues, special tags)
- **Safety flags** indicating whether it's safe to publish

---

### Step 2: Safety Gate Decision

#### If NO Drift Detected ✅
```
safe_to_publish: true
override_required: false
└─ Proceed to publish automatically
```

#### If Drift Detected ⚠️
```
safe_to_publish: false
override_required: true
└─ STOP! Require override flags to continue
```

---

## The Override Flags

### Three Key Flags Control the Override

#### 1. `--force-scdp-override`
- **Purpose**: Bypass the safety gate
- **Meaning**: "I've reviewed the drift and accept the risk"
- **What it does**: Tells the guard script that you've checked for conflicts and want to proceed anyway
- **Use case**: You've manually verified the differences are acceptable

```bash
python comment_preserve_publish.py \
  --base-url https://scdp-dev.cisco.com/conf \
  --page-id 381463502 \
  --md-path SDD.md \
  --heading-title "System Design" \
  --apply \
  --force-scdp-override  # ← Unlock the gate
```

#### 2. `--yes-override`
- **Purpose**: Skip the interactive prompt asking for confirmation
- **Meaning**: "I'm OK proceeding, don't ask me again"
- **What it does**: Removes the user prompt that appears when drift is detected
- **Use case**: Running in automated scripts or CI/CD pipelines

#### 3. `--no-prompt-override`
- **Purpose**: Don't prompt for override even in compare-only mode
- **Meaning**: "Just give me the report, don't ask about overriding"
- **What it does**: Allows compare-only runs without interactive prompts
- **Use case**: Dry-run comparisons where you just want the analysis

---

## Real-World Example

### Scenario 1: Safe Publish (No Override Needed)

```bash
$ python comment_preserve_publish.py \
    --base-url https://scdp-dev.cisco.com/conf \
    --page-id 381463502 \
    --md-path SDD.md \
    --heading-title "System Design" \
    --apply
```

**Result**:
```
[guard] Comparing markdown vs storage...
[guard] safe_to_publish: true ✅
[guard] override_required: false
→ Proceeding with publish automatically
→ Inline comments preserved
→ Report generated
```

---

### Scenario 2: Drift Detected (Override Required)

```bash
$ python comment_preserve_publish.py \
    --base-url https://scdp-dev.cisco.com/conf \
    --page-id 381463502 \
    --md-path SDD.md \
    --heading-title "System Design" \
    --apply
```

**Result**:
```
[guard] Comparing markdown vs storage...
[guard] safe_to_publish: false ⚠️
[guard] override_required: true
[guard] drift: true (Page was manually edited on server)

⚠️  PUBLISH BLOCKED
    Differences detected between your markdown and page storage.
    Manual edits were made to the page on the server.

    Do you want to override and publish anyway? (y/n)
```

**You have two choices**:

1. **Abort** (`n`): Cancel the publish and manually review/merge changes
2. **Override** (`y`): Accept the override and continue

---

### Scenario 3: Providing Flags in Advance

If you've already reviewed the drift and want to publish without prompts:

```bash
$ python comment_preserve_publish.py \
    --base-url https://scdp-dev.cisco.com/conf \
    --page-id 381463502 \
    --md-path SDD.md \
    --heading-title "System Design" \
    --apply \
    --force-scdp-override \     # ← Bypass safety gate
    --yes-override              # ← Skip confirmation prompt
```

**Result**:
```
[guard] Comparing markdown vs storage...
[guard] drift: true
[guard] override_required: true
[source] Override flags provided: PROCEEDING
→ Publishing with override
→ Inline comments preserved
→ Report generated
```

---

## How the Guard Script Enforces This

### Inside the Guard Script Logic

```python
# Pseudo-code showing the decision flow
if safe_to_publish and not override_required:
    # Case 1: No drift, safe to proceed
    return allow_publish = True

elif override_required and not force_scdp_override:
    # Case 2: Drift detected, no override flag
    if interactive_mode:
        ask_user("Override?")  # Waits for user input
    else:
        return allow_publish = False  # Auto-reject in scripts

elif override_required and force_scdp_override:
    # Case 3: Drift detected BUT override flag provided
    if yes_override:
        return allow_publish = True  # No more prompts
    else:
        ask_user("Override?")  # Still need confirmation
```

---

## Command-Line Override Reference

| Scenario | Flags | Behavior |
|----------|-------|----------|
| **No drift** | (none) | Publishes automatically |
| **Drift, interactive** | (none) | Prompts user to confirm |
| **Drift, skip prompt** | `--force-scdp-override --yes-override` | Publishes immediately |
| **Drift, allow prompt** | `--force-scdp-override` | Prompts user to confirm |
| **Compare only** | `--no-prompt-override` | Generates report only, no prompts |

---

## Key Insight: Why This Matters

The override mechanism prevents **data loss**:

✅ **Without it**: Publish blindly → Lose server edits → Team angry  
✅ **With it**: Get warned → Review changes → Make informed decision → Preserve all edits

The inline comment preservation happens **only after** the markdown override succeeds, ensuring:
1. Your markdown publishes
2. Comments from before the publish are re-attached
3. Team's discussion context is preserved

---

## Report Output

After a publish (with or without override), the script generates in `output/`:

```
381463502_20260601T154326Z_comment_preservation_report.json
├── guard
│   ├── status: "ok"
│   ├── drift: true/false          ← Was there a mismatch?
│   ├── safe_to_publish: true/false ← Was override needed?
│   ├── override_required: true/false
│   └── markdown_summary: {...}
│
├── decision
│   ├── override_required: true/false
│   └── final_allowed: true/false  ← Did publish actually happen?
│
└── comment_preservation
    ├── preserved_count: 45
    ├── missing_count: 2
    ├── auto_resolved_count: 0
    └── missing_preview: [...]      ← Which comments were lost
```

---

## Summary for Your Team

**Share this**:

> The markdown override is a **safety mechanism** that:
> - **Detects drift** between your local markdown and the server
> - **Requires explicit confirmation** if differences are found
> - **Prevents accidental data loss** from unreviewed changes
> - **Preserves inline comments** throughout the publish process
> 
> Use `--force-scdp-override --yes-override` only after reviewing the drift report and confirming it's safe to proceed.
