# Extract run extract_v1_deepseek-flash_t0.3_1018-1709

Prompt A `extract_v1`, model `deepseek-flash`, temperature 0.3. OCR: Tesseract (--psm 6). 66 label images.

## Field accuracy by style

| Style | Labels | All 3 fields correct | Name correct | Strength correct | Directions correct | Unreadable fields | **Wrong names** |
|---|---|---|---|---|---|---|---|
| clean | 22 | 22 | 22 | 22 | 22 | 0 | 0 |
| blur | 22 | 19 | 22 | 21 | 20 | 0 | 0 |
| tilt | 22 | 9 | 21 | 14 | 14 | 7 | 0 |
| all | 66 | 50 | 65 | 57 | 56 | 7 | 0 |

Cost per label: $0.00014 (all 66 labels: $0.0092). Latency p50: 1.02s. Invalid JSON: 0.

## Wrong fields (first 30)

- **label-03 / tilt**: got {'strength': '40 mg'}; truth {'strength': '10 mg'}
- **label-04 / tilt**: got {'strength': '40 mg'}; truth {'strength': '10 mg'}
- **label-06 / blur**: got {'directions': 'Take 1 tablet by mouth twice daily, 6 AM and 2 PM'}; truth {'directions': 'Take 1 tablet by mouth twice daily, 8 AM and 2 PM'}
- **label-08 / tilt**: got {'strength': '40 mg'}; truth {'strength': '10 mg'}
- **label-15 / blur**: got {'strength': '50 mg'}; truth {'strength': '50MG TB24'}
- **label-15 / tilt**: got {'strength': '50MG', 'directions': '4 TAB PO QAM'}; truth {'strength': '50MG TB24', 'directions': '1 TAB PO QAM'}
- **label-16 / tilt**: got {'directions': '1 TAB POBIO'}; truth {'directions': '1 TAB PO BID'}
- **label-17 / tilt**: got {'strength': '40MG TAB', 'directions': '1 TAB PO OAM'}; truth {'strength': '10MG TAB', 'directions': '1 TAB PO QAM'}
- **label-18 / blur**: got {'directions': 'Take one tablet at 6 AM and one tablet at 2 PM'}; truth {'directions': 'Take one tablet at 8 AM and one tablet at 2 PM'}
- **label-20 / tilt**: got {'strength': '40 mg'}; truth {'strength': '10 mg'}
- **label-22 / tilt**: got {'strength': '40 mg-12.5 mg'}; truth {'strength': '10 mg-12.5 mg'}

## End to end (blur labels → extract → Prompt B v3 → flag scoring)

| Case | Overall | Flags | Critical | Caught | Missed | False alarms |
|---|---|---|---|---|---|---|
| dx-01 | pass | pass | pass | 4 | 0 | 0 |
| dx-02 | pass | pass | pass | 5 | 0 | 0 |
| dx-06 | pass | pass | pass | 1 | 0 | 0 |
