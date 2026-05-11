# Analysis Confusion Matrix (Merged Injections)

- Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/eu_ai_injections.json`
- Actual: `/Users/my/Documents/projects/detectionDeviation/evaluation/artifact3/rea_case3_injections/merged_llm_extracted_normalized.json`

- TP: 9
- FP: 10
- FN: 7
- TN: 24
- Precision: 0.473684
- Recall: 0.5625
- F1: 0.514286
- Accuracy: 0.66

## Deviation Count Matrix

- Hit: 9
- Miss: 20
- Alarm: 10
- Gold Total: 29
- System Total: 19
- Count Precision: 0.473684
- Count Recall: 0.310345

| ID | Gold Deviations | System Deviations | Hit | Miss | Alarm |
|---|---:|---:|---:|---:|---:|
| art10(1) | 0 | 1 | 0 | 0 | 1 |
| art10(2) | 1 | 1 | 1 | 0 | 0 |
| art10(3) | 1 | 1 | 1 | 0 | 0 |
| art10(4) | 0 | 1 | 0 | 0 | 1 |
| art10(6) | 0 | 1 | 0 | 0 | 1 |
| art11(1) | 3 | 0 | 0 | 3 | 0 |
| art13(1) | 0 | 1 | 0 | 0 | 1 |
| art13(2) | 1 | 0 | 0 | 1 | 0 |
| art13(3) | 2 | 1 | 1 | 1 | 0 |
| art13(4) | 1 | 0 | 0 | 1 | 0 |
| art13(7)(vi) | 0 | 1 | 0 | 0 | 1 |
| art13(8) | 1 | 1 | 1 | 0 | 0 |
| art14(1) | 1 | 1 | 1 | 0 | 0 |
| art14(2) | 0 | 1 | 0 | 0 | 1 |
| art14(3) | 4 | 1 | 1 | 3 | 0 |
| art14(4) | 2 | 1 | 1 | 1 | 0 |
| art15(1) | 0 | 1 | 0 | 0 | 1 |
| art15(3) | 1 | 0 | 0 | 1 | 0 |
| art26(4) | 0 | 1 | 0 | 0 | 1 |
| art8(1) | 0 | 1 | 0 | 0 | 1 |
| art9(1) | 1 | 0 | 0 | 1 | 0 |
| art9(2) | 3 | 1 | 1 | 2 | 0 |
| art9(4) | 0 | 1 | 0 | 0 | 1 |
| art9(5) | 2 | 0 | 0 | 2 | 0 |
| art9(6) | 4 | 1 | 1 | 3 | 0 |
| art9(8) | 1 | 0 | 0 | 1 | 0 |

| ID | Gold Standard | System Output | Result |
|---|---|---|---|
| art10(1) | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| art10(2) | Deviation (True) | Deviation (True) | True Positive (Hit) |
| art10(3) | Deviation (True) | Deviation (True) | True Positive (Hit) |
| art10(4) | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| art10(6) | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| art11(1) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art13(1) | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| art13(2) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art13(3) | Deviation (True) | Deviation (True) | True Positive (Hit) |
| art13(4) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art13(7)(vi) | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| art13(8) | Deviation (True) | Deviation (True) | True Positive (Hit) |
| art14(1) | Deviation (True) | Deviation (True) | True Positive (Hit) |
| art14(2) | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| art14(3) | Deviation (True) | Deviation (True) | True Positive (Hit) |
| art14(4) | Deviation (True) | Deviation (True) | True Positive (Hit) |
| art15(1) | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| art15(3) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art26(4) | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| art8(1) | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| art9(1) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art9(2) | Deviation (True) | Deviation (True) | True Positive (Hit) |
| art9(4) | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| art9(5) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| art9(6) | Deviation (True) | Deviation (True) | True Positive (Hit) |
| art9(8) | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| Others (24) | Non-Deviation (False) | Non-Deviation (False) | True Negatives |
