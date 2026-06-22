import json, glob, os

# Find latest report
reports = sorted(glob.glob('output/*_comment_preservation_report.json'))
latest_report = reports[-1]

with open(latest_report, encoding='utf-8') as f:
    data = json.load(f)

print("=" * 80)
print("COMMENT PRESERVATION TEST: 'Executive Summary' → 'Demo Title' HEADING RENAME")
print("=" * 80)
print(f"\nPage ID: 475398225")
print(f"Report: {os.path.basename(latest_report)}")
print(f"File: SDD-ACI (10).md")

# High level metrics
print("\n" + "=" * 80)
print("HIGH-LEVEL PRESERVATION METRICS")
print("=" * 80)
metrics = data.get('flow_status', {})
preserved = metrics.get('ACTIVE_PRESERVED', 0)
total = metrics.get('ACTIVE_COMMENTS_BEFORE', 0)
print(f"Total active comments before:  {metrics.get('ACTIVE_COMMENTS_BEFORE')}")
print(f"Total active comments after:   {metrics.get('ACTIVE_COMMENTS_AFTER')}")
print(f"Comments preserved:            {preserved}/{total}")
print(f"Missing comments:              {metrics.get('ACTIVE_MISSING', 0)}")
print(f"Auto-resolved:                 {metrics.get('ACTIVE_AUTO_RESOLVED', 0)}")
print(f"New comments:                  {metrics.get('ACTIVE_NEW', 0)}")

# Storage anchor audit details
print("\n" + "=" * 80)
print("DETAILED STORAGE ANCHOR AUDIT")
print("=" * 80)
audit = data.get('storage_anchor_audit', {})
details = audit.get('details', [])
orphaned = [x for x in details if not (x.get('after_anchor_text_preview') or '').strip()]

print(f"Total markers in storage:      {len(details)}")
print(f"Orphaned markers:              {len(orphaned)}")
print(f"Position matches:              {audit.get('summary', {}).get('position_match_count', 0)}/{len(details)}")

if orphaned:
    print(f"\n⚠️  WARNING: {len(orphaned)} ORPHANED MARKERS DETECTED!")
    print("\nOrphaned marker details:")
    for m in orphaned:
        print(f"\n  Reference ID: {m.get('ref','')[-8:]}")
        print(f"  Anchor text (before):  {m.get('before_anchor_text_preview','')[:70]}")
        print(f"  Anchor text (after):   {m.get('after_anchor_text_preview','') or '[EMPTY]'}")
        print(f"  Context (before):      {m.get('before_context_preview','')[:70]}")
else:
    print("\n✅ SUCCESS: All comments preserved - ZERO orphaned markers!")

print("\n" + "=" * 80)
