#!/usr/bin/env python3
"""Verify the original NEXCISION v0.1.0 validation-stack numbers.

This checks preserved Experiment 1 output records. It DOES NOT rerun tests,
reconstruct the missing genuine inputs, or validate a future software release.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
VAL = ROOT / 'experiments/experiment_1_correctness/validation'


def rows(name: str) -> list[dict[str, str]]:
    with (VAL / name).open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle, delimiter='\t'))


def main() -> None:
    s = json.loads((VAL / 'experiment1_summary.json').read_text(encoding='utf-8'))
    t = json.loads((VAL / 'synthetic/case_1000_summary.json').read_text(encoding='utf-8'))
    p = rows('property/property_results.tsv')
    m = rows('mutation/mutation_results.tsv')
    r = rows('real_file_sanity_checks.tsv')
    v = rows('malformed_input_results.tsv')
    f = rows('fixed_case_manifest.tsv')
    safety = rows('safety_case_manifest.tsv')
    synthetic = rows('synthetic/case_1000_results.tsv')

    assert s['software_version'] == t['nexcision_version'] == '0.1.0'
    assert s['status'] == 'PASS' and s['acceptance_criteria_met']
    assert len(r) == 6 and len({x['file'] for x in r}) == 3
    assert all(x['retained_exact']=='True' and x['taxlabels_exact']=='True' and
               x['suffix_exact']=='True' and x['states_per_row_valid']=='True' for x in r)
    assert (s['real_spandx_matrices']['files'], s['real_spandx_matrices']['checks_passed']) == (3,6)
    assert len(f) == 17 and s['fixed_correctness_and_preservation_cases'] == {'cases':17,'passed':17}
    assert len(safety) == 1 and s['all_sites_safety_cases'] == {'cases':1,'passed':1}
    assert len(v) == 26 and all(x['overall']=='PASS' and x['no_unintended_outputs']=='PASS' and
                                 x['inputs_preserved']=='PASS' and x['temporary_files_removed']=='PASS' for x in v)
    assert s['malformed_input_and_output_safety_cases'] == {'cases':26,'passed':26}
    assert len(synthetic) == 1000 and all(x['overall']=='PASS' for x in synthetic)
    assert sum(int(x['nchar_before']) for x in synthetic) == 304000
    assert sum(int(x['rows_removed']) for x in synthetic) == 113740
    assert sum(int(x['rows_retained']) for x in synthetic) == 190260
    assert all(t[key] for key in ('all_oracle_agreement','all_retained_rows_exact',
                                   'all_dimensions_correct','all_region_counts_correct',
                                   'all_repeat_runs_deterministic'))
    assert (t['cases'], t['cases_passed'], t['total_site_rows']) == (1000,1000,304000)
    assert (t['total_rows_removed'],t['total_rows_retained']) == (113740,190260)
    assert len(p) == 9 and all(x['status']=='PASS' for x in p)
    assert sum(int(x['configured_examples']) for x in p) == 1800
    assert len(m) == 12 and all(x['status']=='KILLED' for x in m)
    assert s['mutation_testing']['mutants_killed'] == 12

    # Validate file-level provenance tied to the historical evidence.
    paths = {
        'malformed_input_results_tsv': 'malformed_input_results.tsv',
        'mutation_results_tsv': 'mutation/mutation_results.tsv',
        'property_results_tsv': 'property/property_results.tsv',
        'real_file_sanity_checks_tsv': 'real_file_sanity_checks.tsv',
        'synthetic_1000_results_tsv': 'synthetic/case_1000_results.tsv',
    }
    for key, location in paths.items():
        digest = hashlib.sha256((VAL / location).read_bytes()).hexdigest()
        assert digest == s['key_result_checksums'][key], f'SHA-256 mismatch: {location}'
    print('PASS: archived v0.1.0 Figure 2 evidence — 3 real matrices/6 checks, '
          '17 fixed + 1 safety, 26 malformed, 1,000 synthetic/304,000 rows, '
          '9 properties/1,800 examples, 12/12 mutants; source hashes verified')
    print('LIMIT: This validates archived records, not independent replay of inaccessible real inputs '
          'or a future v1.0.0 release.')


if __name__ == '__main__':
    main()
