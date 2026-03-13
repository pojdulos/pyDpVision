#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fix indentation issues in gLViewer.py"""

with open('dpVision/gui/gLViewer.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix lines around 712-732 - composite section
# These should all have 2 tabs indent (inside if wboit block)
fixes = []
for i in range(712, 733):
    line = lines[i]
    if 'Pass 0: accum' in line or 'Pass 1: reveal' in line or '4) Composite' in line:
        # Comments - should have 2 tabs
        if not line.startswith('\t\t\t\t#'):
            fixes.append((i, line, '\t\t\t\t# ' + line.lstrip('\t #')))
    elif 'glDrawBuffer' in line or 'glDepthMask' in line or 'glDisable' in line or 'glEnable' in line or 'glBlendFunc' in line or 'ws.render_transparent_wboit' in line or 'glBindFramebuffer' in line or 'self._composite_wboit' in line or 'glDepthFunc' in line or 'glClearColor' in line:
        # GL calls - should have 2 tabs
        if not line.startswith('\t\t\t\t'):
            fixes.append((i, line, '\t\t\t\t' + line.lstrip('\t')))
    elif 'self._fBgColor' in line:
        # ClearColor params - should have 3 tabs
        if not line.startswith('\t\t\t\t\t'):
            fixes.append((i, line, '\t\t\t\t\t' + line.lstrip('\t')))

if fixes:
    print(f"Found {len(fixes)} lines to fix")
    for idx, old, new in fixes:
        print(f"Line {idx+1}: {repr(old.strip())} -> {repr(new.strip())}")
        lines[idx] = new
    
    with open('dpVision/gui/gLViewer.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("Fixed!")
else:
    print("No fixes needed")
