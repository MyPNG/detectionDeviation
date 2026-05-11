# Deviation Prompt

- id: REA-04#2
- top_k: 3
- reranked_json: /Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_01_rea_with_injections__reg_for_injectiontest_reranked/chunk4_deontic_stages/rea-04#2.json
- used_reg_ids: REG-032, REG-100, REG-097

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
id: REA-04#2
text: "Your data is not used by any other party or shared with third parties."
slots:
actor: Your data
modal: Prohibited
action: use
actions: use
object: any other party
temporal: by any other party or shared
condition: by any other party or shared with third parties
manner: by any other party or shared with third parties

MAIN REG MATCHES
1. REG-032
clause: Art9(3)
text: "Personal data referred to in paragraph 1 may be processed for the purposes referred to in point (h) of paragraph 2 when those data are processed by or under the responsibility of a professional subject to the obligation of professional secrecy under Union or Member State law or rules established by national competent bodies or by another person also subject to an obligation of secrecy under Union or Member State law or rules established by national competent bodies."
slots:
actor: Personal data referred to in paragraph 1
modal: 
action: process
actions: process
object: for the purposes referred to in point (h) of paragraph 2 when those data are processed by or under the responsibility of a professional subject to the obligation of professional secrecy under Union or Member State law or rules established by national competent bodies or by another person also subject to an obligation of secrecy under Union or Member State law or rules established by national competent bodies.
temporal: by or under the responsibility of
condition: when those data are processed by or under the responsibility of a professional subject to the obligation of professional secrecy under Union or Member State law or rules established by national competent bodies or by another person also subject to an obligation of secrecy under Union or Member State law or rules established by national competent bodies
manner: by or under the responsibility of a professional subject to the obligation of professional secrecy under Union or Member State law or rules established by national competent bodies or by another person also subject to an obligation of secrecy under Union or Member State law or rules established by national competent bodies
graph_context:
- id: REG-018
  edge_type: REFERENCES
  direction: outgoing
  hop_count: 1
  relation_path: REG-032 -> REG-018
  text: "Processing of personal data revealing racial or ethnic origin, political opinions, religious or philosophical beliefs, or trade union membership, and the processing of genetic data, biometric data for the purpose of uniquely identifying a natural person, data concerning health or data concerning a natural person's sex life or sexual orientation shall be prohibited."

2. REG-100
clause: Art15(1(c))
text: "The data subject shall have the right to obtain from the controller confirmation as to whether or not personal data concerning him or her are being processed, and, where that is the case, access to the personal data and the following information: (c) the recipients or categories of recipient to whom the personal data have been"
slots:
actor: The data subject
modal: 
action: have
actions: have
object: the right to obtain from the controller confirmation as to whether or not personal data concerning him or her are being processed, and, where that is the case, access to the personal data and the following information: (c) the recipients or categories of recipient to whom the personal data have been
temporal: following information
condition: where that is the case
manner: 
graph_context:
- id: REG-097
  edge_type: PARENT_CHILD
  direction: incoming
  hop_count: 1
  relation_path: REG-097 -> REG-100
  text: "The data subject shall have the right to obtain from the controller confirmation as to whether or not personal data concerning him or her are being processed, and, where that is the case, access to the personal data and the following information:"
- id: REG-098
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-100 <- REG-097 -> REG-098
  text: "The data subject shall have the right to obtain from the controller confirmation as to whether or not personal data concerning him or her are being processed, and, where that is the case, access to the personal data and the following information: (a) the purposes of the processing;"
- id: REG-099
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-100 <- REG-097 -> REG-099
  text: "The data subject shall have the right to obtain from the controller confirmation as to whether or not personal data concerning him or her are being processed, and, where that is the case, access to the personal data and the following information: (b) the categories of personal data concerned;"
- id: REG-101
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-100 <- REG-097 -> REG-101
  text: "or will be disclosed, in particular recipients in third countries or international organisations;"
- id: REG-102
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-100 <- REG-097 -> REG-102
  text: "The data subject shall have the right to obtain from the controller confirmation as to whether or not personal data concerning him or her are being processed, and, where that is the case, access to the personal data and the following information: (d) where possible, the envisaged period for which the personal data will be stored, or, if not possible, the criteria used to determine that period;"
- id: REG-103
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-100 <- REG-097 -> REG-103
  text: "The data subject shall have the right to obtain from the controller confirmation as to whether or not personal data concerning him or her are being processed, and, where that is the case, access to the personal data and the following information: (e) the existence of the right to request from the controller rectification or erasure of personal data or restriction of processing of personal data concerning the data subject or to object to such processing;"
- id: REG-104
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-100 <- REG-097 -> REG-104
  text: "The data subject shall have the right to obtain from the controller confirmation as to whether or not personal data concerning him or her are being processed, and, where that is the case, access to the personal data and the following information: (f) the right to lodge a complaint with a supervisory authority;"
- id: REG-105
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-100 <- REG-097 -> REG-105
  text: "The data subject shall have the right to obtain from the controller confirmation as to whether or not personal data concerning him or her are being processed, and, where that is the case, access to the personal data and the following information: (g) where the personal data are not collected from the data subject, any available information as to their source;"
- id: REG-106
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-100 <- REG-097 -> REG-106
  text: "The data subject shall have the right to obtain from the controller confirmation as to whether or not personal data concerning him or her are being processed, and, where that is the case, access to the personal data and the following information: (h) the existence of automated decision-making, including profiling, referred to in Article 22(1) and (4) and, at least in those cases, meaningful information about the logic involved, as well as the significance and the envisaged consequences of such processing for the data subject."

3. REG-097
clause: Art15(1)
text: "The data subject shall have the right to obtain from the controller confirmation as to whether or not personal data concerning him or her are being processed, and, where that is the case, access to the personal data and the following information:"
slots:
actor: The data subject
modal: 
action: have
actions: have
object: the right to obtain from the controller confirmation as to whether or not personal data concerning him or her are being processed, and, where that is the case, access to the personal data and the following information:
temporal: following information
condition: where that is the case
manner: 
graph_context:
- none

REQUIRED REG IDS
REG-032, REG-100, REG-097

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
  "id": "REA-04#2",
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
