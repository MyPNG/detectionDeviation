# Retrieval Confusion Matrix (Clause Relevance)

- Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/eu_ai_injections_relevant_clauses.json`
- Actual: `/Users/my/Documents/projects/detectionDeviation/evaluation/artifact3/rea_case3_injections/merged_main_clauses_deduplicated.csv`

- Precision: 0.365854
- Recall: 0.882353
- F1: 0.517241

| | Retrieved (System found it) | Not Retrieved (System missed it) |
|---|---:|---:|
| Relevant (Gold Standard) | 15 (True Positives) | 2 (False Negatives) |
| Irrelevant (Gold Standard) | 26 (False Positives) | 0 (True Negatives) |

## Missed Relevant Clauses

art9(2), art9(5)

## False Positive Clauses

art10(1), art10(6), art13(1), art13(5), art13(6), art13(7), art14(2), art15(1), art15(2), art26(1), art26(12), art26(2), art26(3), art26(4), art26(9), art49(6), art60(2), art79(1), art79(5), art79(6), art8(1), art89(4), art9(10), art9(4), art9(7), art9(9)

## Retrieved Clauses Not Listed In Gold JSON

None
