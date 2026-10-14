#!/usr/bin/env python3
"""Rebuild the vector/raster NEXCISION Figure 2 from verified v0.1.0 records.

Requires matplotlib. Figure labels are intentionally frozen to original results;
the associated verification script checks their underlying archived evidence.
For v1.0.0, rerun validation and explicitly update both files and the legend.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib import rcParams

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from verify_figure2 import main as verify_records  # noqa: E402

NAVY = '#0D3263'
TEAL = '#079D91'
PALE_TEAL = '#E7F6F3'
PALE_BLUE = '#E5EEF7'
INK = '#112F56'
MUTED = '#546A80'
WHITE = '#FFFFFF'

LAYERS = [
    ('Genuine SPANDx matrices', '3 matrices  |  6/6 archived checks'),
    ('Independent naïve oracle', 'Direct 1-based inclusive interval membership'),
    ('Permanent fixed cases', '17/17 correctness + 1/1 empty-output safety'),
    ('Malformed-input challenges', '26/26 controlled failures; no unintended outputs'),
    ('Deterministic synthetic corpus', '1,000/1,000 matrices  |  304,000 site rows'),
    ('Property-based testing', '9 invariants  |  1,800 generated examples'),
    ('Deliberate mutation testing', '12/12 selected faults detected'),
]


def main() -> None:
    verify_records()
    rcParams['font.family'] = 'DejaVu Sans'
    rcParams['svg.fonttype'] = 'none'  # editable text in SVG
    rcParams['svg.hashsalt'] = 'nexcision-figure2-v0.1.0'

    fig = plt.figure(figsize=(13.6, 8.55), facecolor=WHITE)
    ax = fig.add_axes((0,0,1,1))
    ax.set_xlim(0,1360);ax.set_ylim(0,855);ax.axis('off')

    ax.text(64,789,'Validation designed to make failure visible',fontsize=28,
            fontweight='bold', color=NAVY, va='center')
    ax.text(64,743,'Seven complementary evidence layers · original NEXCISION v0.1.0 evaluation',
            fontsize=14.4,color=MUTED,va='center')

    left=69; width=1223; row_h=76; space=13; first_y=635
    for i,(heading,stat) in enumerate(LAYERS):
        y=first_y-i*(row_h+space)
        fill=PALE_TEAL if i%2==0 else PALE_BLUE
        edge=TEAL if i%2==0 else NAVY
        rect=FancyBboxPatch((left,y),width,row_h,boxstyle='round,pad=0,rounding_size=11',
                            linewidth=1.7,edgecolor=edge,facecolor=fill)
        ax.add_patch(rect)
        ax.add_patch(FancyBboxPatch((left+15,y+15),5,row_h-30,
                                   boxstyle='round,pad=0,rounding_size=2.5',
                                   linewidth=0,facecolor=edge))
        ax.text(left+39,y+row_h/2,heading,fontsize=17.8,fontweight='bold',
                color=NAVY,va='center')
        ax.text(left+width-26,y+row_h/2,stat,fontsize=14.1,
                color=INK,va='center',ha='right')

    summary_y=40
    ax.add_patch(FancyBboxPatch((left+56,summary_y),width-112,52,
                                boxstyle='round,pad=0,rounding_size=12',
                                linewidth=0,facecolor=TEAL))
    ax.text(680,summary_y+26,'PASS  ·  exact site membership  ·  retained-content preservation  ·  deterministic outputs',
            fontsize=15.2,fontweight='bold',color=WHITE,va='center',ha='center')
    ax.text(680,17,'Evidence applies to the prespecified SPANDx-style transposed NEXUS model; '
            'v1.0.0 requires fresh validation.',
            fontsize=10.2,color=MUTED,va='center',ha='center')

    png=HERE/'Figure2_NEXCISION_validation.png'
    svg=HERE/'Figure2_NEXCISION_validation.svg'
    fig.savefig(png,dpi=300,facecolor=WHITE,metadata={'Software':'NEXCISION Figure 2 reproducible rendering'})
    fig.savefig(svg,facecolor=WHITE,metadata={'Date':None,'Creator':'NEXCISION Figure 2 reproducible rendering'})
    # Matplotlib adds trailing spaces to multiline SVG path data. Strip only
    # spaces/tabs preceding newlines, keeping the SVG valid and git-diff clean.
    svg.write_bytes(b'\n'.join(line.rstrip(b' \t') for line in svg.read_bytes().split(b'\n')))
    plt.close(fig)
    print('WROTE:',png,'and',svg)


if __name__ == '__main__':
    main()
