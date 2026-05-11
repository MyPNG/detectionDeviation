# Analysis Confusion Matrix (Merged Injections)

- Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/rea_no_injections.json`
- Actual: `/Users/my/Documents/projects/detectionDeviation/evaluation/artifact3/100_20_4/merged_llm_extracted_normalized.json`

- TP: 3
- FP: 1
- FN: 6
- TN: 43
- Precision: 0.75
- Recall: 0.333333
- F1: 0.461538
- Accuracy: 0.867925

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
| art6(1) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art77(1) | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| Others (43) | Non-Deviation (False) | Non-Deviation (False) | True Negatives |
