#!/usr/bin/env python3
"""Render scientifically reconciled Figure 3 without modifying archived plots.

Input: frozen NEXCISION v0.1.0 formal summary and verification script.
Output: editable-text SVG and 300 dpi PNG for four panels and assembled figure.
"""
from __future__ import annotations
import csv
import sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DATA = ROOT/'experiments/experiment_2_scalability/results/formal/formal_summary-2432330.tsv'
sys.path.insert(0,str(HERE))
from verify_figure3 import main as verify_record

NAVY='#0D3263'; TEAL='#079D91'; BLUE='#2677B3'; INK='#183656'; MUTED='#5D728A'; PALE='#DBE8F2'; WHITE='#FFFFFF'
plt.rcParams.update({
    'font.family':'DejaVu Sans','font.size':10.5,'axes.titlesize':12.4,
    'axes.labelsize':10.4,'xtick.labelsize':9.2,'ytick.labelsize':9.2,
    'svg.fonttype':'none','svg.hashsalt':'nexcision-figure3-v0.1.0-reconciled',
    'axes.spines.top':False,'axes.spines.right':False,
    'axes.edgecolor':NAVY,'axes.labelcolor':INK,'xtick.color':MUTED,'ytick.color':MUTED,
    'savefig.facecolor':WHITE, 'figure.facecolor':WHITE,
})


def read_rows():
    with DATA.open(newline='',encoding='utf-8') as f:
        return list(csv.DictReader(f,delimiter='\t'))

def vals(rows,key): return np.array([float(r[key]) for r in rows],dtype=float)

def errors(rows,prefix,suffix):
    med=vals(rows,f'{prefix}_median_{suffix}')
    q1=vals(rows,f'{prefix}_q1_{suffix}')
    q3=vals(rows,f'{prefix}_q3_{suffix}')
    return np.vstack([np.maximum(0,med-q1),np.maximum(0,q3-med)])

def style(ax):
    ax.tick_params(direction='out',length=3.5,width=.8)
    ax.grid(axis='y',color=PALE,lw=.65,alpha=.65,which='major')
    ax.set_axisbelow(True)
    for side in ['left','bottom']: ax.spines[side].set_linewidth(.8)


