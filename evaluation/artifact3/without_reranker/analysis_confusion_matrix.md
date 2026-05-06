# Analysis Confusion Matrix

- Evaluated chunks: 12
- Skipped chunks: 0

## Overall Calculation Matrix

- TP: 2
- FP: 5
- FN: 10
- TN: 152
- Precision: 0.285714
- Recall: 0.166667
- F1: 0.210526
- Accuracy: 0.911243

## Chunk: chunk1

### Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/chunk1/output.json`
### Actual: `/Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_03/chunk1/llm_extracted_normalized.json`

| ID | Gold Standard | System Output | Result |
|---|---|---|---|
| REG-013 | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| REG-017 | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| REG-021 | Deviation (True) | Deviation (True) | True Positive (Hit) |
| REG-025 | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| REG-028 | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| REG-032 | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| REG-035 | Deviation (True) | Deviation (True) | True Positive (Hit) |
| Others (10) | Non-Deviation (False) | Non-Deviation (False) | True Negatives |

### Calculation Matrix

- TP: 2
- FP: 2
- FN: 3
- TN: 10
- Precision: 0.5
- Recall: 0.4
- F1: 0.444444

## Chunk: chunk2

### Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/chunk2/output.json`
### Actual: `/Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_03/chunk2/llm_response.json`

| ID | Gold Standard | System Output | Result |
|---|---|---|---|
| REG-092 | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| Others (5) | Non-Deviation (False) | Non-Deviation (False) | True Negatives |

### Calculation Matrix

- TP: 0
- FP: 1
- FN: 0
- TN: 5
- Precision: 0.0
- Recall: 0.0
- F1: 0.0

## Chunk: chunk3

### Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/chunk3/output.json`
### Actual: `/Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_03/chunk3/llm_response.json`

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

## Chunk: chunk 4

### Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/chunk 4/output.json`
### Actual: `/Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_03/chunk4/llm_response.json`

| ID | Gold Standard | System Output | Result |
|---|---|---|---|
| REG-001 | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| REG-012 | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| REG-016 | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| Others (16) | Non-Deviation (False) | Non-Deviation (False) | True Negatives |

### Calculation Matrix

- TP: 0
- FP: 0
- FN: 3
- TN: 16
- Precision: 0.0
- Recall: 0.0
- F1: 0.0

## Chunk: chunk5

### Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/chunk5/ouput.json`
### Actual: `/Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_03/chunk5/llm_response.json`

| ID | Gold Standard | System Output | Result |
|---|---|---|---|
| REG-001 | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| Others (10) | Non-Deviation (False) | Non-Deviation (False) | True Negatives |

### Calculation Matrix

- TP: 0
- FP: 1
- FN: 0
- TN: 10
- Precision: 0.0
- Recall: 0.0
- F1: 0.0

## Chunk: chunk6

### Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/chunk6/output.json`
### Actual: `/Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_03/chunk6/llm_response.json`

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

## Chunk: chunk7

### Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/chunk7/output.json`
### Actual: `/Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_03/chunk7/llm_response.json`

| ID | Gold Standard | System Output | Result |
|---|---|---|---|
| Others (17) | Non-Deviation (False) | Non-Deviation (False) | True Negatives |

### Calculation Matrix

- TP: 0
- FP: 0
- FN: 0
- TN: 17
- Precision: 0.0
- Recall: 0.0
- F1: 0.0

## Chunk: chunk8

### Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/chunk8/output.json`
### Actual: `/Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_03/chunk8/llm_response.json`

| ID | Gold Standard | System Output | Result |
|---|---|---|---|
| Others (15) | Non-Deviation (False) | Non-Deviation (False) | True Negatives |

### Calculation Matrix

- TP: 0
- FP: 0
- FN: 0
- TN: 15
- Precision: 0.0
- Recall: 0.0
- F1: 0.0

## Chunk: chunk9

### Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/chunk9/output.json`
### Actual: `/Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_03/chunk9/llm_response.json`

| ID | Gold Standard | System Output | Result |
|---|---|---|---|
| Others (10) | Non-Deviation (False) | Non-Deviation (False) | True Negatives |

### Calculation Matrix

- TP: 0
- FP: 0
- FN: 0
- TN: 10
- Precision: 0.0
- Recall: 0.0
- F1: 0.0

## Chunk: chunk10

### Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/chunk10/output.json`
### Actual: `/Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_03/chunk10/llm_response.json`

| ID | Gold Standard | System Output | Result |
|---|---|---|---|
| Others (17) | Non-Deviation (False) | Non-Deviation (False) | True Negatives |

### Calculation Matrix

- TP: 0
- FP: 0
- FN: 0
- TN: 17
- Precision: 0.0
- Recall: 0.0
- F1: 0.0

## Chunk: chunk11

### Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/chunk11/output.json`
### Actual: `/Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_03/chunk11/llm_response.json`

| ID | Gold Standard | System Output | Result |
|---|---|---|---|
| REG-025 | Non-Deviation (False) | Deviation (True) | False Positive (Alarm) |
| Others (17) | Non-Deviation (False) | Non-Deviation (False) | True Negatives |

### Calculation Matrix

- TP: 0
- FP: 1
- FN: 0
- TN: 17
- Precision: 0.0
- Recall: 0.0
- F1: 0.0

## Chunk: chunk12

### Expected: `/Users/my/Documents/projects/detectionDeviation/goldstandard/chunk12/output.json`
### Actual: `/Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_03/chunk12/llm_response.json`

| ID | Gold Standard | System Output | Result |
|---|---|---|---|
| REG-013 | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| REG-017 | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| REG-035 | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| REG-036 | Deviation (True) | Non-Deviation (False) | False Negative (Miss) |
| Others (10) | Non-Deviation (False) | Non-Deviation (False) | True Negatives |

### Calculation Matrix

- TP: 0
- FP: 0
- FN: 4
- TN: 10
- Precision: 0.0
- Recall: 0.0
- F1: 0.0
