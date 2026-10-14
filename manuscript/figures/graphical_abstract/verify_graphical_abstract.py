#!/usr/bin/env python3
"""Check graphical-abstract source/output consistency and build determinism."""
from pathlib import Path
import hashlib
import subprocess
import sys
import tempfile
from xml.etree import ElementTree as ET
from PIL import Image

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import render_graphical_abstract as r

assert len(r.ROWS)==6 and len(r.REMOVED)==3 and len(r.RETAINED)==3
assert set(r.REMOVED).isdisjoint(set(r.RETAINED))
assert r.ROWS==[row for row in r.ROWS if row in r.REMOVED or row in r.RETAINED]
assert all(len(states)==len(r.TAXA) for _,states in r.ROWS)
assert len({name.split('_')[0] for name,_ in r.ROWS})==1

src=HERE/'GraphicalAbstract_NEXCISION.svg'
img=HERE/'GraphicalAbstract_NEXCISION.png'
assert src.exists() and img.exists(),'Run render_graphical_abstract.py first'
root=ET.parse(src).getroot()
assert root.attrib.get('viewBox')=='0 0 2400 1350'
all_text=' '.join(n.text or '' for n in root.iter() if n.tag.endswith('text'))
for claim in ['NEX','CISION','18000','19000','3 removed  ·  3 retained',
              'NCHAR  6 → 3    |    NTAX  5 → 5','4.83 GiB in 24.24 s','23.4 GiB peak RSS',
              '1,000 synthetic matrices','12/12 deliberate faults detected','Snakemake','Single reference-coordinate axis',
              'validation and performance results refer to the frozen v0.1.0 release.']:
    assert claim.lower() in all_text.lower(),f'Missing: {claim}'
with Image.open(img) as png:
    assert png.size==(4800,2700),png.size
    assert png.mode in ('RGB','RGBA'),png.mode
with tempfile.TemporaryDirectory() as td:
    subprocess.run([sys.executable,str(HERE/'render_graphical_abstract.py'),'--out-dir',td],check=True,capture_output=True)
    for fn in (src.name,img.name):
        original=(HERE/fn).read_bytes(); replay=(Path(td)/fn).read_bytes()
        assert hashlib.sha256(original).digest()==hashlib.sha256(replay).digest(),f'Nondeterministic rendering: {fn}'
print('PASS: matrix arithmetic, required claims, dimensions, and exact rerender SHA-256 hashes')
