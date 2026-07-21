# Fixed validation case 013 comments blank lines: comments and blank lines

Whole-line NEXUS comments and blank lines inside the matrix must remain in their original positions. Only `CP013831_180` and the required `nchar` value may change.

Run this case from the repository root with:

```bash
python validation/run_fixed_cases.py --case case_013_comments_blank_lines
```
