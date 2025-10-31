with open('c:/Agent-S-Redfinger/src/vision/providers.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix lines 166-170 (0-indexed: 166-170)
for i in range(166, 171):
    if i < len(lines) and lines[i].startswith('        '):
        lines[i] = lines[i][4:]  # Remove 4 spaces

with open('c:/Agent-S-Redfinger/src/vision/providers.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Fixed indentation")
