import glob
import os
import re

storage_path = sorted(glob.glob("output/*_saved_storage_after_reanchor.html"))[-1]
html = open(storage_path, encoding="utf-8").read()

refs = [
    "f1b09088-fa50-4946-b3c5-cc28d49302d6",
    "29ad3d2a-54f1-4c2e-95c2-8d779cfc5394",
    "58ef4478-202b-4b11-8ac6-fa41d8f566ee",
    "d7057a7a-a70b-4274-a2e7-eb2783336b15",
]

print("Storage:", os.path.basename(storage_path))
print("Document length:", len(html))
print()

for ref in refs:
    m = re.search(r'ac:ref="' + re.escape(ref) + r'"', html)
    if not m:
        print(ref[-8:], "NOT FOUND")
        continue

    pos = m.start()
    # Show local snippet around marker and how close to top it is
    start = max(0, pos - 140)
    end = min(len(html), pos + 220)
    snippet = html[start:end].replace("\n", " ")

    print(f"{ref[-8:]} pos={pos} ({(pos/len(html))*100:.2f}% of doc)")
    print(snippet[:320])
    print("---")
