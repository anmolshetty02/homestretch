# Extract run extract_v2_deepseek-flash_t0.3_1018-1711

Prompt A `extract_v2`, model `deepseek-flash`, temperature 0.3. OCR: Tesseract (--psm 6). 66 label images.

## Field accuracy by style

| Style | Labels | All 3 fields correct | Name correct | Strength correct | Directions correct | Unreadable fields | **Wrong names** |
|---|---|---|---|---|---|---|---|
| clean | 22 | 22 | 22 | 22 | 22 | 0 | 0 |
| blur | 22 | 13 | 22 | 16 | 18 | 7 | 0 |
| tilt | 22 | 1 | 18 | 5 | 10 | 29 | 0 |
| all | 66 | 36 | 62 | 43 | 50 | 36 | 0 |

Cost per label: $0.00013 (all 66 labels: $0.0083). Latency p50: 1.04s. Invalid JSON: 0.

## Wrong fields (first 30)

- **label-06 / blur**: got {'directions': 'Take 1 tablet by mouth twice daily, 6 AM and 2 PM'}; truth {'directions': 'Take 1 tablet by mouth twice daily, 8 AM and 2 PM'}
- **label-11 / blur**: got {'directions': 'Take 2 tablets by mouth once daily'}; truth {'directions': 'Take 2 tablets by mouth twice daily'}
- **label-15 / tilt**: got {'strength': '50MG', 'directions': '4 TAB PO QAM'}; truth {'strength': '50MG TB24', 'directions': '1 TAB PO QAM'}
- **label-17 / tilt**: got {'strength': '40MG TAB', 'directions': '1 TAB PO OAM'}; truth {'strength': '10MG TAB', 'directions': '1 TAB PO QAM'}
- **label-18 / blur**: got {'directions': 'Take one tablet at 6 AM and one tablet at 2 PM'}; truth {'directions': 'Take one tablet at 8 AM and one tablet at 2 PM'}

## End to end (blur labels → extract → Prompt B v3 → flag scoring)

| Case | Overall | Flags | Critical | Caught | Missed | False alarms |
|---|---|---|---|---|---|---|
| dx-01 | pass | pass | pass | 4 | 0 | 0 |
| dx-02 | pass | pass | pass | 5 | 0 | 0 |
| dx-06 | pass | warn | pass | 1 | 0 | 0 |
