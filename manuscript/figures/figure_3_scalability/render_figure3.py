#!/usr/bin/env python3
"""Render replicate-level Figure 3 without modifying archived benchmark records.

Input: frozen NEXCISION v0.1.0 formal measured and summary TSV files.
Output: editable-text SVG and 300 dpi PNG for four panels and assembled figure.
"""
from __future__ import annotations
import csv
import sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DATA = ROOT/'experiments/experiment_2_scalability/results/formal/formal_summary-2432330.tsv'
MEASURED = ROOT/'experiments/experiment_2_scalability/results/formal/formal_measured-2432330.tsv'
sys.path.insert(0,str(HERE))
from verify_figure3 import main as verify_record

# Accessible across common colour-vision deficiencies; separate marker shape and
# luminance ensure that a monochrome printout remains interpretable.
NAVY = '#1F3B5C'
TEAL = '#1B9E77'
AMBER = '#D89C1D'
INK = '#333333'
MUTED = '#535B65'
GRID = '#DDE1E5'
WHITE = '#FFFFFF'

plt.rcParams.update({
    'font.family':'DejaVu Sans', 'font.size':10.1, 'axes.titlesize':11.9,
    'axes.labelsize':10.1, 'xtick.labelsize':9.1, 'ytick.labelsize':9.1,
    'svg.fonttype':'none', 'svg.hashsalt':'nexcision-figure3-v0.1.0-replicates',
    'axes.spines.top':False, 'axes.spines.right':False,
    'axes.edgecolor':INK, 'axes.labelcolor':INK, 'xtick.color':MUTED,
    'ytick.color':MUTED, 'savefig.facecolor':WHITE, 'figure.facecolor':WHITE,
})


def read_rows(path):
    with path.open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle, delimiter='\t'))


def vals(rows, key):
    return np.asarray([float(row[key]) for row in rows], dtype=float)


def style(ax, grid_x=False):
    ax.tick_params(direction='out', length=3.3, width=.75)
    ax.grid(axis='both' if grid_x else 'y', color=GRID, lw=.6,
            alpha=.8, which='major')
    ax.set_axisbelow(True)
    for side in ('left', 'bottom'):
        ax.spines[side].set_linewidth(.8)


# Display-only offsets, symmetric about the true configuration x-coordinate.
# They DO NOT change any input size or interval count used for analysis/fits.
JITTER_LOG10 = np.array([-.032, -.016, 0, .016, .032])
JITTER_CATEGORICAL = np.array([-.15, -.075, 0, .075, .15])


def measured_by_case(measured):
    from collections import defaultdict
    byid = defaultdict(list)
    for row in measured:
        byid[row['case_id']].append(row)
    for rows in byid.values():
        rows.sort(key=lambda row: int(row['repeat']))
    return byid


def series_points(ax, summaries, measurements, metric, xkey,
                  log_x=True, point_color=TEAL):
    """Plot all five measured runs per configuration, with no random jitter."""
    count = 0
    for summary in summaries:
        runs = measurements[summary['case_id']]
        assert len(runs) == len(JITTER_LOG10) == 5
        x = float(summary[xkey])
        xplot = x * 10**JITTER_LOG10 if log_x else x + JITTER_CATEGORICAL
        yplot = vals(runs, metric)
        ax.scatter(xplot, yplot, s=36, marker='o', color=point_color,
                   edgecolor=INK, linewidth=.55, alpha=.85, zorder=4)
        count += len(runs)
    return count


def median_markers(ax, x, y, label='Configuration median'):
    # Short horizontal strokes are visible independent of marker colours.
    ax.scatter(x, y, marker='_', s=300, color=NAVY, linewidths=2.5,
               zorder=7, label=label)


