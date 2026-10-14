#!/usr/bin/env python3
"""Render the NEXCISION graphical abstract as an editable SVG and raster PNG.

No experimental data are recalculated. Benchmark claims refer only to the frozen
v0.1.0 evaluation; the illustrative matrix is independently computed here.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import svgwrite
import cairosvg

W, H = 2400, 1350
NAVY = '#103463'
DARK = '#08284e'
TEAL = '#008f89'
TEAL_DARK = '#087f7a'
TEXT = '#173a61'
MUTED = '#55708b'
PALE = '#edf7f6'
SKY = '#edf5fa'
LINE = '#c8dce9'
WHITE = '#ffffff'
AMBER = '#fff4e8'
RED = '#aa4960'
FONT = 'DejaVu Sans, Liberation Sans, Arial, sans-serif'

# This one-reference example follows the 1-based inclusive-coordinate model.
TAXA = ['Iso1', 'Iso2', 'Iso3', 'Iso4', 'Iso5']
ROWS = [
    ('CP013831_16000', ('A', 'A', 'C', 'G', 'T')),
    ('CP013831_17000', ('A', 'G', 'C', 'T', 'A')),
    ('CP013831_18000', ('A', 'G', 'C', 'T', 'G')),
    ('CP013831_18500', ('A', 'C', 'G', 'A', 'C')),
    ('CP013831_19000', ('G', 'C', 'T', 'T', 'A')),
    ('CP013831_20000', ('A', 'A', 'C', 'G', 'T')),
]
EXCLUSION_START, EXCLUSION_END = 18000, 19000

def position(row):
    return int(row[0].rsplit('_', 1)[1])

REMOVED = [row for row in ROWS if EXCLUSION_START <= position(row) <= EXCLUSION_END]
RETAINED = [row for row in ROWS if not (EXCLUSION_START <= position(row) <= EXCLUSION_END)]
assert len(ROWS) == 6 and len(REMOVED) == 3 and len(RETAINED) == 3
assert [position(r) for r in RETAINED] == [16000, 17000, 20000]
assert [r[1] for r in RETAINED] == [r[1] for r in ROWS if r not in REMOVED]


def main(out_dir: Path, render_px: int = 4800):
    out_dir.mkdir(parents=True, exist_ok=True)
    svg_path = out_dir / 'GraphicalAbstract_NEXCISION.svg'
    png_path = out_dir / 'GraphicalAbstract_NEXCISION.png'
    d = svgwrite.Drawing(str(svg_path), size=(f'{W}px', f'{H}px'), viewBox=f'0 0 {W} {H}', profile='full')
    d.add(d.rect(insert=(0, 0), size=(W, H), fill=WHITE))

    def rect(x, y, w, h, fill, stroke=None, sw=2, radius=0):
        opts = {'insert': (x,y), 'size': (w,h), 'fill':fill, 'rx':radius, 'ry':radius}
        if stroke: opts.update(stroke=stroke, stroke_width=sw)
        d.add(d.rect(**opts))
    def rule(x1,y1,x2,y2,color=LINE,width=2,dash=None):
        attrs={'start':(x1,y1), 'end':(x2,y2), 'stroke':color, 'stroke_width':width, 'stroke_linecap':'round'}
        if dash: attrs['stroke_dasharray']=dash
        d.add(d.line(**attrs))
    def circle(x,y,r,fill,stroke=None,sw=2):
        opts={'center':(x,y),'r':r,'fill':fill}
        if stroke: opts.update(stroke=stroke,stroke_width=sw)
        d.add(d.circle(**opts))
    def t(x,y,s,size=28,bold=False,color=TEXT,anchor='start',spacing=None):
        opts=dict(insert=(x,y), font_family=FONT, font_size=size,
                  font_weight='700' if bold else '400', fill=color, text_anchor=anchor)
        if spacing:opts['letter_spacing']=spacing
        d.add(d.text(str(s),**opts))
    def lines(x, y, items, size=26, step=38, color=TEXT, bold=False):
        for i, s in enumerate(items): t(x,y+i*step,s,size,bold,color)
    def arrow(x1,y,x2,color=NAVY):
        rule(x1,y,x2-15,y,color,7)
        d.add(d.polyline(points=[(x2-27,y-13),(x2-11,y),(x2-27,y+13)],
                         fill='none',stroke=color,stroke_width=7,stroke_linejoin='round',stroke_linecap='round'))
    def v_arrow(x,ya,yb,color=TEAL):
        rule(x,ya,x,yb-11,color,5)
        d.add(d.polyline(points=[(x-9,yb-19),(x,yb-9),(x+9,yb-19)],
                         fill='none',stroke=color,stroke_width=5,stroke_linecap='round',stroke_linejoin='round'))
    def panel(x,number,heading_lines):
        y=235
        rect(x,y,520,745,WHITE,LINE,2,18)
        rect(x,y,520,101,NAVY,radius=18)
        rect(x,y+22,520,79,NAVY)
        circle(x+52,y+51,30,WHITE)
        t(x+52,y+61,str(number),33,True,NAVY,'middle')
        for i,label in enumerate(heading_lines): t(x+103,y+47+i*37,label,33,True,WHITE)
        return x+23
    def matrix(x,y,rows,selected=False):
        # Matrix is a compact display of site-rows x taxa, not a full NEXUS file.
        rect(x,y,473,69+len(rows)*58,WHITE,LINE,2,10)
        rect(x+1,y+1,471,67,SKY,radius=10)
        rect(x+1,y+24,471,44,SKY)
        t(x+13,y+26,'Genomic coordinate',24,True,NAVY)
        t(x+13,y+53,'(row label)',21,False,MUTED)
        t(x+352,y+26,'Taxa',24,True,NAVY,'middle')
        rule(x+219,y,x+219,y+69+len(rows)*58,LINE,2)
        for j, taxon in enumerate(TAXA):
            t(x+250+j*43,y+57,taxon,16,True,TEXT,'middle')
        for i,(label, bases) in enumerate(rows):
            ry=y+69+i*58
            highlight = selected and EXCLUSION_START <= position((label,bases)) <= EXCLUSION_END
            if highlight:rect(x+3,ry+2,467,54,PALE)
            if i>0:rule(x+2,ry,x+471,ry,LINE,1)
            t(x+12,ry+38,label,22,highlight,TEAL_DARK if highlight else TEXT)
            for j,base in enumerate(bases):
                cell_x=x+230+j*43
                rect(cell_x,ry+9,37,41,WHITE,LINE,1,6)
                t(cell_x+18.5,ry+38,base,25,True,TEAL_DARK if highlight else NAVY,'middle')
        return y+69+len(rows)*58

    # HEADER
    t(43,143,'NEX',132,True,NAVY)
    t(335,143,'CISION',132,True,TEAL)
    rule(873,48,873,181,LINE,4)
    lines(927,89,['Reproducible site excision','from transposed NEXUS matrices'],47,62,NAVY,True)
    t(929,201,'Exact, auditable filtering of reference-defined genomic sites.',28,False,MUTED)

    # PANELS
    xs=[40,640,1240,1840]
    for idx, h in enumerate([
        ['The problem'],['Define the exclusion'],['Exact site excision'],['Integrate into your','pipeline'],
    ]): panel(xs[idx],idx+1,h)
    arrow(568,633,630)
    arrow(1168,633,1230)
    arrow(1768,633,1830)

    # PANEL 1: Input matrix & problem
    lines(65,377,['Ad hoc edits risk wrong site removal','and inconsistent matrix dimensions.'],26,39)
    matrix(64,463,ROWS,True)
    rect(66,906,469,52,AMBER,radius=8)
    t(82,940,'3 site rows fall within the exclusion',22,True,RED)

    # PANEL 2: Inclusive BED-like region and explanation
    lines(665,377,['Supply genomic intervals','using 1-based inclusive coordinates.'],26,39)
    rect(680,474,438,140,WHITE,TEAL,3,14)
    t(899,511,'regions.tsv',31,True,NAVY,'middle')
    rule(706,529,1094,529,LINE,2)
    t(766,558,'start',26,True,TEAL,'middle')
    t(1031,558,'end',26,True,TEAL,'middle')
    rule(903,537,903,601,LINE,2,'6,6')
    t(766,596,'18000',31,True,NAVY,'middle')
    t(1031,596,'19000',31,True,NAVY,'middle')
    rule(712,696,1080,696,NAVY,4)
    for idx, n in enumerate([16000,17000,18000,19000,20000,21000]):
        tx=712+368*idx/5
        rule(tx,682,tx,710,NAVY,2)
        if n in (18000,19000):circle(tx,696,11,TEAL,WHITE,2)
        if n in (16000,18000,20000):t(tx,739,f'{n:,}',20,False,MUTED,'middle')
    rule(712+368*2/5,696,712+368*3/5,696,TEAL,12)
    circle(712+368*2/5,696,11,TEAL,WHITE,2)
    circle(712+368*3/5,696,11,TEAL,WHITE,2)
    t(900,790,'18,000–19,000 (inclusive)',28,True,TEAL,'middle')
    rect(678,841,440,94,PALE,LINE,1,10)
    t(900,877,'Shared reference-coordinate axis',22,True,NAVY,'middle')
    t(900,913,'No contig-aware intervals',23,False,MUTED,'middle')

    # PANEL 3: actual filtered matrix
    lines(1265,377,['Matching site rows are removed;','retained states and order stay intact.'],26,39)
    matrix(1263,490,RETAINED,False)
    rect(1265,758,469,65,PALE,radius=8)
    t(1499,801,'3 removed  ·  3 retained',31,True,TEAL_DARK,'middle')
    t(1499,869,'NCHAR  6 → 3    |    NTAX  5 → 5',26,True,NAVY,'middle')
    lines(1269,921,['Compatible independent NEXUS blocks','are preserved; unsafe metadata is rejected.'],22,31,MUTED)

    # PANEL 4: workflow that avoids implying outputs are mandatory
    lines(1865,377,['Command-line integration for shell','and Snakemake workflows.'],26,39)
    # input
    rect(1881,464,438,92,SKY,LINE,2,12)
    t(2100,504,'input.nex + regions.tsv',26,True,NAVY,'middle')
    t(2100,535,'Supported matrix + intervals',22,False,MUTED,'middle')
    v_arrow(2100,561,597)
    rect(1881,601,438,83,PALE,TEAL,3,12)
    t(2100,653,'NEXCISION',38,True,TEAL_DARK,'middle')
    v_arrow(2100,690,727)
    rect(1881,733,438,105,SKY,LINE,2,12)
    t(2100,773,'filtered.nex',29,True,NAVY,'middle')
    t(2100,807,'Optional counts + SHA-256 report',20,False,MUTED,'middle')
    v_arrow(2100,845,880)
    rect(1881,885,438,70,WHITE,LINE,2,12)
    t(2100,930,'Downstream phylogenomics',25,True,NAVY,'middle')

    # EVIDENCE STRIP
    ev_y=1006; ev_h=180
    for xx, fill in [(40,PALE),(833,SKY),(1626,PALE)]:rect(xx,ev_y,734,ev_h,fill,LINE,2,14)
    circle(97,1068,24,TEAL)
    t(97,1078,'✓',34,True,WHITE,'middle')
    t(143,1058,'Independent validation',31,True,NAVY)
    lines(143,1103,['Naïve oracle · 1,000 synthetic matrices','12/12 deliberate faults detected'],24,33,TEXT)

    circle(888,1068,24,NAVY)
    t(888,1078,'↗',34,True,WHITE,'middle')
    t(930,1058,'Multi-gigabyte performance',30,True,NAVY)
    t(930,1105,'4.83 GiB in 24.24 s',30,True,NAVY)
    t(930,1147,'v0.1.0 · 1 pinned CPU · ~23.4 GiB peak RSS',20,False,MUTED)

    circle(1680,1068,24,TEAL)
    t(1680,1078,'→',33,True,WHITE,'middle')
    t(1723,1058,'Auditable provenance',31,True,NAVY)
    lines(1723,1103,['Per-interval counts when requested','Optional report with SHA-256 checksums'],24,33,TEXT)

    # FOOTER: single caveat and source URL, not a repeated slogan.
    rule(40,1218,2360,1218,LINE,2)
    t(40,1268,'Scope: supported transposed NEXUS matrices with a single reference-coordinate axis.',24,False,MUTED)
    t(2360,1268,'github.com/RhysWhite/nexcision',27,True,TEAL_DARK,'end')
    t(40,1311,'Illustrative matrix example; validation and performance results refer to the frozen v0.1.0 release.',20,False,MUTED)

    d.save(pretty=True)
    cairosvg.svg2png(url=str(svg_path),write_to=str(png_path),output_width=render_px,output_height=round(render_px*H/W))
    print(f'SVG {svg_path}')
    print(f'PNG {png_path}')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out-dir',type=Path,default=Path(__file__).resolve().parent)
    p.add_argument('--png-width',type=int,default=4800)
    a=p.parse_args()
    main(a.out_dir,a.png_width)
