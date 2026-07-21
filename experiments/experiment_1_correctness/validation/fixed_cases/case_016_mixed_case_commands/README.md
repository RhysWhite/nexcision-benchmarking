# Fixed validation case 016 mixed case commands: mixed command capitalisation

NEXUS commands use mixed capitalisation and spaces around dimension assignments. Capitalisation and spacing must remain unchanged except for `NCHAR` changing from 6 to 5.

Run this case from the repository root with:

```bash
python validation/run_fixed_cases.py --case case_016_mixed_case_commands
```
