import json
import glob

# Get latest report
p = sorted(glob.glob('output/*_comment_preservation_report.json'))[-1]
d = json.load(open(p, encoding='utf-8'))

print('REPORT:', p.split('output\\')[-1])
print()

# Search for comments by their visible anchor text/original selection preview
search_keywords = {
    'content': 'Main heading - content (was Demo Test)',
    'hardware overview': 'Child heading - Hardware Overview',
    'content has been chnages': 'Modified text - content has been chnages',
    'something chnage': 'Renamed heading - something chnage (was Physical Topology)',
    'spine-leaf architecture': 'Content under renamed heading'
}

comment_map = d.get('comment_marker_map', {}).get('after', [])
storage_audit = {x.get('ref'): x for x in d.get('storage_anchor_audit', {}).get('details', [])}

print('=== CHECKING YOUR SPECIFIC COMMENTS ===')
print()

for keyword, description in search_keywords.items():
    matches = [c for c in comment_map if keyword.lower() in str(c.get('visible_anchor_text_preview', '')).lower() or keyword.lower() in str(c.get('original_selection_preview', '')).lower()]
    if matches:
        print(f'✓ {description}')
        for m in matches[:1]:
            cid = m.get('comment_id')
            ref = m.get('ref')
            audit = storage_audit.get(ref, {})
            orig = m.get('original_selection_preview', '')[:50]
            curr = m.get('visible_anchor_text_preview', '')[:50]
            exact = audit.get('exact_position')
            print(f'  Comment ID: {cid}')
            print(f'  Original: {orig}')
            print(f'  Current: {curr}')
            print(f'  EXACT POSITION PRESERVED: {exact}')
            print(f'  Type: {m.get("classification")}')
            print()
    else:
        print(f'✗ NOT FOUND: {description}')
        print()
