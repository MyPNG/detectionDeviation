# Deviation Prompt

- id: REA-04#3
- top_k: 3
- reranked_json: /Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_01_rea_with_injections__reg_for_injectiontest_reranked/chunk4_deontic_stages/rea-04#3.json
- used_reg_ids: REG-112, REG-114, REG-116

## System Prompt
```text
You are a legal compliance deviation assessor.

Compare the REA and REG primarily using the raw text.
Use the logical slots only to structure the comparison and focus on these dimensions:
- actor
- modal
- action
- object
- temporal
- condition
- manner
- sequence
- negation

Use graph context only as supporting legal context when provided.
Use it only to clarify the meaning, scope, order, alternatives, or parent-child structure of the main REG clauses.
Do not let graph context override the main REG text unless it clearly resolves ambiguity.

Your task is to determine whether and where the REA deviates from the REG.
A deviation exists only if there is a meaning-changing mismatch supported by the provided text.

Important rules:
1. Treat raw clause text as the authoritative evidence.
2. Treat logical slots as guidance, not as the final source of truth.
3. Use graph context only when needed to interpret the REG.
4. Do not use external knowledge.
5. Do not treat omission alone as a deviation.
6. Do not assume that shared verbs imply the same constraint.
7. Only classify a deviation when the quoted REA and REG spans clearly express the same or directly conflicting constraint.
8. Prefer Non-Deviation if the evidence is ambiguous.
9. For every deviation, quote the exact REA span and exact REG span that support the mismatch.
10. If no quote-supported mismatch exists, return Non-Deviation.

Deviation categories:
- responsibility = different actor
- modal_force = different obligation, permission, or prohibition
- action = different required action
- object_scope = different target or scope
- temporal = different timing, frequency, deadline, or duration
- condition = different if, when, unless, or provided-that condition
- manner = different method or format
- sequence = different order of steps
- negation = reversed, added, or removed negative constraint
- other = quote-supported mismatch not covered above

Return JSON only using this exact schema:
{
  "id": "REA-XX#Y",
  "per_reg_comparisons": [
    {
      "reg_id": "REG-XXX",
      "comparison": {
        "raw_text_alignment": "aligned|partially_aligned|not_aligned|unclear",
        "actor_similarity": "similar|different|unclear|missing",
        "modal_similarity": "similar|different|unclear|missing",
        "action_similarity": "similar|different|unclear|missing",
        "actions_similarity": "similar|different|unclear|missing",
        "object_similarity": "similar|different|unclear|missing",
        "temporal_similarity": "similar|different|unclear|missing"
      },
      "deviation": true,
      "types": ["temporal"],
      "evidence_rea": ["..."],
      "evidence_reg": ["..."],
      "reasoning_short": "...",
      "confidence": "low|medium|high",
      "needs_more_context": false
    }
  ],
  "overall_deviation": true,
  "overall_confidence": "low|medium|high"
}
```

## User Prompt
```text
REA FOCUS UNIT
id: REA-04#3
text: "The Data Controller removes the data upon your request."
slots:
actor: The Data Controller
modal: Mandatory
action: remove
actions: remove
object: the data
temporal: upon your request
condition: upon your request
manner: 

MAIN REG MATCHES
1. REG-112
clause: Art17(1)
text: "The data subject shall have the right to obtain from the controller the erasure of personal data concerning him or her without undue delay"
slots:
actor: The data subject
modal: 
action: have
actions: have
object: the right to obtain from the controller the erasure of personal data concerning him or her without undue delay
temporal: without undue delay
condition: 
manner: 
graph_context:
- id: REG-113
  edge_type: AND
  direction: incoming
  hop_count: 1
  relation_path: REG-113 -> REG-112
  text: "and the controller shall have the obligation to erase personal data without undue delay where one of the following grounds applies:"

2. REG-114
clause: Art17(1(a))
text: "The data subject shall have the right to obtain from the controller the erasure of personal data concerning him or her without undue delay"
slots:
actor: The data subject
modal: 
action: have
actions: have
object: the right to obtain from the controller the erasure of personal data concerning him or her without undue delay
temporal: without undue delay
condition: 
manner: 
graph_context:
- id: REG-115
  edge_type: AND
  direction: incoming
  hop_count: 1
  relation_path: REG-115 -> REG-114
  text: "and the controller shall have the obligation to erase personal data without undue delay where one of the following grounds applies: (a) the personal data are no longer necessary in relation to the purposes for which they were collected or otherwise processed;"

3. REG-116
clause: Art17(1(b))
text: "The data subject shall have the right to obtain from the controller the erasure of personal data concerning him or her without undue delay"
slots:
actor: The data subject
modal: 
action: have
actions: have
object: the right to obtain from the controller the erasure of personal data concerning him or her without undue delay
temporal: without undue delay
condition: 
manner: 
graph_context:
- id: REG-117
  edge_type: AND
  direction: incoming
  hop_count: 1
  relation_path: REG-117 -> REG-116
  text: "and the controller shall have the obligation to erase personal data without undue delay where one of the following grounds applies: (b) the data subject withdraws consent on which the processing is based according to point (a) of Article 6(1), or point (a) of Article 9(2), and where there is no other legal ground for the processing;"

REQUIRED REG IDS
REG-112, REG-114, REG-116

INSTRUCTIONS
1. Compare the REA and REG primarily using the raw text.
2. Use the slots only as checklist hints (actor/modal/action/object/condition/temporal/manner/sequence/negation).
3. For each REG, first align the two constraints, then report slot comparison judgments for actor/modal/action/actions/object/temporal in the comparison block.
4. Use these labels for each comparison field: similar | different | unclear | missing.
5. Every deviation claim must include evidence spans from both REA and REG.
6. Do not assume that shared verbs imply the same constraint.
7. Only classify a deviation when the quoted REA and REG spans clearly express the same or directly conflicting constraint.
8. Do not treat omission alone as a deviation.
9. If evidence is ambiguous or weak for a REG comparison, set deviation=false, confidence=low, and needs_more_context=true for that REG.
10. Return exactly one per_reg_comparisons entry for each REG ID listed under REQUIRED REG IDS. No missing IDs and no extra IDs.
11. Return JSON only in this schema:

{
  "id": "REA-04#3",
  "per_reg_comparisons": [
    {
      "reg_id": "REG-XXX",
      "comparison": {
        "raw_text_alignment": "aligned | partially_aligned | not_aligned | unclear",
        "actor_similarity": "similar | different | unclear | missing",
        "modal_similarity": "similar | different | unclear | missing",
        "action_similarity": "similar | different | unclear | missing",
        "actions_similarity": "similar | different | unclear | missing",
        "object_similarity": "similar | different | unclear | missing",
        "temporal_similarity": "similar | different | unclear | missing"
      },
      "deviation": true,
      "types": ["responsibility | modal_force | action | object_scope | temporal | condition | manner | sequence | negation | other"],
      "evidence_rea": ["...exact quote span(s)..."],
      "evidence_reg": ["...exact quote span(s)..."],
      "reasoning_short": "...one concise explanation...",
      "confidence": "low | medium | high",
      "needs_more_context": false
    }
  ],
  "overall_deviation": true,
  "overall_confidence": "low | medium | high"
}
```
