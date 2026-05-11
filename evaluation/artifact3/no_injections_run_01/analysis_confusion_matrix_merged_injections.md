# Analysis Confusion Matrix (Merged Injections)

- Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/rea_no_injections.json`
- Actual: `/Users/my/Documents/projects/detectionDeviation/evaluation/artifact3/no_injections_run_01/merged_llm_extracted_normalized.json`

- TP: 3
- FP: 5
- FN: 6
- TN: 13
- Precision: 0.375
- Recall: 0.333333
- F1: 0.352941
- Accuracy: 0.592593

| ID | Gold Standard | System Output | Result |
|---|---|---|---|
| art13(1) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art13(2) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art14(1) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art14(2) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art15(1) | Deviation (True) | Deviation (True) | True Positive (Hit) |
| art17(1) | Deviation (True) | Deviation (True) | True Positive (Hit) |
| art17(3) | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| art18(1) | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| art20(2) | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| art21(1) | Deviation (True) | Deviation (True) | True Positive (Hit) |
| art21(2) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art45(1) | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| art6(1) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art77(1) | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| Others (13) | Non-Deviation (False) | Non-Deviation (False) | True Negatives |
