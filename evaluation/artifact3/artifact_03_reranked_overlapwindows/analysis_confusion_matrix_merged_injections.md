# Analysis Confusion Matrix (Merged Injections)

- Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/rea_with_injections.json`
- Actual: `/Users/my/Documents/projects/detectionDeviation/evaluation/artifact3/artifact_03_reranked_overlapwindows/merged_llm_extracted_normalized.json`

- TP: 2
- FP: 3
- FN: 5
- TN: 21
- Precision: 0.4
- Recall: 0.285714
- F1: 0.333333
- Accuracy: 0.741935

## Deviation Count Matrix

- Hit: 2
- Miss: 6
- Alarm: 4
- Gold Total: 8
- System Total: 6
- Count Precision: 0.333333
- Count Recall: 0.25

| ID | Gold Deviations | System Deviations | Hit | Miss | Alarm |
|---|---:|---:|---:|---:|---:|
| art12(3) | 1 | 0 | 0 | 1 | 0 |
| art15(1) | 1 | 1 | 1 | 0 | 0 |
| art16 | 1 | 0 | 0 | 1 | 0 |
| art17 | 0 | 2 | 0 | 0 | 2 |
| art20(1) | 1 | 0 | 0 | 1 | 0 |
| art20(2) | 0 | 1 | 0 | 0 | 1 |
| art21 | 1 | 1 | 1 | 0 | 0 |
| art33 | 2 | 0 | 0 | 2 | 0 |
| art34 | 1 | 0 | 0 | 1 | 0 |
| art77(1) | 0 | 1 | 0 | 0 | 1 |

| ID | Gold Standard | System Output | Result |
|---|---|---|---|
| art12(3) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art15(1) | Deviation (True) | Deviation (True) | True Positive (Hit) |
| art16 | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art17 | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| art20(1) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art20(2) | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| art21 | Deviation (True) | Deviation (True) | True Positive (Hit) |
| art33 | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art34 | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art77(1) | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| Others (21) | Non-Deviation (False) | Non-Deviation (False) | True Negatives |
