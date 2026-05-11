# Analysis Confusion Matrix

- Evaluated chunks: 11
- Skipped chunks: 1

## Overall Calculation Matrix

- TP: 3
- FP: 4
- FN: 9
- TN: 100
- Precision: 0.428571
- Recall: 0.25
- F1: 0.315789
- Accuracy: 0.887931

## Chunk: chunk1

### Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/chunk1/output.json`
### Actual: `/Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_03_reranked_overlapwindows/chunk1/llm_response.json`

| ID | Gold Standard | System Output | Result |
|---|---|---|---|
| REG-013 | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| REG-017 | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| REG-021 | Deviation (True) | Deviation (True) | True Positive (Hit) |
| REG-025 | Deviation (True) | Deviation (True) | True Positive (Hit) |
| REG-027 | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| REG-032 | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| REG-035 | Deviation (True) | Deviation (True) | True Positive (Hit) |
| Others (10) | Non-Deviation (False) | Non-Deviation (False) | True Negatives |

### Calculation Matrix

- TP: 3
- FP: 2
- FN: 2
- TN: 10
- Precision: 0.6
- Recall: 0.6
- F1: 0.6

### Deviation Count Matrix

- Hit: 3
- Miss: 3
- Alarm: 2
- Gold Total: 6
- System Total: 5
- Count Precision: 0.6
- Count Recall: 0.5

| ID | Gold Deviations | System Deviations | Hit | Miss | Alarm |
|---|---:|---:|---:|---:|---:|
| REG-013 | 1 | 0 | 0 | 1 | 0 |
| REG-017 | 1 | 0 | 0 | 1 | 0 |
| REG-021 | 1 | 1 | 1 | 0 | 0 |
| REG-025 | 1 | 1 | 1 | 0 | 0 |
| REG-027 | 0 | 1 | 0 | 0 | 1 |
| REG-032 | 0 | 1 | 0 | 0 | 1 |
| REG-035 | 2 | 1 | 1 | 1 | 0 |

## Chunk: chunk2

### Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/chunk2/output.json`
### Actual: `/Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_03_reranked_overlapwindows/chunk2/llm_response.json`

| ID | Gold Standard | System Output | Result |
|---|---|---|---|
| REG-092 | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| Others (4) | Non-Deviation (False) | Non-Deviation (False) | True Negatives |

### Calculation Matrix

- TP: 0
- FP: 1
- FN: 0
- TN: 4
- Precision: 0.0
- Recall: 0.0
- F1: 0.0

### Deviation Count Matrix

- Hit: 0
- Miss: 0
- Alarm: 1
- Gold Total: 0
- System Total: 1
- Count Precision: 0.0
- Count Recall: 0.0

| ID | Gold Deviations | System Deviations | Hit | Miss | Alarm |
|---|---:|---:|---:|---:|---:|
| REG-092 | 0 | 1 | 0 | 0 | 1 |

## Chunk: chunk3

### Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/chunk3/output.json`
### Actual: `/Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_03_reranked_overlapwindows/chunk3/llm_response.json`

| ID | Gold Standard | System Output | Result |
|---|---|---|---|
| Others (9) | Non-Deviation (False) | Non-Deviation (False) | True Negatives |

### Calculation Matrix

- TP: 0
- FP: 0
- FN: 0
- TN: 9
- Precision: 0.0
- Recall: 0.0
- F1: 0.0

### Deviation Count Matrix

- Hit: 0
- Miss: 0
- Alarm: 0
- Gold Total: 0
- System Total: 0
- Count Precision: 0.0
- Count Recall: 0.0

| ID | Gold Deviations | System Deviations | Hit | Miss | Alarm |
|---|---:|---:|---:|---:|---:|

## Chunk: chunk 4

### Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/chunk 4/output.json`
### Actual: `/Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_03_reranked_overlapwindows/chunk4/llm_response.json`

| ID | Gold Standard | System Output | Result |
|---|---|---|---|
| REG-001 | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| REG-012 | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| REG-016 | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| Others (7) | Non-Deviation (False) | Non-Deviation (False) | True Negatives |

### Calculation Matrix

- TP: 0
- FP: 0
- FN: 3
- TN: 7
- Precision: 0.0
- Recall: 0.0
- F1: 0.0

### Deviation Count Matrix

- Hit: 0
- Miss: 3
- Alarm: 0
- Gold Total: 3
- System Total: 0
- Count Precision: 0.0
- Count Recall: 0.0

| ID | Gold Deviations | System Deviations | Hit | Miss | Alarm |
|---|---:|---:|---:|---:|---:|
| REG-001 | 1 | 0 | 0 | 1 | 0 |
| REG-012 | 1 | 0 | 0 | 1 | 0 |
| REG-016 | 1 | 0 | 0 | 1 | 0 |

## Chunk: chunk5

### Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/chunk5/ouput.json`
### Actual: `/Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_03_reranked_overlapwindows/chunk5/llm_response.json`

| ID | Gold Standard | System Output | Result |
|---|---|---|---|
| Others (8) | Non-Deviation (False) | Non-Deviation (False) | True Negatives |

### Calculation Matrix

- TP: 0
- FP: 0
- FN: 0
- TN: 8
- Precision: 0.0
- Recall: 0.0
- F1: 0.0

### Deviation Count Matrix

- Hit: 0
- Miss: 0
- Alarm: 0
- Gold Total: 0
- System Total: 0
- Count Precision: 0.0
- Count Recall: 0.0

