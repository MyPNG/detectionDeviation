# Retrieval Confusion Matrix (Article Relevance)

- Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/relevant_non_relevant_requirements_case3.json`
- Actual: `/Users/my/Documents/projects/detectionDeviation/evaluation/artifact3/rea_case3_injections/merged_main_clauses_deduplicated.csv`

- Precision: 0.583333
- Recall: 1.0
- F1: 0.736842

| | Retrieved (System found it) | Not Retrieved (System missed it) |
|---|---:|---:|
| Relevant (Gold Standard) | 7 (True Positives) | 0 (False Negatives) |
| Irrelevant (Gold Standard) | 5 (False Positives) | 3 (True Negatives) |

## Missed Relevant Articles

None

## False Positive Articles

Article 26, Article 49, Article 60, Article 79, Article 89

## Retrieved Articles Not Listed In Gold JSON

Article 49, Article 89
