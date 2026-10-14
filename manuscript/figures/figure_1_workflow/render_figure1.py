#!/usr/bin/env python3
"""Deterministically regenerate NEXCISION Figure 1 (SVG + PNG).

The diagram is based on the accompanying exact, independently checkable
transposed NEXUS example. Only standard-library Python and CairoSVG for PNG.
No scientific figures or measurements are invented or inferred.
"""
from __future__ import annotations
import html
from pathlib import Path

BASE = Path(__file__).resolve().parent
NAVY = '#0B2C60'
NAVY_2 = '#16437B'
TEAL = '#008F89'
TEAL_BRIGHT = '#00A69B'
SOFT_TEAL = '#E7F5F2'
PALE = '#F2F6FA'
GRAY = '#5B6D83'
BORDER = '#C7D8E6'
WHITE = '#FFFFFF'
ROWS = [
    ('CP013831_16000', 'AACGT'),
    ('CP013831_18000', 'AGCTG'),
    ('CP013831_18500', 'ACGAC'),
    ('CP013831_19000', 'GCTTA'),
    ('CP013831_20000', 'AACGT'),
]
TAXA = ['Iso1', 'Iso2', 'Iso3', 'Iso4', 'Iso5']
START, END = 18000, 19000
KEPT = [(p, seq) for p, seq in ROWS if not START <= int(p.rsplit('_', 1)[1]) <= END]
REMOVED = [(p, seq) for p, seq in ROWS if START <= int(p.rsplit('_', 1)[1]) <= END]
assert len(TAXA) == 5 and len(ROWS) == 5 and len(REMOVED) == 3 and len(KEPT) == 2
assert all(len(s) == len(TAXA) and set(s) <= set('ACGT') for _, s in ROWS)
assert KEPT == [ROWS[0], ROWS[-1]]

head = '''<svg xmlns="http://www.w3.org/2000/svg" width="1900" height="870" viewBox="0 0 1900 870" role="img" aria-labelledby="f-title f-desc">
<title id="f-title">NEXCISION workflow: coordinate-labelled site row excision</title>
<desc id="f-desc">Five sequence-character rows across five taxa are supplied. The inclusive interval 18000 through 19000 removes three rows, leaving rows at positions 16000 and 20000 unchanged. The taxon count stays five and the site-character count falls from five to two.</desc>
<defs>
 <linearGradient id="wordmark" x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" stop-color="#00A59C"/><stop offset="100%" stop-color="#00877F"/></linearGradient>
 <linearGradient id="softselect" x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" stop-color="#E7F6F3"/><stop offset="100%" stop-color="#D7F1EC"/></linearGradient>
 <filter id="shadow" x="-10%" y="-20%" width="120%" height="160%"><feDropShadow dx="0" dy="3" stdDeviation="5" flood-color="#153c59" flood-opacity="0.07"/></filter>
 <style>
    text {font-family:"Liberation Sans","DejaVu Sans",sans-serif;}
    .logoBlue{font-size:122px;font-weight:700;fill:#0B2C60;letter-spacing:-4px}
    .logoTeal{font-size:122px;font-weight:700;fill:url(#wordmark);letter-spacing:-3px}
    .title{font-size:30px;font-weight:700;fill:#0B2C60}
    .sub{font-size:22px;fill:#008F89}
    .th{font-size:20px;font-weight:700;fill:#0B2C60}
    .label{font-size:20px;fill:#0B2C60}
    .labelgreen{font-size:20px;font-weight:700;fill:#008F89}
    .base{font-size:23px;font-weight:700;fill:#0B2C60}
    .basegreen{font-size:23px;font-weight:700;fill:#008F89}
    .small{font-size:17px;fill:#5B6D83}
    .mono{font-family:"DejaVu Sans Mono",monospace;}
 </style>
</defs>'''

parts = [head]
def add(t): parts.append(t)
def rect(x,y,w,h, fill='none', stroke='none', rx=0, sw=1, extra=''):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>')
def line(x1,y1,x2,y2,stroke=NAVY, sw=2, dash=None):
    opt=f' stroke-dasharray="{dash}"' if dash else ''
    add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round"{opt}/>')
def text(x,y,s,cl='label',anchor=None, fill=None, size=None, weight=None, extra=''):
    attrs=[f'x="{x}"',f'y="{y}"',f'class="{cl}"']
    if anchor: attrs.append(f'text-anchor="{anchor}"')
    if fill: attrs.append(f'fill="{fill}"')
    if size: attrs.append(f'font-size="{size}"')
    if weight: attrs.append(f'font-weight="{weight}"')
    if extra: attrs.append(extra)
    add('<text '+' '.join(attrs)+'>'+html.escape(s)+'</text>')
def arrow(x,y):
    # Simple arrows are paths, not font glyphs.
    add(f'<path d="M {x} {y} h 24 m -11 -12 l 13 12 -13 12" fill="none" stroke="{NAVY}" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/>')

def cell(x,cy,ch,selected=False):
    rect(x,cy-27,51,39,fill='#FFFFFF',stroke='#DAE5EB',rx=6,sw=1.1)
    text(x+25.5,cy, ch, 'basegreen' if selected else 'base',anchor='middle')

# Opaque background and editable vector logo (no embedded font artwork).
rect(0,0,1900,870,fill=WHITE)
text(60,144,'NEX','logoBlue')
text(299,144,'CISION','logoTeal')
text(66,203,'Precise removal of coordinate-labelled site rows from transposed NEXUS matrices.',
     'label', size=27, fill=NAVY)
line(60,232,1840,232,'#DCE9ED',2)

