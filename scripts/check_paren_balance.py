"""Quick paren-balance checker for Java files. Reports extra ) or ( by line."""
import sys

path = sys.argv[1]
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

parens = 0
braces = 0
in_block = False
in_string = False
escape = False
in_line = False
issues = []

for i, line in enumerate(lines):
    j = 0
    in_line = False
    while j < len(line):
        ch = line[j]
        nxt = line[j+1] if j+1 < len(line) else ''
        if in_block:
            if ch == '*' and nxt == '/':
                in_block = False; j += 2; continue
            j += 1; continue
        if in_line:
            break
        if in_string:
            if escape:
                escape = False; j += 1; continue
            if ch == '\\':
                escape = True; j += 1; continue
            if ch == '"':
                in_string = False
            j += 1; continue
        if ch == '/' and nxt == '/':
            in_line = True; break
        if ch == '/' and nxt == '*':
            in_block = True; j += 2; continue
        if ch == '"':
            in_string = True; j += 1; continue
        if ch == '(':
            parens += 1
        if ch == ')':
            parens -= 1
            if parens < 0 and not issues:
                issues.append((')', i+1, line.rstrip()[:80]))
        if ch == '{':
            braces += 1
        if ch == '}':
            braces -= 1
            if braces < 0 and not issues:
                issues.append(('}', i+1, line.rstrip()[:80]))
        j += 1

print(f'Final parens depth: {parens}')
print(f'Final braces depth: {braces}')
if issues:
    print('First issue:')
    for kind, lineno, text in issues:
        print(f'  extra {kind} at L{lineno}: {text}')
else:
    print('No issues found')
