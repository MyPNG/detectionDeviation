# Deviation Prompt

- id: REA-05#2
- top_k: 3
- reranked_json: /Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_01_rea_with_injections__reg_for_injectiontest_reranked/chunk5_deontic_stages/rea-05#2.json
- used_reg_ids: REG-002, REG-108, REG-062

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
id: REA-05#2
text: "This minimal build SHALL process personal data such as: the unique User ID set by Google Analytics, the date and time, the title of the page being viewed, the URL of the page being viewed, the URL of the page that was viewed prior to the current page, the screen resolution, the time in local timezone, the files that were clicked on and downloaded, the links clicked on to an outside domain, the type of device, and the country, region, and city."
slots:
actor: This minimal build
modal: Mandatory(shall)
action: process
actions: process
object: personal data such as: the unique User ID set by Google Analytics, the date and time, the title of the page being viewed, the URL of the page being viewed, the URL of the page that was viewed prior to the current page, the screen resolution, the time in local timezone, the files that were clicked on and downloaded, the links clicked on to an outside domain, the type of device, and the country, region, and city.
temporal: prior to the current page
condition: 
manner: by Google Analytics

MAIN REG MATCHES
1. REG-002
clause: Art6(1(a))
text: "Processing shall be lawful only if and to the extent that at least one of the following applies: (a) the data subject has given consent to the processing of his or her personal data for one or more specific purposes;"
slots:
actor: Processing
modal: 
action: be lawful
actions: be lawful
object: only if and to the extent that at least one of the following applies: (a) the data subject has given consent to the processing of his or her personal data for one or more specific purposes;
temporal: following applies
condition: if and to the extent that at least one of the following applies
manner: 
graph_context:
- id: REG-001
  edge_type: PARENT_CHILD
  direction: incoming
  hop_count: 1
  relation_path: REG-001 -> REG-002
  text: "Processing shall be lawful only if and to the extent that at least one of the following applies:"
- id: REG-003
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-002 <- REG-001 -> REG-003
  text: "Processing shall be lawful only if and to the extent that at least one of the following applies: (b) processing is necessary for the performance of a contract to which the data subject is party or in order to take steps at the request of the data subject prior to entering into a contract;"
- id: REG-004
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-002 <- REG-001 -> REG-004
  text: "Processing shall be lawful only if and to the extent that at least one of the following applies: (c) processing is necessary for compliance with a legal obligation to which the controller is subject;"
- id: REG-005
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-002 <- REG-001 -> REG-005
  text: "Processing shall be lawful only if and to the extent that at least one of the following applies: (d) processing is necessary in order to protect the vital interests of the data subject or of another natural person;"
- id: REG-006
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-002 <- REG-001 -> REG-006
  text: "Processing shall be lawful only if and to the extent that at least one of the following applies: (e) processing is necessary for the performance of a task carried out in the public interest or in the exercise of official authority vested in the controller;"
- id: REG-007
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-002 <- REG-001 -> REG-007
  text: "Processing shall be lawful only if and to the extent that at least one of the following applies: (f) processing is necessary for the purposes of the legitimate interests pursued by the controller or by a third party, except where such interests are overridden by the interests or fundamental rights and freedoms of the data subject which require protection of personal data, in particular where the data subject is a child. Point (f) of the first subparagraph shall not apply to processing carried out by public authorities in the performance of their tasks."

2. REG-108
clause: Art15(3)
text: "The controller shall provide a copy of the personal data undergoing processing."
slots:
actor: The controller
modal: 
action: provide
actions: provide
object: a copy of the personal data undergoing processing.
temporal: 
condition: 
manner: 
graph_context:
- id: REG-109
  edge_type: SEQUENCE
  direction: incoming
  hop_count: 1
  relation_path: REG-109 -> REG-108
  text: "For any further copies requested by the data subject, the controller may charge a reasonable fee based on administrative costs."

3. REG-062
clause: Art13(2)
text: "In addition to the information referred to in paragraph 1, the controller shall, at the time when personal data are obtained, provide the data subject with the following further information necessary to ensure fair and transparent processing:"
slots:
actor: the controller
modal: 
action: refer
actions: refer
object: addition to the information referred to in paragraph 1
temporal: following further information necessary to ensure
condition: when personal data are obtained
manner: 
graph_context:
- id: REG-055
  edge_type: REFERENCES
  direction: outgoing
  hop_count: 1
  relation_path: REG-062 -> REG-055
  text: "Where personal data relating to a data subject are collected from the data subject, the controller shall, at the time when personal data are obtained, provide the data subject with all of the following information:"
- id: REG-063
  edge_type: PARENT_CHILD
  direction: outgoing
  hop_count: 1
  relation_path: REG-062 -> REG-063
  text: "In addition to the information referred to in paragraph 1, the controller shall, at the time when personal data are obtained, provide the data subject with the following further information necessary to ensure fair and transparent processing: (a) the period for which the personal data will be stored, or if that is not possible, the criteria used to determine that period;"
- id: REG-064
  edge_type: PARENT_CHILD
  direction: outgoing
  hop_count: 1
  relation_path: REG-062 -> REG-064
  text: "In addition to the information referred to in paragraph 1, the controller shall, at the time when personal data are obtained, provide the data subject with the following further information necessary to ensure fair and transparent processing: (b) the existence of the right to request from the controller access to and rectification or erasure of personal data or restriction of processing concerning the data subject or to object to processing as well as the right to data portability;"
- id: REG-065
  edge_type: PARENT_CHILD
  direction: outgoing
  hop_count: 1
  relation_path: REG-062 -> REG-065
  text: "In addition to the information referred to in paragraph 1, the controller shall, at the time when personal data are obtained, provide the data subject with the following further information necessary to ensure fair and transparent processing: (c) where the processing is based on point (a) of Article 6(1) or point (a) of Article 9(2), the existence of the right to withdraw consent at any time, without affecting the lawfulness of processing based on consent before its withdrawal;"
- id: REG-066
  edge_type: PARENT_CHILD
  direction: outgoing
  hop_count: 1
  relation_path: REG-062 -> REG-066
  text: "In addition to the information referred to in paragraph 1, the controller shall, at the time when personal data are obtained, provide the data subject with the following further information necessary to ensure fair and transparent processing: (d) the right to lodge a complaint with a supervisory authority;"
- id: REG-067
  edge_type: PARENT_CHILD
  direction: outgoing
  hop_count: 1
  relation_path: REG-062 -> REG-067
  text: "In addition to the information referred to in paragraph 1, the controller shall, at the time when personal data are obtained, provide the data subject with the following further information necessary to ensure fair and transparent processing: (e) whether the provision of personal data is a statutory or contractual requirement, or a requirement necessary to enter into a contract, as well as whether the data subject is obliged to provide the personal data and of the possible consequences of failure to provide such data;"
- id: REG-068
  edge_type: PARENT_CHILD
  direction: outgoing
  hop_count: 1
  relation_path: REG-062 -> REG-068
  text: "In addition to the information referred to in paragraph 1, the controller shall, at the time when personal data are obtained, provide the data subject with the following further information necessary to ensure fair and transparent processing: (f) the existence of automated decision-making, including profiling, referred to in Article 22(1) and (4) and, at least in those cases, meaningful information about the logic involved, as well as the significance and the envisaged consequences of such processing for the data subject."

REQUIRED REG IDS
REG-002, REG-108, REG-062

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
  "id": "REA-05#2",
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
