import json

with open(r'output\475401118_20260623T102426Z_comment_preservation_report.json') as f:
    data = json.load(f)

print("=== MARKERS WITH NO ANCHOR TEXT MATCH ===")
if 'storage_anchor_audit' in data:
    audit = data['storage_anchor_audit']
    details = audit.get('details', [])
    
    no_match = [d for d in details if not d.get('same_anchor_text')]
    print(f"Total markers without anchor text match: {len(no_match)}")
    
    for detail in no_match:
        print(f"\nRef: {detail.get('ref')}")
        print(f"  Before anchor: {detail.get('before_anchor_text_preview')}")
        print(f"  After anchor: {detail.get('after_anchor_text_preview')}")
        print(f"  Before start: {detail.get('before_start')}")
        print(f"  After start: {detail.get('after_start')}")
        print(f"  Offset delta: {detail.get('offset_delta')}")
        print(f"  Classification: {detail.get('classification')}")








