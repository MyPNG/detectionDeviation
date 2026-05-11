# Retrieval Confusion Matrix (Article Relevance)

- Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/relevant_non_relevant_requirements_case3.json`
- Actual: `/Users/my/Documents/projects/detectionDeviation/evaluation/artifact3/case3_v3/merged_main_clauses_deduplicated.csv`

- Precision: 0.875
- Recall: 1.0
- F1: 0.933333

| | Retrieved (System found it) | Not Retrieved (System missed it) |
|---|---:|---:|
| Relevant (Gold Standard) | 7 (True Positives) | 0 (False Negatives) |
| Irrelevant (Gold Standard) | 1 (False Positives) | 5 (True Negatives) |

## Missed Relevant Articles

None

## False Positive Articles

Article 12

## Retrieved Articles Not Listed In Gold JSON

None
