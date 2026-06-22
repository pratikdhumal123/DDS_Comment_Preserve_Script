import json, glob, os

# Find latest report
reports = sorted(glob.glob('output/*_comment_preservation_report.json'))
if not reports:
    print("No report found")
    exit(1)

latest_report = reports[-1]
print(f"Report: {os.path.basename(latest_report)}")

with open(latest_report, encoding='utf-8') as f:
    data = json.load(f)

# Get storage anchor audit
audit = data.get('storage_anchor_audit', {})
details = audit.get('details', [])

# Find orphaned (empty anchor text after)
orphaned = [x for x in details if not (x.get('after_anchor_text_preview') or '').strip()]

print(f"Total markers checked: {len(details)}")
print(f"Orphaned markers: {len(orphaned)}")

if orphaned:
    print("\nOrphaned markers details:")
    for m in orphaned:
        print(f"  - Ref: {m.get('ref','')[-8:]}")
        print(f"    Before text: {m.get('before_anchor_text_preview','')[:60]}")
        print(f"    After text: {m.get('after_anchor_text_preview','')[:20]}")
else:
    print("\n✅ SUCCESS: All comments preserved - ZERO orphaned markers!")

# Check position similarity
position_matches = audit.get('summary', {}).get('position_match_count', 0)
print(f"\nPosition matches: {position_matches}/{len(details)}")
print(f"Position match %: {(position_matches/len(details)*100) if details else 0:.1f}%")
