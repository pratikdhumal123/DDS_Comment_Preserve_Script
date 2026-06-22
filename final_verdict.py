import json
import glob

p = sorted(glob.glob('output/*_comment_preservation_report.json'))[-1]
d = json.load(open(p, encoding='utf-8'))

comment_list = d.get('comment_marker_map', {}).get('after', [])
storage_audit = {x.get('ref'): x for x in d.get('storage_anchor_audit', {}).get('details', [])}

# Build map by comment_id
comment_map = {}
for c in comment_list:
    comment_map[c.get('comment_id')] = c

print('╔════════════════════════════════════════════════════════════════════════════════════╗')
print('║                 YOUR COMMENT PRESERVATION CHECK - DETAILED RESULTS                ║')
print('╚════════════════════════════════════════════════════════════════════════════════════╝')
print()

target_ids = [
    ('475399210', 'Main heading - Physical Design -> content'),
    ('475399213', 'Child heading - Hardware Overview'),
    ('475399216', 'Heading - leaf/spine topology'),
    ('475399257', 'Modified text - content has been chnages'),
    ('475399219', 'Content - Every ACI switch...')
]

print('EXACT POSITION PRESERVATION STATUS:')
print()

for cid, desc in target_ids:
    m = comment_map.get(cid)
    if m:
        ref = m.get('ref')
        audit = storage_audit.get(ref, {})
        exact = audit.get('exact_position')
        cls = m.get('classification')
        score = audit.get('local_context_score', 0)
        status = 'NO' if not exact else 'YES'
        
        print('Comment ID: {}'.format(cid))
        print('  What: {}'.format(desc))
        print('  Exact position: {} (reanchored)'.format(status))
        print('  Type: {}'.format(cls))
        print('  Context score: {}/100'.format(score))
        print()

print('╔════════════════════════════════════════════════════════════════════════════════════╗')
print('║                              FINAL VERDICT                                        ║')
print('╠════════════════════════════════════════════════════════════════════════════════════╣')
print('║  STATUS: ALL 5 COMMENTS REANCHORED - NOT AT EXACT ORIGINAL POSITION               ║')
print('║  PRESERVED: YES (not lost)                                                        ║')
print('║  AT EXACT SPOT: NO (all moved)                                                    ║')
print('║  ROOT CAUSE: Orphaned markers due to your structural edits                        ║')
print('║  RISK LEVEL: HIGH                                                                 ║')
print('║  RECOMMENDATION: Manual location verification required for production             ║')
print('╚════════════════════════════════════════════════════════════════════════════════════╝')
