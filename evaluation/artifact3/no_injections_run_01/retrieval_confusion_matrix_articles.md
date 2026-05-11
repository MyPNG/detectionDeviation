# Retrieval Confusion Matrix (Article Relevance)

- Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/relevant_non_relevant_articles_no_injections.json`
- Actual: `/Users/my/Documents/projects/detectionDeviation/evaluation/artifact3/no_injections_run_01/merged_main_clauses_deduplicated.csv`

- Precision: 0.714286
- Recall: 1.0
- F1: 0.833333

| | Retrieved (System found it) | Not Retrieved (System missed it) |
|---|---:|---:|
| Relevant (Gold Standard) | 10 (True Positives) | 0 (False Negatives) |
| Irrelevant (Gold Standard) | 4 (False Positives) | 9 (True Negatives) |

## Missed Relevant Articles

None

## False Positive Articles

Article 45, Article 49, Article 78, Article 9

## Retrieved Articles Not Listed In Gold JSON

None
