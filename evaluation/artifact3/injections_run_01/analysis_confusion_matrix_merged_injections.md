# Analysis Confusion Matrix (Merged Injections)

- Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/rea_with_injections.json`
- Actual: `/Users/my/Documents/projects/detectionDeviation/evaluation/artifact3/injections_run_01/merged_llm_extracted_normalized.json`

- TP: 4
- FP: 4
- FN: 3
- TN: 7
- Precision: 0.5
- Recall: 0.571429
- F1: 0.533333
- Accuracy: 0.611111

| ID | Gold Standard | System Output | Result |
|---|---|---|---|
| art12(3) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art13 | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| art14(2) | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| art14(4) | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| art15(1) | Deviation (True) | Deviation (True) | True Positive (Hit) |
| art16 | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art17 | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| art20(1) | Deviation (True) | Deviation (True) | True Positive (Hit) |
| art21 | Deviation (True) | Deviation (True) | True Positive (Hit) |
| art33 | Deviation (True) | Deviation (True) | True Positive (Hit) |
| art34 | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| Others (7) | Non-Deviation (False) | Non-Deviation (False) | True Negatives |
