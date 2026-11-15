# Usefulness judge: pipeline vs v8 alone (deepseek-flash)

115 turns where the pipeline ran a lookup; each judged in both orders; win = wins both orders.

| Group | Turns | Pipeline more useful | v8 alone more useful | Tie |
|---|---|---|---|---|
| All | 115 | 33 | 14 | 68 |
| Reply cites a lookup | 31 | 22 | 4 | 5 |
| Lookup ran, reply cites none | 84 | 11 | 10 | 63 |
| category med_question | 32 | 17 | 5 | 10 |
| category red_flag | 77 | 14 | 9 | 54 |
| category scope | 3 | 2 | 0 | 1 |
| category style | 3 | 0 | 0 | 3 |

Order disagreements (counted as tie): 28 of 115.
