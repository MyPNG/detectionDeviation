# Deviation Prompt

- id: REA-06#2
- top_k: 3
- reranked_json: /Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_01_rea_with_injections__reg_for_injectiontest_reranked/chunk6_deontic_stages/rea-06#2.json
- used_reg_ids: REG-053, REG-024, REG-091

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
id: REA-06#2
text: "Embedded content from other websites behaves in the exact same way as if the visitor had visited the other website."
slots:
actor: Embedded content from other websites
modal: 
action: embed
actions: embed
object: other websites
temporal: 
condition: if the visitor had visited the other website
manner: 

MAIN REG MATCHES
1. REG-053
clause: Art12(7)
text: "Where the icons are presented electronically they shall be machine-readable."
slots:
actor: the icons
modal: 
action: be machine-readable
actions: be machine-readable
object: .
temporal: 
condition: Where the icons are presented electronically they shall be machine-readable
manner: 
graph_context:
- id: REG-052
  edge_type: SEQUENCE
  direction: outgoing
  hop_count: 1
  relation_path: REG-053 -> REG-052
  text: "The information to be provided to data subjects pursuant to Articles 13 and 14 may be provided in combination with standardised icons in order to give in an easily visible, intelligible and clearly legible manner a meaningful overview of the intended processing."

2. REG-024
clause: Art9(2(e))
text: "Paragraph 1 shall not apply if one of the following applies: (e) processing relates to personal data which are manifestly made public by the data subject;"
slots:
actor: Paragraph 1
modal: 
action: apply
actions: apply
object: if one of the following applies: (e) processing relates to personal data which are manifestly made public by the data subject;
temporal: following applies
condition: if one of the following applies
manner: by the data subject
graph_context:
- id: REG-018
  edge_type: REFERENCES
  direction: outgoing
  hop_count: 1
  relation_path: REG-024 -> REG-018
  text: "Processing of personal data revealing racial or ethnic origin, political opinions, religious or philosophical beliefs, or trade union membership, and the processing of genetic data, biometric data for the purpose of uniquely identifying a natural person, data concerning health or data concerning a natural person's sex life or sexual orientation shall be prohibited."
- id: REG-019
  edge_type: PARENT_CHILD
  direction: incoming
  hop_count: 1
  relation_path: REG-019 -> REG-024
  text: "Paragraph 1 shall not apply if one of the following applies:"
- id: REG-020
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-024 <- REG-019 -> REG-020
  text: "Paragraph 1 shall not apply if one of the following applies: (a) the data subject has given explicit consent to the processing of those personal data for one or more specified purposes, except where Union or Member State law provide that the prohibition referred to in paragraph 1 may not be lifted by the data subject;"
- id: REG-021
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-024 <- REG-019 -> REG-021
  text: "Paragraph 1 shall not apply if one of the following applies: (b) processing is necessary for the purposes of carrying out the obligations and exercising specific rights of the controller or of the data subject in the field of employment and social security and social protection law in so far as it is authorised by Union or Member State law or a collective agreement pursuant to Member State law providing for appropriate safeguards for the fundamental rights and the interests of the data subject;"
- id: REG-022
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-024 <- REG-019 -> REG-022
  text: "Paragraph 1 shall not apply if one of the following applies: (c) processing is necessary to protect the vital interests of the data subject or of another natural person where the data subject is physically or legally incapable of giving consent;"
- id: REG-023
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-024 <- REG-019 -> REG-023
  text: "Paragraph 1 shall not apply if one of the following applies: (d) processing is carried out in the course of its legitimate activities with appropriate safeguards by a foundation, association or any other not-for-profit body with a political, philosophical, religious or trade union aim and on condition that the processing relates solely to the members or to former members of the body or to persons who have regular contact with it in connection with its purposes and that the personal data are not disclosed outside that body without the consent of the data subjects;"
- id: REG-025
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-024 <- REG-019 -> REG-025
  text: "Paragraph 1 shall not apply if one of the following applies: (f) processing is necessary for the establishment, exercise or defence of legal claims or whenever courts are acting in their judicial capacity;"
- id: REG-026
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-024 <- REG-019 -> REG-026
  text: "Paragraph 1 shall not apply if one of the following applies: (g) processing is necessary for reasons of substantial public interest, on the basis of Union"