def chart(ax, panel, summaries, measurements):
    if panel in ('A', 'B'):
        group = sorted((r for r in summaries if r['series'] == 'input_size'),
                       key=lambda row: float(row['input_gib']))
        assert len(group) == 6
        x = vals(group, 'input_gib')
        if panel == 'A':
            y = vals(group, 'elapsed_median_seconds')
            metric = 'elapsed_seconds'
            # Original, independently validated log-log fit for >= ~100 MB.
            # The separate original-scale OLS model has a negative intercept;
            # do not extrapolate it over the ~10 MB observation on log axes.
            mask = x >= .09
            slope, intercept = np.polyfit(np.log10(x[mask]),
                                          np.log10(y[mask]), 1)
            fit_x = np.geomspace(x[mask].min(), x.max(), 200)
            fit_y = 10**intercept * fit_x**slope
            ax.set_title('A  Runtime scales near-linearly with input size',
                         loc='left', fontweight='bold', color=NAVY, pad=12)
            ax.set_ylabel('Elapsed time (seconds)')
            ax.set_ylim(.073, 40)
            ax.text(.985, .04, f'Log–log exponent = {slope:.3f} (≥100 MB)',
                    transform=ax.transAxes, ha='right', va='bottom',
                    color=INK, fontsize=8.9)
        else:
            y = vals(group, 'peak_rss_median_gib')
            metric = 'peak_rss_bytes'
            coef = np.polyfit(x, y, 1)
            fit_x = np.geomspace(x.min(), x.max(), 200)
            fit_y = np.polyval(coef, fit_x)
            ax.set_title('B  Peak memory increases with input size',
                         loc='left', fontweight='bold', color=NAVY, pad=12)
            ax.set_ylabel('Peak RSS (GiB)')
            ax.set_ylim(.047, 37)
            ax.text(.985, .04, f'Linear slope = {coef[0]:.3f} GiB/GiB',
                    transform=ax.transAxes, ha='right', va='bottom',
                    color=INK, fontsize=8.9)
        ax.plot(fit_x, fit_y, ls='--', color=INK, lw=1.7, dashes=(5, 3),
                zorder=2, label='Fitted trend')
        # Plot peak RSS in GiB: archived raw measurements are recorded in bytes.
        if panel == 'A':
            count = series_points(ax, group, measurements, metric, 'input_gib')
        else:
            for summary in group:
                runs = measurements[summary['case_id']]
                xplot = float(summary['input_gib']) * 10**JITTER_LOG10
                yp = vals(runs, metric) / (1024**3)
                ax.scatter(xplot, yp, s=36, marker='o', color=TEAL,
                           edgecolor=INK, linewidth=.55, alpha=.85, zorder=4)
            count = sum(len(measurements[g['case_id']]) for g in group)
        median_markers(ax, x, y)
        assert count == 30
        ax.set_xscale('log'); ax.set_yscale('log')
        ax.set_xlabel('Input matrix size (GiB)')
        ax.set_xlim(.007, 6.1)
        ax.set_xticks(x)
        ax.set_xticklabels(['10 MB', '100 MB', '500 MB', '1 GB', '2 GB', '5 GB'])
        ax.tick_params(axis='x', labelsize=8.5)
        style(ax, grid_x=True)
        if panel == 'A':
            # A compact shared key; B and D use the same visual encodings.
            ax.legend(handles=[
                Line2D([], [], ls='none', marker='o', ms=5,
                       markerfacecolor=TEAL, markeredgecolor=INK,
                       label='Measured run (n=5)'),
                Line2D([], [], ls='none', marker='_', ms=14,
                       markeredgewidth=2.3, color=NAVY, label='Median'),
                Line2D([], [], ls='--', dashes=(5, 3), lw=1.7,
                       color=INK, label='Fitted trend'),
            ], loc='upper left', frameon=False, fontsize=8.2,
               ncol=3, handlelength=1.8, columnspacing=1.2)
        return count

    if panel == 'C':
        byid = {r['case_id']: r for r in summaries if r['series'] == 'matrix_shape'}
        group = [byid[z] for z in ('shape_tall', 'shape_balanced', 'shape_wide')]
        colours = (NAVY, TEAL, AMBER)
        markers = ('o', 's', '^')
        x = np.arange(3, dtype=float)
        y = vals(group, 'elapsed_median_seconds')
        count = 0
        for i, row in enumerate(group):
            runs = measurements[row['case_id']]
            assert len(runs) == 5
            ax.scatter(x[i] + JITTER_CATEGORICAL, vals(runs, 'elapsed_seconds'),
                       marker=markers[i], s=60, color=colours[i],
                       edgecolor=INK, linewidth=.8, zorder=4)
            ax.plot([x[i]-.21, x[i]+.21], [y[i],y[i]], color=INK,
                    lw=2.8, zorder=7, solid_capstyle='butt')
            count += len(runs)
        assert count == 15
        ax.set_xticks(x)
        ax.set_xticklabels(['Tall\n64 × 3.5M\n0.458 GiB',
                            'Balanced\n512 × 500k\n0.482 GiB',
                            'Wide\n8,192 × 32k\n0.489 GiB'])
        ax.set_ylabel('Elapsed time (seconds)')
        ax.set_xlabel('Matrix shape (taxa × site rows; actual input size)')
        ax.set_title('C  Matrix shape is associated with runtime',
                     loc='left', fontweight='bold', color=NAVY, pad=12)
        ax.set_xlim(-.48, 2.48)
        ax.set_ylim(0, 6.4)
        for i, val in enumerate(y):
            ax.text(i, val+.3, f'{val:.2f} s', ha='center', va='bottom',
                    fontsize=9, color=INK, fontweight='bold')
        style(ax)
        return count

    if panel == 'D':
        group = sorted((r for r in summaries if r['series'] == 'interval_count'),
                       key=lambda row: int(row['actual_intervals']))
        assert len(group) == 6
        x = vals(group, 'actual_intervals')
        y = vals(group, 'elapsed_median_seconds')
        count = series_points(ax, group, measurements,
                              'elapsed_seconds', 'actual_intervals')
        assert count == 30
        ax.plot(x, y, lw=2.1, color=NAVY, zorder=5,
                marker='_', markersize=13, markeredgewidth=2.5)
        ax.set_xscale('log'); ax.set_xlim(.68, 1.7e5)
        ax.set_ylim(0, 5.9)
        ax.set_ylabel('Elapsed time (seconds)')
        ax.set_xlabel('Number of supplied intervals')
        ax.set_title('D  Runtime rises modestly with interval count',
                     loc='left', fontweight='bold', color=NAVY, pad=12)
        ax.text(.98, .93, '+13.5% from 1 to 100,000',
                transform=ax.transAxes, ha='right', va='top',
                fontsize=9, color=INK, fontweight='bold')
        ax.set_xticks([1, 10, 100, 1000, 10000, 100000])
        ax.set_xticklabels(['1','10','100','1k','10k','100k'])
        style(ax)
        return count
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
    rows=read_rows(DATA)
    measured=measured_by_case(read_rows(MEASURED))
    for panel in 'ABCD':
        fig,ax=plt.subplots(figsize=(7.35,5.05),layout='constrained')
        chart(ax,panel,rows,measured)
        save(fig,f'Figure3_{panel}')
    fig,axes=plt.subplots(2,2,figsize=(15.2,10.1),layout='constrained')
    for ax,panel in zip(axes.ravel(),'ABCD'):chart(ax,panel,rows,measured)
    # Figure-level title is in the journal caption, not inside the artwork.
    # Bottom left figure information is included in legend, not on the axes.
    save(fig,'Figure3_NEXCISION_scalability')
    print('WROTE: Figure 3 replicate-level plots (A=30, B=30, C=15, D=30; 75 distinct runs); frozen v0.1.0 data')

if __name__=='__main__':main()
