import re

with open('static/index-v2-prototype.html','r') as f:
    content = f.read()

# Get _dvGuide entries with their titles — handle multi-line and escaped quotes
entries_raw = re.findall(r"'([a-z][a-z0-9_-]+)':\s*\{", content)
entries = []
for key in entries_raw:
    # Extract title value from the entry block
    m = re.search(r"'"+key+r"':\s*\{[^}]*?'title':\s*'([^']+)'", content)
    if m:
        entries.append((key, m.group(1)))

print('=== _dvGuide ENTRIES CONNECTED vs NOT CONNECTED ===')
print()

connected = []
not_connected = []

for key, title in sorted(entries):
    exact = f'data-guide="{key}"'
    if exact in content:
        connected.append((key, title))
    else:
        # Check dynamic patterns
        dynamic_patterns = {
            'signal-': 'dynamic via template',
            'confidence-': 'dynamic via template',
            'trade-type-': 'dynamic via template',
            'macro-': 'dynamic via template',
        }
        is_dynamic = False
        for prefix in dynamic_patterns:
            if key.startswith(prefix):
                is_dynamic = True
                break
        if is_dynamic:
            connected.append((key, title + ' [dynamic]'))
        else:
            not_connected.append((key, title))

print(f'CONNECTED ({len(connected)}):')
for k, t in connected:
    print(f'  {k}  →  {t}')

print()
print(f'NOT CONNECTED ({len(not_connected)}):')
for k, t in not_connected:
    print(f'  {k}  →  {t}')

print()
print('=== ELEMENTS WITH data-guide BUT NO _dvGuide ENTRY ===')
data_guides = set(re.findall(r'data-guide="([^"]+)"', content))
static_guides = {g for g in data_guides if '${' not in g and '+' not in g}
guide_keys = {k for k,_ in entries}
orphan_guides = static_guides - guide_keys
for g in sorted(orphan_guides):
    print(f'  data-guide="{g}" — NO _dvGuide entry')
