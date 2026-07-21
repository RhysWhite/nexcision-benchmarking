# Fixed validation case 018 inline terminator removed: inline terminator on removed final row

The final row carries the matrix semicolon and is selected for removal. NEXCISION must remove the row but preserve the semicolon as a standalone matrix terminator.

Run this case from the repository root with:

```bash
python validation/run_fixed_cases.py --case case_018_inline_terminator_removed
```
