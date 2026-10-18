# Extract run extract_v0_deepseek-flash_t0.3_1018-1707

Prompt A `extract_v0`, model `deepseek-flash`, temperature 0.3. OCR: Tesseract (--psm 6). 66 label images.

## Field accuracy by style

| Style | Labels | All 3 fields correct | Name correct | Strength correct | Directions correct | Unreadable fields | **Wrong names** |
|---|---|---|---|---|---|---|---|
| clean | 22 | 20 | 22 | 20 | 22 | 0 | 0 |
| blur | 22 | 15 | 22 | 18 | 19 | 0 | 0 |
| tilt | 22 | 6 | 18 | 12 | 11 | 0 | 4 |
| all | 66 | 41 | 62 | 50 | 52 | 0 | 4 |

Cost per label: $0.00008 (all 66 labels: $0.0050). Latency p50: 0.90s. Invalid JSON: 0.

## Wrong fields (first 30)

- **label-03 / tilt**: got {'name': 'Lisinoptl', 'strength': '40 m9'}; truth {'name': 'Lisinopril', 'strength': '10 mg'}
- **label-04 / tilt**: got {'strength': '40 mg'}; truth {'strength': '10 mg'}
- **label-05 / tilt**: got {'name': 'ibuprofen', 'directions': 'take as needed for pain'}; truth {'name': 'Advil (ibuprofen)', 'directions': 'Take 1 to 2 tablets every 4 to 6 hours as needed for pain'}
- **label-06 / blur**: got {'directions': 'Take 1 tablet by mouth twice daily, 6 AM and 2 PM'}; truth {'directions': 'Take 1 tablet by mouth twice daily, 8 AM and 2 PM'}
- **label-06 / tilt**: got {'directions': 'Take one tablet at 8AM and 2PM'}; truth {'directions': 'Take 1 tablet by mouth twice daily, 8 AM and 2 PM'}
- **label-07 / tilt**: got {'directions': 'Take 1 tablet by mouth in the morning'}; truth {'directions': 'Take 1 tablet by mouth once daily in the morning'}
- **label-08 / tilt**: got {'strength': '40 mg', 'directions': 'Take one tablet by mouth in the morning'}; truth {'strength': '10 mg', 'directions': 'Take 1 tablet by mouth once daily in the morning'}
- **label-11 / blur**: got {'directions': 'Take 2 tablets by mouth terce daily'}; truth {'directions': 'Take 2 tablets by mouth twice daily'}
- **label-11 / tilt**: got {'strength': '209'}; truth {'strength': '20 mg'}
- **label-13 / tilt**: got {'name': "Lisinopt'l"}; truth {'name': 'Lisinopril'}
- **label-14 / blur**: got {'strength': '25MG'}; truth {'strength': '25MG TAB'}
- **label-14 / tilt**: got {'strength': '25M6 TAB', 'directions': '1 TAB POBIO'}; truth {'strength': '25MG TAB', 'directions': '1 TAB PO BID'}
- **label-15 / clean**: got {'strength': '50MG'}; truth {'strength': '50MG TB24'}
- **label-15 / blur**: got {'strength': '50MG'}; truth {'strength': '50MG TB24'}
- **label-15 / tilt**: got {'strength': '50MG', 'directions': '4 TAB PO QAM'}; truth {'strength': '50MG TB24', 'directions': '1 TAB PO QAM'}
- **label-16 / clean**: got {'strength': '40MG'}; truth {'strength': '40MG TAB'}
- **label-16 / blur**: got {'strength': '40MG'}; truth {'strength': '40MG TAB'}
- **label-16 / tilt**: got {'directions': '1 TAB POBIO'}; truth {'directions': '1 TAB PO BID'}
- **label-17 / blur**: got {'strength': '10MG'}; truth {'strength': '10MG TAB'}
- **label-17 / tilt**: got {'strength': '40MG TAB', 'directions': '1 TAB PO OAM'}; truth {'strength': '10MG TAB', 'directions': '1 TAB PO QAM'}
- **label-18 / blur**: got {'directions': 'Take one tablet at 6 AM and one tablet at 2 PM'}; truth {'directions': 'Take one tablet at 8 AM and one tablet at 2 PM'}
- **label-18 / tilt**: got {'directions': 'Take ps0 guess'}; truth {'directions': 'Take one tablet at 8 AM and one tablet at 2 PM'}
- **label-20 / tilt**: got {'name': 'Lisinoptl', 'strength': '40 m9'}; truth {'name': 'Lisinopril', 'strength': '10 mg'}
- **label-21 / tilt**: got {'strength': '8.6mo', 'directions': 'Take > tablets at bectime as nended or constipation'}; truth {'strength': '8.6 mg', 'directions': 'Take 2 tablets at bedtime as needed for constipation'}
- **label-22 / tilt**: got {'strength': '40 mg-12.5 mo', 'directions': 'take 1 tablet py mouth once daily'}; truth {'strength': '10 mg-12.5 mg', 'directions': 'Take 1 tablet by mouth once daily'}

## End to end (blur labels → extract → Prompt B v3 → flag scoring)

| Case | Overall | Flags | Critical | Caught | Missed | False alarms |
|---|---|---|---|---|---|---|
| dx-01 | pass | pass | pass | 4 | 0 | 0 |
| dx-02 | pass | pass | pass | 5 | 0 | 0 |
| dx-06 | pass | pass | pass | 1 | 0 | 0 |
