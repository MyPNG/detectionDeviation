# Retrieval Confusion Matrix (Clause Relevance)

- Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/eu_ai_injections_relevant_clauses.json`
- Actual: `/Users/my/Documents/projects/detectionDeviation/evaluation/artifact3/case3_v3/merged_main_clauses_deduplicated.csv`

- Precision: 0.340909
- Recall: 0.882353
- F1: 0.491803

| | Retrieved (System found it) | Not Retrieved (System missed it) |
|---|---:|---:|
| Relevant (Gold Standard) | 15 (True Positives) | 2 (False Negatives) |
| Irrelevant (Gold Standard) | 29 (False Positives) | 0 (True Negatives) |

## Missed Relevant Clauses

art9(1), art9(5)

## False Positive Clauses

art10(1), art10(2(a)), art10(2(b)), art10(2(c)), art10(2(d)), art10(2(e)), art10(2(h)), art10(6), art12(3(a)), art13(1), art13(3(b)), art13(3(i)), art13(7), art13(8(e)), art14(2), art14(3(a)), art14(3(b)), art14(4(a)), art14(4(b)), art14(4(c)), art14(4(d)), art14(4(e)), art15(1), art15(2), art15(4), art8(1), art9(2(d)), art9(4), art9(9)

## Retrieved Clauses Not Listed In Gold JSON

None
