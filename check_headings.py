import glob, os, re

# Find the saved storage file from before the Demo Title test
files = sorted(glob.glob('output/475398225_*_saved_storage_*.html'))
print("Available saved storage files (last 5):")
for f in files[-5:]:
    print(f"  {os.path.basename(f)}")

# Get the latest one before the Demo Title test run
if files:
    with open(files[-1], 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Search for heading text
    headings = re.findall(r'<h[1-6][^>]*>([^<]+)</h[1-6]>', content)
    print("\nHeadings found in Confluence storage (first 15):")
    for h in headings[:15]:
        clean = h.strip()[:80]
        print(f"  - {clean}")
