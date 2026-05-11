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
  "deviation": true,
  "types": ["temporal"],
  "evidence_rea": ["..."],
  "evidence_reg": ["..."],
  "reasoning_short": "...",
  "confidence": "low|medium|high",
  "needs_more_context": false
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

LOCAL REA SIBLING CONTEXT
- REA-01#3: "shall assess the impact of the system on people, organizations, and society by completing an Impact Assessment early in the system's development, typically when defining the product vision and requirements."
actor: 
modal: Mandatory(shall)
action: assess
actions: assess
object: the impact of the system on people, organizations, and society by completing an Impact Assessment early in the system's development, typically when defining the product vision and requirements.
temporal: by completing an Impact Assessment early
condition: when defining the product vision and requirements
manner: by completing an Impact Assessment early in the system's development

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

GRAPH CONTEXT
BELONGS_TO:
- [REG-005] outgoing -> Art9: ""
- [REG-022] outgoing -> Art9: ""
- [REG-066] outgoing -> Art13: ""
- [REG-073] outgoing -> Art13: ""
- [REG-075] outgoing -> Art13: ""
PARENT_CHILD:
- [REG-073] outgoing -> REG-074: "(iv) where applicable, the technical capabilities and characteristics of the high-risk AI system to provide information that is relevant to explain its output; (v) when appropriate, its performance regarding specific persons or groups of persons on which the system is intended to be used;"
REFERENCES:
- [REG-005] incoming -> REG-023: "When implementing the risk management system as provided for in paragraphs 1 to 7, providers shall give consideration to whether in view of its intended purpose the high-risk AI system is likely to have an adverse impact on persons under the age of 18 and, as appropriate, other vulnerable groups."
- [REG-005] incoming -> REG-024: "For providers of high-risk AI systems that are subject to requirements regarding internal risk management processes under other relevant provisions of Union law, the aspects provided in paragraphs 1 to 9 may be part of, or combined with, the risk management procedures established pursuant to that law."
SEQUENCE:
- [REG-022] outgoing -> REG-021: "The testing of high-risk AI systems shall be performed, as appropriate, at any time throughout the development process, and, in any event, prior to their being placed on the market or put into service."

INSTRUCTIONS
1. Compare the REA and REG primarily using the raw text.
2. Use the slots only as checklist hints (actor/modal/action/object/condition/temporal/manner/sequence/negation).
3. Use the local REA sibling context to resolve dependent references such as 'the results', 'that plan', 'those reviewers', or inherited actor/modal context.
4. Every deviation claim must include evidence spans from both REA and REG.
5. Do not assume that shared verbs imply the same constraint.
6. Only classify a deviation when the quoted REA and REG spans clearly express the same or directly conflicting constraint.
7. Do not treat omission alone as a deviation.
8. If evidence is ambiguous or weak, set deviation=false, confidence=low, and needs_more_context=true.
9. Return JSON only in this schema:

{
  "deviation": true,
  "types": ["responsibility | modal_force | action | object_scope | temporal | condition | manner | sequence | negation | other"],
  "evidence_rea": ["...exact quote span(s)..."],
  "evidence_reg": ["...exact quote span(s)..."],
  "reasoning_short": "...one concise explanation...",
  "confidence": "low | medium | high",
  "needs_more_context": false
}
```