| ID | Gold Deviations | System Deviations | Hit | Miss | Alarm |
|---|---:|---:|---:|---:|---:|

## Chunk: chunk6

### Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/chunk6/output.json`
### Actual: `/Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_03_reranked_overlapwindows/chunk6/llm_response.json`

| ID | Gold Standard | System Output | Result |
|---|---|---|---|
| Others (11) | Non-Deviation (False) | Non-Deviation (False) | True Negatives |

### Calculation Matrix

- TP: 0
- FP: 0
- FN: 0
- TN: 11
- Precision: 0.0
- Recall: 0.0
- F1: 0.0

### Deviation Count Matrix

- Hit: 0
- Miss: 0
- Alarm: 0
- Gold Total: 0
- System Total: 0
- Count Precision: 0.0
- Count Recall: 0.0

| ID | Gold Deviations | System Deviations | Hit | Miss | Alarm |
|---|---:|---:|---:|---:|---:|

## Chunk: chunk7

### Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/chunk7/output.json`
### Actual: `/Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_03_reranked_overlapwindows/chunk7/llm_response.json`

| ID | Gold Standard | System Output | Result |
|---|---|---|---|
| Others (12) | Non-Deviation (False) | Non-Deviation (False) | True Negatives |

### Calculation Matrix

- TP: 0
- FP: 0
- FN: 0
- TN: 12
- Precision: 0.0
- Recall: 0.0
- F1: 0.0

### Deviation Count Matrix

- Hit: 0
- Miss: 0
- Alarm: 0
- Gold Total: 0
- System Total: 0
- Count Precision: 0.0
- Count Recall: 0.0

| ID | Gold Deviations | System Deviations | Hit | Miss | Alarm |
|---|---:|---:|---:|---:|---:|

## Chunk: chunk8

### Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/chunk8/output.json`
### Actual: `/Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_03_reranked_overlapwindows/chunk8/llm_response.json`

| ID | Gold Standard | System Output | Result |
|---|---|---|---|
| Others (13) | Non-Deviation (False) | Non-Deviation (False) | True Negatives |

### Calculation Matrix

- TP: 0
- FP: 0
- FN: 0
- TN: 13
- Precision: 0.0
- Recall: 0.0
- F1: 0.0

### Deviation Count Matrix

- Hit: 0
- Miss: 0
- Alarm: 0
- Gold Total: 0
- System Total: 0
- Count Precision: 0.0
- Count Recall: 0.0

| ID | Gold Deviations | System Deviations | Hit | Miss | Alarm |
|---|---:|---:|---:|---:|---:|

## Chunk: chunk9

### Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/chunk9/output.json`
### Actual: `/Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_03_reranked_overlapwindows/chunk9/llm_response.json`

| ID | Gold Standard | System Output | Result |
|---|---|---|---|
| Others (8) | Non-Deviation (False) | Non-Deviation (False) | True Negatives |

### Calculation Matrix

- TP: 0
- FP: 0
- FN: 0
- TN: 8
- Precision: 0.0
- Recall: 0.0
- F1: 0.0

### Deviation Count Matrix

- Hit: 0
- Miss: 0
- Alarm: 0
- Gold Total: 0
- System Total: 0
- Count Precision: 0.0
- Count Recall: 0.0

| ID | Gold Deviations | System Deviations | Hit | Miss | Alarm |
|---|---:|---:|---:|---:|---:|

## Chunk: chunk11

### Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/chunk11/output.json`
### Actual: `/Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_03_reranked_overlapwindows/chunk11/llm_response.json`

| ID | Gold Standard | System Output | Result |
|---|---|---|---|
| REG-025 | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| Others (10) | Non-Deviation (False) | Non-Deviation (False) | True Negatives |

### Calculation Matrix

- TP: 0
- FP: 1
- FN: 0
- TN: 10
- Precision: 0.0
- Recall: 0.0
- F1: 0.0

### Deviation Count Matrix

- Hit: 0
- Miss: 0
- Alarm: 1
- Gold Total: 0
- System Total: 1
- Count Precision: 0.0
- Count Recall: 0.0

| ID | Gold Deviations | System Deviations | Hit | Miss | Alarm |
|---|---:|---:|---:|---:|---:|
| REG-025 | 0 | 1 | 0 | 0 | 1 |

## Chunk: chunk12

### Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/chunk12/output.json`
### Actual: `/Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_03_reranked_overlapwindows/chunk12/llm_response.json`

| ID | Gold Standard | System Output | Result |
|---|---|---|---|
| REG-013 | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| REG-017 | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| REG-035 | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| REG-036 | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| Others (8) | Non-Deviation (False) | Non-Deviation (False) | True Negatives |

### Calculation Matrix

- TP: 0
- FP: 0
- FN: 4
- TN: 8
- Precision: 0.0
- Recall: 0.0
- F1: 0.0

### Deviation Count Matrix

- Hit: 0
- Miss: 4
- Alarm: 0
- Gold Total: 4
- System Total: 0
- Count Precision: 0.0
- Count Recall: 0.0

| ID | Gold Deviations | System Deviations | Hit | Miss | Alarm |
|---|---:|---:|---:|---:|---:|
| REG-013 | 1 | 0 | 0 | 1 | 0 |
| REG-017 | 1 | 0 | 0 | 1 | 0 |
| REG-035 | 1 | 0 | 0 | 1 | 0 |
| REG-036 | 1 | 0 | 0 | 1 | 0 |

## Skipped

- chunk10: system output json missing
