# Deviation Prompt

- id: REA-01#4
- top_k: 5
- reranked_json: /Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_01_case3_v3_reranked/chunk1_deontic_stages/rea-01#4.json
- used_reg_ids: REG-073, REG-075, REG-066, REG-005, REG-022

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
id: REA-01#4
text: "shall not document the effort using the Impact Assessment template provided by the Office of Responsible AI."
slots:
actor: 
modal: Prohibited(shall not)
action: document
actions: document
object: the effort using the Impact Assessment template provided by the Office of Responsible AI.
temporal: by the Office of Responsible AI
condition: 
manner: by the Office of Responsible AI

MAIN REG MATCHES
1. REG-073
clause: Art13(6)
text: "The Provider SHALL provide information that is relevant to explain the high-risk AI system's output where applicable, and describe the technical capabilities and characteristics of the high-risk AI system."
slots:
actor: The Provider
modal: Mandatory
action: provide
actions: provide
object: information that is relevant to explain the high-risk AI system's output where applicable, and describe the technical capabilities and characteristics of the high-risk AI system.
temporal: 
condition: where applicable
manner: where applicable, and describe

2. REG-075
clause: Art13(7)
text: "The Developer SHALL take into account the intended purpose of the high-risk AI system when appropriate, specifying for the input data, or any other relevant information in terms of the training, validation and testing data sets used;"
slots:
actor: The Developer
modal: Mandatory
action: take
actions: take
object: into account the intended purpose of the high-risk AI system when appropriate, specifying for the input data, or any other relevant information in terms of the training, validation and testing data sets used;
temporal: when appropriate
condition: when appropriate
manner: specifying for the input data, or any other relevant information in terms of the training, validation and testing data sets used

3. REG-066
clause: Art13(2)
text: "The Deployer SHALL accompany high-risk AI systems with instructions for use in an appropriate digital format or otherwise that include concise, complete, correct and clear information that is relevant, accessible and comprehensible to deployers."
slots:
actor: The Deployer
modal: Mandatory(shall)
action: accompany
actions: accompany
object: high-risk AI systems with instructions for use in an appropriate digital format or otherwise that include concise, complete, correct and clear information that is relevant, accessible and comprehensible to deployers.
temporal: 
condition: that include concise, complete, correct and clear information that is relevant, accessible and comprehensible to deployers
manner: in an appropriate digital format or otherwise

4. REG-005
clause: Art9(1)
text: "The Organization SHALL establish, implement, document, and maintain a risk management system in relation to high-risk AI systems."
slots:
actor: The Organization
modal: Mandatory(shall)
action: establish
actions: establish | implement | document | and
object: implement, document, and maintain a risk management system in relation to high-risk AI systems.
temporal: 
condition: 
manner: 

5. REG-022
clause: Art9(8)
text: "Testing shall be carried out against prior defined metrics and probabilistic thresholds that are appropriate to the intended purpose of the high-risk AI system."
slots:
actor: Testing
modal: Mandatory(shall)
action: carried
actions: carried
object: out against prior defined metrics and probabilistic thresholds that are appropriate to the intended purpose of the high-risk AI system.
temporal: 
condition: 
manner: 

REQUIRED REG IDS
REG-073, REG-075, REG-066, REG-005, REG-022

GRAPH CONTEXT
- none provided in this prompt build

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
  "id": "REA-01#4",
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
