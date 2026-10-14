#!/usr/bin/env python3
"""Independent, standard-library verification of the frozen Experiment 2 record.

All source statistics are recalculated from five measurements per configuration.
The verification is for NEXCISION v0.1.0, not a future v1.0.0 benchmark.
"""
from __future__ import annotations
import csv
import hashlib
import math
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / 'experiments/experiment_2_scalability/results/formal'
MEASURED = DATA / 'formal_measured-2432330.tsv'
SUMMARY = DATA / 'formal_summary-2432330.tsv'
EXPECTED = DATA / 'SOURCE_SHA256SUMS.txt'
KEY = DATA / 'derived/experiment2_key_results.tsv'


def load(path):
    with path.open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle, delimiter='\t'))


def equal(a, b, name, atol=1e-9):
    if not math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=atol):
        raise AssertionError(f'{name}: observed={a!r}, expected={b!r}')


def percentile(x, p):
    values = sorted(float(v) for v in x)
    h = (len(values) - 1) * p
    lo, hi = math.floor(h), math.ceil(h)
    return values[lo] + (h - lo) * (values[hi] - values[lo])


def linear_fit(x, y):
    x, y = list(map(float, x)), list(map(float, y))
    xm, ym = statistics.mean(x), statistics.mean(y)
    slope = sum((a-xm)*(b-ym) for a,b in zip(x,y))/sum((a-xm)**2 for a in x)
    intercept = ym-slope*xm
    residual = sum((b-(slope*a+intercept))**2 for a,b in zip(x,y))
    total = sum((b-ym)**2 for b in y)
    return slope, intercept, 1-residual/total


def main():
    for line in EXPECTED.read_text().splitlines():
        if not line.strip():
            continue
        checksum, filename = line.split(maxsplit=1)
        observed = hashlib.sha256((DATA / filename).read_bytes()).hexdigest()
        assert checksum == observed, f'Source digest mismatch: {filename}'
    measured, summary, key = load(MEASURED), load(SUMMARY), load(KEY)
    assert len(measured)==105 and len(summary)==21
    assert {x['case_id'] for x in summary} == {x['case_id'] for x in measured}
    assert all(x['returncode']=='0' and x['correct']=='True' for x in measured)
    assert all(x['all_correct']=='True' and x['deterministic_output']=='True' for x in summary)
    byid = defaultdict(list)
    for r in measured: byid[r['case_id']].append(r)
    for s in summary:
        group = byid[s['case_id']]
        assert len(group)==5 and sorted(int(r['repeat']) for r in group)==[1,2,3,4,5]
        assert len({r['filtered_sha256'] for r in group})==1
        for col, summary_col, factor in (
            ('elapsed_seconds','elapsed',1.0),
            ('peak_rss_bytes','peak_rss',1.0),
        ):
            arr = [float(q[col]) for q in group]
            for label, fn in (('median',statistics.median),('q1',lambda a: percentile(a,0.25)),('q3',lambda a:percentile(a,0.75))):
                equal(s[f'{summary_col}_{label}_'+('seconds' if col=='elapsed_seconds' else 'bytes')],fn(arr),f'{s["case_id"]} {col} {label}')
        equal(s['input_gib'],float(s['input_bytes'])/1024**3,f'{s["case_id"]} size')
        equal(s['peak_rss_median_gib'],float(s['peak_rss_median_bytes'])/1024**3,f'{s["case_id"]} rss')
    bykey = {r['metric']:float(r['value']) for r in key}
    sizes = sorted((s for s in summary if s['series']=='input_size'),key=lambda x:float(x['input_gib']))
    x=[float(s['input_gib']) for s in sizes]
    y=[float(s['elapsed_median_seconds']) for s in sizes]
    m=[float(s['peak_rss_median_gib']) for s in sizes]
    runtime_slope, runtime_int, runtime_r2 = linear_fit(x,y)
    mem_slope, mem_int, mem_r2 = linear_fit(x,m)
    power=[(math.log10(a),math.log10(b)) for a,b in zip(x,y) if a>=.09]
    exponent,_,_ = linear_fit([z[0] for z in power],[z[1] for z in power])
    for metric, val in (
        ('Runtime slope',runtime_slope),('Runtime linear-model R²',runtime_r2),
        ('Runtime log-log exponent (>=100 MB)', exponent),
        ('Peak-memory slope',mem_slope),('Peak-memory linear-model R²',mem_r2),
    ): equal(bykey[metric],val,metric)
    shape={s['case_id']:s for s in summary if s['series']=='matrix_shape'}
    ratio=float(shape['shape_tall']['elapsed_median_seconds'])/float(shape['shape_wide']['elapsed_median_seconds'])
    equal(bykey['Tall versus wide runtime ratio'],ratio,'tall/wide')
    intervals={s['case_id']:s for s in summary if s['series']=='interval_count'}
    delta=100*(float(intervals['intervals_100000']['elapsed_median_seconds'])/float(intervals['intervals_000001']['elapsed_median_seconds'])-1)
    equal(bykey['1 to 100,000 interval runtime increase'],delta,'interval overhead')
    assert runtime_int < 0, 'Review Panel A fit design if linear-model intercept changes'
    assert runtime_slope*x[0]+runtime_int < 0, 'Review Panel A fit design if negative prediction disappears'
    assert mem_int>0
    print('PASS: Figure 3 archived v0.1.0 measurements — 105/105 runs; 21/21 configurations; median/IQR; source hashes; linear and power-law models; matrix-shape and interval contrasts')
    print('NOTE: OLS runtime fit predicts negative runtime at the smallest size. Plot only the >=100 MB log-log fit as the visible dashed trend.')
    print('LIMIT: Validates archived v0.1.0 measurements, not independent rerun of benchmarks on the future release.')

if __name__=='__main__': main()
