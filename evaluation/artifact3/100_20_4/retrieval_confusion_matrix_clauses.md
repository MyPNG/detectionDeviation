# Retrieval Confusion Matrix (Clause Relevance)

- Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/eu_ai_injections_relevant_clauses.json`
- Actual: `/Users/my/Documents/projects/detectionDeviation/evaluation/artifact3/100_20_4/merged_main_clauses_deduplicated.csv`

- Precision: 0.150943
- Recall: 0.470588
- F1: 0.228571

| | Retrieved (System found it) | Not Retrieved (System missed it) |
|---|---:|---:|
| Relevant (Gold Standard) | 8 (True Positives) | 9 (False Negatives) |
| Irrelevant (Gold Standard) | 45 (False Positives) | 0 (True Negatives) |

## Missed Relevant Clauses

art10(2), art10(3), art10(4), art11(1), art13(8), art15(3), art9(5), art9(6), art9(8)

## False Positive Clauses

art13(1), art14(2), art14(5), art15(1), art15(2), art17(1), art17(2), art17(3), art18(1), art18(2), art18(3), art20(1), art20(2), art20(3), art21(1), art21(2), art21(3), art21(4), art22(2), art26(3), art40(3), art42(2), art42(3), art42(8), art45(1), art45(2), art45(7), art46(1), art46(2), art46(3), art47(3), art49(1), art49(2), art49(4), art49(5), art49(6), art6(1), art6(3), art77(1), art77(2), art78(2), art89(1), art9(3), art93(2), art93(3)

## Retrieved Clauses Not Listed In Gold JSON

None