def chart(ax, panel, rows):
    if panel in ('A','B'):
        inp=sorted((r for r in rows if r['series']=='input_size'),key=lambda z:float(z['input_gib']))
        x=vals(inp,'input_gib')
        if panel=='A':
            y=vals(inp,'elapsed_median_seconds')
            err=errors(inp,'elapsed','seconds')
            # Fit the original manuscript's predeclared >=~100MB subset in log-log space.
            # The six-median original-scale linear fit has a negative intercept and must NOT
            # be extrapolated to ~10MB on logarithmic axes.
            mask=x>=.09
            coef=np.polyfit(np.log10(x[mask]),np.log10(y[mask]),1)
            fit_x=np.geomspace(x[mask].min(),x.max(),200)
            ax.plot(fit_x,10**coef[1]*fit_x**coef[0],ls='--',color=TEAL,lw=1.9,zorder=2)
            ax.set_title('A  Runtime scales near-linearly with input size',loc='left',fontweight='bold',color=NAVY,pad=13)
            ax.set_ylabel('Median elapsed time (seconds)')
            ax.text(.985,.04,rf'Log–log exponent = {coef[0]:.3f} (≥100 MB)',transform=ax.transAxes,
                    ha='right',va='bottom',color=TEAL,fontsize=9)
        else:
            y=vals(inp,'peak_rss_median_gib')
            m=vals(inp,'peak_rss_median_bytes')
            err=errors(inp,'peak_rss','bytes')/(1024**3)
            coeff=np.polyfit(x,y,1)
            fit_x=np.geomspace(x.min(),x.max(),200)
            ax.plot(fit_x,np.polyval(coeff,fit_x),ls='--',color=TEAL,lw=1.9,zorder=2)
            ax.set_title('B  Peak memory increases with input size',loc='left',fontweight='bold',color=NAVY,pad=13)
            ax.set_ylabel('Median peak RSS (GiB)')
            ax.text(.985,.04,f'Linear slope = {coeff[0]:.3f} GiB/GiB',transform=ax.transAxes,
                    ha='right',va='bottom',color=TEAL,fontsize=9)
        ax.errorbar(x,y,yerr=err,fmt='o-',lw=1.45,markersize=5.6,capsize=3,
                    color=BLUE,ecolor=BLUE,elinewidth=1.1,zorder=3)
        ax.set_xscale('log');ax.set_yscale('log');ax.set_xlabel('Input matrix size (GiB)')
        for i,label in enumerate(['10 MB','100 MB','500 MB','1 GB','2 GB','5 GB']):
            off=(5,7) if i<4 else (5,-12) if i==4 else (-29,7)
            ax.annotate(label,(x[i],y[i]),xytext=off,textcoords='offset points',fontsize=8,color=INK)
        ax.set_xlim(.007,6.1)
        if panel=='A': ax.set_ylim(.073,40)
        else: ax.set_ylim(.047,37)
        ax.grid(axis='both',which='major',color=PALE,lw=.55,alpha=.7)
        return
    if panel=='C':
        by={r['case_id']:r for r in rows if r['series']=='matrix_shape'}
        data=[by[z] for z in ['shape_tall','shape_balanced','shape_wide']]
        y=vals(data,'elapsed_median_seconds')
        err=errors(data,'elapsed','seconds')
        xs=np.arange(3)
        ax.bar(xs,y,color=[NAVY,BLUE,TEAL],width=.57)
        ax.errorbar(xs,y,yerr=err,fmt='none',ecolor=INK,elinewidth=1.1,capsize=3,zorder=5)
        ax.set_xticks(xs)
        ax.set_xticklabels([f'Tall\n64 × 3.5M\n0.458 GiB',f'Balanced\n512 × 500k\n0.482 GiB',f'Wide\n8,192 × 32k\n0.489 GiB'])
        ax.set_ylabel('Median elapsed time (seconds)');ax.set_xlabel('Matrix shape (taxa × site rows; actual input size)')
        ax.set_title('C  Matrix shape is associated with runtime',loc='left',fontweight='bold',color=NAVY,pad=13)
        ax.set_ylim(0,6.15)
        for i,val in enumerate(y):ax.text(i,val+.16,f'{val:.2f} s',ha='center',fontsize=9,color=INK)
        style(ax);return
    if panel=='D':
        data=sorted((r for r in rows if r['series']=='interval_count'),key=lambda z:int(z['actual_intervals']))
        x=vals(data,'actual_intervals')
        y=vals(data,'elapsed_median_seconds')
        err=errors(data,'elapsed','seconds')
        ax.errorbar(x,y,yerr=err,fmt='o-',color=BLUE,ecolor=BLUE,lw=1.7,capsize=3,markersize=5.8)
        ax.set_xscale('log');ax.set_xlim(.68,1.7e5)
        ax.set_ylim(0,5.85) # untruncated y-axis makes the 13.5% overhead proportionally honest
        ax.set_ylabel('Median elapsed time (seconds)')
        ax.set_xlabel('Number of supplied intervals')
        ax.set_title('D  Runtime rises modestly with interval count',loc='left',fontweight='bold',color=NAVY,pad=13)
        ax.text(.98,.92,'+13.5% from 1 to 100,000',transform=ax.transAxes,
                ha='right',va='top',fontsize=9,color=TEAL,fontweight='bold')
        ax.set_xticks([1,10,100,1000,10000,100000])
        ax.set_xticklabels(['1','10','100','1k','10k','100k'])
        style(ax);return
    raise ValueError(panel)


def save_svg_clean(fig,path):
    fig.savefig(path,format='svg',metadata={'Date':None,'Creator':'NEXCISION verified Figure 3 renderer'})
    # Matplotlib draws multi-line path attributes with trailing spaces by default.
    # These whitespace-only changes are immaterial to valid SVG path geometry.
    content=path.read_text(encoding='utf-8')
    cleaned='\n'.join(line.rstrip() for line in content.splitlines())+'\n'
    path.write_text(cleaned,encoding='utf-8')


def save(fig,stem):
    fig.savefig(HERE/f'{stem}.png',dpi=300,metadata={'Software':'NEXCISION verified Figure 3 renderer'})
    save_svg_clean(fig,HERE/f'{stem}.svg')
    plt.close(fig)


def main():
    verify_record()
    rows=read_rows()
    for panel in 'ABCD':
        fig,ax=plt.subplots(figsize=(7.35,5.05),layout='constrained')
        chart(ax,panel,rows)
        save(fig,f'Figure3_{panel}')
    fig,axes=plt.subplots(2,2,figsize=(15.2,10.1),layout='constrained')
    for ax,panel in zip(axes.ravel(),'ABCD'):chart(ax,panel,rows)
    fig.suptitle('NEXCISION  |  Scalability and resource use',color=NAVY,fontweight='bold',fontsize=20)
    # Bottom left figure information is included in legend, not on the axes.
    save(fig,'Figure3_NEXCISION_scalability')
    print('WROTE: Four PNG/SVG panels and assembled Figure 3 (v0.1.0 historical evidence)')

if __name__=='__main__':main()
