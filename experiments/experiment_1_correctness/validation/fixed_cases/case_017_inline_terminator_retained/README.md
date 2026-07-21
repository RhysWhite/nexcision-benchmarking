# Fixed validation case 017 inline terminator retained: inline terminator on retained row

The matrix semicolon is appended to the final retained row. Filtering an earlier row must preserve that inline terminator exactly.

Run this case from the repository root with:

```bash
python validation/run_fixed_cases.py --case case_017_inline_terminator_retained
```
