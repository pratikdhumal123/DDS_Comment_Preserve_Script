import json
import glob

p = sorted(glob.glob('output/*_comment_preservation_report.json'))[-1]
d = json.load(open(p, encoding='utf-8'))

print('REPORT:', p.split('output\\')[-1])
print()

# Show risk assessment
risk = d.get('risk_assessment', {})
print('=== WHY NOT EXACT-POSITION ===')
print('Risk Level:', risk.get('risk_level'))
print('Manual Review:', risk.get('manual_review_required'))
print()
print('Root causes:')
for reason in risk.get('reasons', []):
    print(f'  • {reason}')
print()

# Search for target comments
target_ids = ['475399210', '475399213', '475399216', '475399219', '475399257']
comment_map = d.get('comment_marker_map', {}).get('after', [])
storage_audit = {x.get('ref'): x for x in d.get('storage_anchor_audit', {}).get('details', [])}

print('=== YOUR SPECIFIC COMMENTS ===')
print()

for cid in target_ids:
    matches = [c for c in comment_map if str(c.get('comment_id')) == cid]
    if matches:
        m = matches[0]
        ref = m.get('ref')
        audit = storage_audit.get(ref, {})
        print(f'Comment ID: {cid}')
        print(f'  Original anchor text: {m.get("original_selection_preview")}')
        print(f'  Current visible text: {m.get("visible_anchor_text_preview")}')
        print(f'  Classification: {m.get("classification")}')
        print(f'  Exact position: {audit.get("exact_position")} (NO = reanchored)')
        print(f'  Same anchor text: {audit.get("same_anchor_text")}')
        print(f'  Context match score: {audit.get("local_context_score")}')
        print()
