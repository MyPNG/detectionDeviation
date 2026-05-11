# Deviation Prompt

- id: REA-04#1
- top_k: 3
- reranked_json: /Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_01_rea_with_injections__reg_for_injectiontest_reranked/chunk4_deontic_stages/rea-04#1.json
- used_reg_ids: REG-059, REG-080, REG-055

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
id: REA-04#1
text: "Based on our legitimate interests, we collect the following data for the purpose of running this website."
slots:
actor: we
modal: Mandatory
action: base
actions: base
object: our legitimate interests
temporal: following data for the purpose of
condition: for the purpose of running this website
manner: 

MAIN REG MATCHES
1. REG-059
clause: Art13(1(d))
text: "Where personal data relating to a data subject are collected from the data subject, the controller shall, at the time when personal data are obtained, provide the data subject with all of the following information: (d) where the processing is based on point (f) of Article 6(1), the legitimate interests pursued by the controller or by a third party;"
slots:
actor: the controller
modal: 
action: relate
actions: relate
object: a data subject
temporal: following information
condition: Where personal data relating to a data subject are collected from the data subject
manner: by the controller or by a third party
graph_context:
- id: REG-055
  edge_type: PARENT_CHILD
  direction: incoming
  hop_count: 1
  relation_path: REG-055 -> REG-059
  text: "Where personal data relating to a data subject are collected from the data subject, the controller shall, at the time when personal data are obtained, provide the data subject with all of the following information:"
- id: REG-056
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-059 <- REG-055 -> REG-056
  text: "Where personal data relating to a data subject are collected from the data subject, the controller shall, at the time when personal data are obtained, provide the data subject with all of the following information: (a) the identity and the contact details of the controller and, where applicable, of the controller's representative;"
- id: REG-057
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-059 <- REG-055 -> REG-057
  text: "Where personal data relating to a data subject are collected from the data subject, the controller shall, at the time when personal data are obtained, provide the data subject with all of the following information: (b) the contact details of the data protection officer, where applicable;"
- id: REG-058
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-059 <- REG-055 -> REG-058
  text: "Where personal data relating to a data subject are collected from the data subject, the controller shall, at the time when personal data are obtained, provide the data subject with all of the following information: (c) the purposes of the processing for which the personal data are intended as well as the legal basis for the processing;"
- id: REG-060
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-059 <- REG-055 -> REG-060
  text: "Where personal data relating to a data subject are collected from the data subject, the controller shall, at the time when personal data are obtained, provide the data subject with all of the following information: (e) the recipients or categories of recipients of the personal data, if any;"
- id: REG-061
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-059 <- REG-055 -> REG-061
  text: "Where personal data relating to a data subject are collected from the data subject, the controller shall, at the time when personal data are obtained, provide the data subject with all of the following information: (f) where applicable, the fact that the controller intends to transfer personal data to a third country or international organisation and the existence or absence of an adequacy decision by the Commission, or in the case of transfers referred to in Article 46 or 47, or the second subparagraph of Article 49(1), reference to the appropriate or suitable safeguards and the means by which to obtain a copy of them or where they have been made available."

2. REG-080
clause: Art14(2(b))
text: "In addition to the information referred to in paragraph 1, the controller shall provide the data subject with the following information necessary to ensure fair and transparent processing in respect of the data subject: (b) where the processing is based on point (f) of Article 6(1), the legitimate interests pursued by the controller or by a third party;"
slots:
actor: the controller
modal: 
action: provide
actions: provide
object: the data subject with the following information necessary to ensure fair and transparent processing in respect of the data subject: (b) where the processing is based on point (f) of Article 6(1), the legitimate interests pursued by the controller or by a third party;
temporal: following information necessary to ensure fair
condition: where the processing is based on point (f) of Article 6(1)
manner: by the controller or by a third party
graph_context:
- id: REG-071
  edge_type: REFERENCES
  direction: outgoing
  hop_count: 1
  relation_path: REG-080 -> REG-071
  text: "Where personal data have not been obtained from the data subject, the controller shall provide the data subject with the following information:"
- id: REG-078
  edge_type: PARENT_CHILD
  direction: incoming
  hop_count: 1
  relation_path: REG-078 -> REG-080
  text: "In addition to the information referred to in paragraph 1, the controller shall provide the data subject with the following information necessary to ensure fair and transparent processing in respect of the data subject:"
- id: REG-079
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-080 <- REG-078 -> REG-079
  text: "In addition to the information referred to in paragraph 1, the controller shall provide the data subject with the following information necessary to ensure fair and transparent processing in respect of the data subject: (a) the period for which the personal data will be stored, or if that is not possible, the criteria used to determine that period;"
- id: REG-081
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-080 <- REG-078 -> REG-081
  text: "In addition to the information referred to in paragraph 1, the controller shall provide the data subject with the following information necessary to ensure fair and transparent processing in respect of the data subject: (c) the existence of the right to request from the controller access to and rectification or erasure of personal data or restriction of processing concerning the data subject and to object to processing as well as the right to data portability;"
- id: REG-082
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-080 <- REG-078 -> REG-082
  text: "In addition to the information referred to in paragraph 1, the controller shall provide the data subject with the following information necessary to ensure fair and transparent processing in respect of the data subject: (d) where processing is based on point (a) of Article 6(1) or point (a) of Article 9(2), the existence of the right to withdraw consent at any time, without affecting the lawfulness of processing based on consent before its withdrawal;"
- id: REG-083
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-080 <- REG-078 -> REG-083
  text: "In addition to the information referred to in paragraph 1, the controller shall provide the data subject with the following information necessary to ensure fair and transparent processing in respect of the data subject: (e) the right to lodge a complaint with a supervisory authority;"
- id: REG-084
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-080 <- REG-078 -> REG-084
  text: "In addition to the information referred to in paragraph 1, the controller shall provide the data subject with the following information necessary to ensure fair and transparent processing in respect of the data subject: (f) from which source the personal data originate, and if applicable, whether it came from publicly accessible sources;"
- id: REG-085
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-080 <- REG-078 -> REG-085
  text: "In addition to the information referred to in paragraph 1, the controller shall provide the data subject with the following information necessary to ensure fair and transparent processing in respect of the data subject: (g) the existence of automated decision-making, including profiling, referred to in Article 22(1) and (4) and, at least in those cases, meaningful information about the logic involved, as well as the significance and the envisaged consequences of such processing for the data subject."

3. REG-055
clause: Art13(1)
text: "Where personal data relating to a data subject are collected from the data subject, the controller shall, at the time when personal data are obtained, provide the data subject with all of the following information:"
slots:
actor: the controller
modal: 
action: relate
actions: relate
object: a data subject
temporal: following information
condition: Where personal data relating to a data subject are collected from the data subject
manner: 
graph_context:
- none

REQUIRED REG IDS
REG-059, REG-080, REG-055

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
  "id": "REA-04#1",
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
