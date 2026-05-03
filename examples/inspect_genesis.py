#!/usr/bin/env python3
"""Check and display generated genesis files."""

import json
from pathlib import Path

# Check generated files
genesis_dir = Path('.chainright/genesis_example')

print('📁 Generated Files:')
print('='*70)
for json_file in sorted(genesis_dir.glob('*.json')):
    size = json_file.stat().st_size
    lines = len(json_file.read_text().split('\n'))
    print(f'{json_file.name:20} | {size:8,} bytes | ~{lines:5} lines')

print()
print('📊 Sample Concepts (first 2):')
print('='*70)
with open(genesis_dir / 'concepts.json') as f:
    concepts = json.load(f)
    for concept in concepts[:2]:
        print(f'• {concept["text"][:60]}...')
        print(f'  Keywords: {concept["keywords"]}')
        print(f'  Source: {concept["metalocation"]["source_title"]}')
        print(f'  Metalocation path:')
        ml = concept["metalocation"]
        print(f'    {ml["book_title"]}')
        print(f'    Chapter {ml["chapter_number"]}: {ml["chapter_title"]}')
        print(f'    Section {ml["section_number"]}: {ml["section_title"]}')
        print(f'    Paragraph {ml["paragraph_number"]}')
        print()
