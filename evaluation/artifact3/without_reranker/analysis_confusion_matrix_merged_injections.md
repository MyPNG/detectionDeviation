# Analysis Confusion Matrix (Merged Injections)

- Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/rea_no_injections.json`
- Actual: `/Users/my/Documents/projects/detectionDeviation/evaluation/artifact3/without_reranker/merged_llm_extracted_normalized.json`

- TP: 4
- FP: 1
- FN: 5
- TN: 29
- Precision: 0.8
- Recall: 0.444444
- F1: 0.571429
- Accuracy: 0.846154

| ID | Gold Standard | System Output | Result |
|---|---|---|---|
| art13(1) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art13(2) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art14(1) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art14(2) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art15(1) | Deviation (True) | Deviation (True) | True Positive (Hit) |
| art17(1) | Deviation (True) | Deviation (True) | True Positive (Hit) |
| art21(1) | Deviation (True) | Deviation (True) | True Positive (Hit) |
| art21(2) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art6(1) | Deviation (True) | Deviation (True) | True Positive (Hit) |
| art77(1) | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| Others (29) | Non-Deviation (False) | Non-Deviation (False) | True Negatives |