# Three step headings and subtitles.
text(65,278,'1  Input transposed NEXUS matrix','title')
text(65,313,'Five taxa; five genomic-site rows.','sub')
text(735,278,'2  Select genomic interval','title')
text(735,313,'1-based inclusive boundaries.','sub')
text(1203,278,'3  Filtered NEXUS matrix','title')
text(1203,313,'Remaining site rows are unchanged.','sub')

# Main table shells.
rect(60,349,623,390,fill=WHITE,stroke=NAVY,rx=16,sw=2,extra='filter="url(#shadow)"')
rect(1195,349,642,390,fill=WHITE,stroke=NAVY,rx=16,sw=2,extra='filter="url(#shadow)"')

# Header of first matrix: these are taxa, not bases.
text(82,385,'Genomic coordinate (row label)','th')
text(489,384,'Taxa (columns)','th',anchor='middle')
rect(83,397,196,30,fill=PALE,rx=7)
text(180,417,'NCHAR = 5','small',anchor='middle')
rect(287,397,113,30,fill=PALE,rx=7)
text(343,417,'NTAX = 5','small',anchor='middle')
line(305,440,305,703,NAVY_2,1.5)
for j,t in enumerate(TAXA):
    x=328+j*63
    rect(x,435,55,32,fill='#ECF3F8',stroke='#D4E1EB',rx=5,sw=1)
    text(x+27.5,457,t,'th',anchor='middle')

# Matrix rows, upper three are selected within a green stripe.
cy_in = [506,552,598,644,690]
rect(70,525,599,138,fill='url(#softselect)',stroke=TEAL,rx=13,sw=1.6,extra='stroke-dasharray="6 4"')
for i,(label,states) in enumerate(ROWS):
    selected= START <= int(label.rsplit('_',1)[1]) <= END
    cy=cy_in[i]
    text(82,cy,label,'labelgreen' if selected else 'label')
    for j,base in enumerate(states): cell(330+j*63,cy,base,selected=selected)

# Matrix brace/disclaimer below table, outside body.
text(81,724,'Highlighted: CP013831_18000 to CP013831_19000', 'small')

# Center: interval input.
rect(738,372,390,174,fill=WHITE,stroke=TEAL,rx=16,sw=2,extra='filter="url(#shadow)"')
text(933,405,'regions.tsv','th',anchor='middle')
text(839,445,'start','labelgreen',anchor='middle')
text(1031,445,'end','labelgreen',anchor='middle')
line(766,464,1101,464,'#B7DDD7',1.5)
line(932,422,932,524,'#C9E7E3',1.5,dash='3 4')
text(839,505,'18000','basegreen',anchor='middle')
text(1031,505,'19000','basegreen',anchor='middle')

# 1-based inclusive interval timeline.
startx,endx=766,1100
yline=610
line(startx,yline,endx,yline,NAVY_2,3)
ticks=[16000,17000,18000,19000,20000,21000]
xs=[startx+i*(endx-startx)/5 for i in range(6)]
for tick,x in zip(ticks,xs):
    line(round(x,2),yline-13,round(x,2),yline+13,NAVY_2,1.5)
    text(round(x,2),yline+40,f'{tick:,}','small',anchor='middle')
line(xs[2],yline,xs[3],yline,TEAL,9)
for x in [xs[2],xs[3]]: add(f'<circle cx="{x}" cy="{yline}" r="10" fill="{TEAL}" stroke="white" stroke-width="2"/>')
text(933,685,'18,000–19,000 (inclusive)','labelgreen',anchor='middle')
text(933,716,'Matches 3 labelled site rows','small',anchor='middle')

# Arrows between steps.
arrow(696,560)
arrow(1151,560)

# Right hand table: same five taxa, two unchanged site rows.
text(1219,385,'Genomic coordinate (row label)','th')
text(1627,384,'Taxa (columns)','th',anchor='middle')
rect(1218,397,197,30,fill=PALE,rx=7)
text(1316.5,417,'NCHAR = 2','small',anchor='middle')
rect(1423,397,114,30,fill=PALE,rx=7)
text(1480,417,'NTAX = 5','small',anchor='middle')
line(1455,440,1455,661,NAVY_2,1.5)
for j,t in enumerate(TAXA):
    x=1481+j*67
    rect(x,435,60,32,fill='#ECF3F8',stroke='#D4E1EB',rx=5,sw=1)
    text(x+30,457,t,'th',anchor='middle')
for i,(label,states) in enumerate(KEPT):
    cy=530+i*84
    text(1219,cy,label,'label')
    for j,base in enumerate(states): cell(1485+j*67,cy,base)
line(1219,650,1811,650,'#DAE6EE',1.5)
text(1220,680,'Retained row labels, order and states are identical.','small')
text(1220,711,'Dimensions: NCHAR 5 → 2; NTAX stays 5.','small')

# Output summary ribbon for rapid interpretation.
rect(720,761,472,60,fill=SOFT_TEAL,stroke=TEAL,rx=13,sw=1.8)
text(956,798,'3 rows removed   ·   2 rows retained','labelgreen',anchor='middle')
text(949,851,'Illustrative, exact example: one reference-coordinate axis (CP013831).','small',anchor='middle')

add('</svg>')
svg='\n'.join(parts)+'\n'
path=BASE/'Figure1_NEXCISION_corrected.svg'
path.write_text(svg,encoding='utf8')
try:
    import cairosvg
except ImportError:
    print('CairoSVG missing: SVG written, PNG not rendered')
else:
    cairosvg.svg2png(bytestring=svg.encode(),write_to=str(BASE/'Figure1_NEXCISION_corrected.png'), output_width=3800,output_height=1740)
print('Wrote',path)
