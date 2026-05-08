# Analysis Confusion Matrix (Merged Injections)

- Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/eu_ai_injections.json`
- Actual: `/Users/my/Documents/projects/detectionDeviation/evaluation/artifact3/rea_case3_injections/merged_llm_extracted_normalized.json`

- TP: 6
- FP: 3
- FN: 10
- TN: 26
- Precision: 0.666667
- Recall: 0.375
- F1: 0.48
- Accuracy: 0.711111

| ID | Gold Standard | System Output | Result |
|---|---|---|---|
| art10(2) | Deviation (True) | Deviation (True) | True Positive (Hit) |
| art10(3) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art10(4) | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| art11(1) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art13(1) | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| art13(2) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art13(3) | Deviation (True) | Deviation (True) | True Positive (Hit) |
| art13(4) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art13(8) | Deviation (True) | Deviation (True) | True Positive (Hit) |
| art14(1) | Deviation (True) | Deviation (True) | True Positive (Hit) |
| art14(2) | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| art14(3) | Deviation (True) | Deviation (True) | True Positive (Hit) |
| art14(4) | Deviation (True) | Deviation (True) | True Positive (Hit) |
| art15(3) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art9(1) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art9(2) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art9(5) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art9(6) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art9(8) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| Others (26) | Non-Deviation (False) | Non-Deviation (False) | True Negatives |
