# Analysis Confusion Matrix (Merged Injections)

- Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/rea_no_injections.json`
- Actual: `/Users/my/Documents/projects/detectionDeviation/evaluation/artifact3/schema_v2_outputs/merged_llm_extracted_normalized.json`

- TP: 4
- FP: 3
- FN: 5
- TN: 23
- Precision: 0.571429
- Recall: 0.444444
- F1: 0.5
- Accuracy: 0.771429

| ID | Gold Standard | System Output | Result |
|---|---|---|---|
| art13(1) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art13(2) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art14(1) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art14(2) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art15(1) | Deviation (True) | Deviation (True) | True Positive (Hit) |
| art17(1) | Deviation (True) | Deviation (True) | True Positive (Hit) |
| art17(3) | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| art20(2) | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| art21(1) | Deviation (True) | Deviation (True) | True Positive (Hit) |
| art21(2) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art6(1) | Deviation (True) | Deviation (True) | True Positive (Hit) |
| art77(1) | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| Others (23) | Non-Deviation (False) | Non-Deviation (False) | True Negatives |