- id: REG-027
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-024 <- REG-019 -> REG-027
  text: "or Member State law which shall be proportionate to the aim pursued, respect the essence of the right to data protection and provide for suitable and specific measures to safeguard the fundamental rights and the interests of the data subject;"
- id: REG-028
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-024 <- REG-019 -> REG-028
  text: "Paragraph 1 shall not apply if one of the following applies: (h) processing is necessary for the purposes of preventive or occupational medicine, for the assessment of the working capacity of the employee, medical diagnosis, the provision of health or social care or treatment or the management of health or social care systems and services on the basis of Union or Member State law or pursuant to contract with a health professional and subject to the conditions and safeguards referred to in paragraph 3;"
- id: REG-029
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-024 <- REG-019 -> REG-029
  text: "Paragraph 1 shall not apply if one of the following applies: (i) processing is necessary for reasons of public interest in the area of public health, such as protecting against serious cross-border threats to health or ensuring high standards of quality and safety of health care and of medicinal products or medical devices, on the basis of Union or Member State law which provides for suitable and specific measures to safeguard the rights and freedoms of the data subject, in particular professional secrecy;"
- id: REG-030
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-024 <- REG-019 -> REG-030
  text: "Paragraph 1 shall not apply if one of the following applies: (j) processing is necessary for archiving purposes in the public interest, scientific or historical research purposes or statistical purposes in accordance with Article 89(1) based on Union"
- id: REG-031
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-024 <- REG-019 -> REG-031
  text: "or Member State law which shall be propor­ tionate to the aim pursued, respect the essence of the right to data protection and provide for suitable and specific measures to safeguard the fundamental rights and the interests of the data subject."

3. REG-091
clause: Art14(5)
text: "Paragraphs 1 to 4 shall not apply where and insofar as:"
slots:
actor: Paragraphs 1 to 4
modal: 
action: apply
actions: apply
object: where and insofar as:
temporal: 
condition: where and insofar as
manner: 
graph_context:
- id: REG-071
  edge_type: REFERENCES
  direction: outgoing
  hop_count: 1
  relation_path: REG-091 -> REG-071
  text: "Where personal data have not been obtained from the data subject, the controller shall provide the data subject with the following information:"
- id: REG-092
  edge_type: PARENT_CHILD
  direction: outgoing
  hop_count: 1
  relation_path: REG-091 -> REG-092
  text: "Paragraphs 1 to 4 shall not apply where and insofar as: (a) the data subject already has the information;"
- id: REG-093
  edge_type: PARENT_CHILD
  direction: outgoing
  hop_count: 1
  relation_path: REG-091 -> REG-093
  text: "Paragraphs 1 to 4 shall not apply where and insofar as: (b) the provision of such information proves impossible or would involve a disproportionate effort, in particular for processing for archiving purposes in the public interest, scientific or historical research purposes or statistical purposes, subject to the conditions and safeguards referred to in Article 89(1) or in so far as the obligation referred to in paragraph 1 of this Article is likely to render impossible or seriously impair the achievement of the objectives of that processing."
- id: REG-094
  edge_type: PARENT_CHILD
  direction: outgoing
  hop_count: 1
  relation_path: REG-091 -> REG-094
  text: "In such cases the controller shall take appropriate measures to protect the data subject's rights and freedoms and legitimate interests, including making the information publicly available;"
- id: REG-095
  edge_type: PARENT_CHILD
  direction: outgoing
  hop_count: 1
  relation_path: REG-091 -> REG-095
  text: "Paragraphs 1 to 4 shall not apply where and insofar as: (c) obtaining or disclosure is expressly laid down by Union or Member State law to which the controller is subject and which provides appropriate measures to protect the data subject's legitimate interests or"
- id: REG-096
  edge_type: PARENT_CHILD
  direction: outgoing
  hop_count: 1
  relation_path: REG-091 -> REG-096
  text: "Paragraphs 1 to 4 shall not apply where and insofar as: (d) where the personal data must remain confidential subject to an obligation of professional secrecy regulated by Union or Member State law, including a statutory obligation of secrecy."

REQUIRED REG IDS
REG-053, REG-024, REG-091

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
  "id": "REA-06#2",
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
