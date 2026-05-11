# Deviation Prompt

- id: REA-02#2
- top_k: 3
- reranked_json: /Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_01_rea_with_injections__reg_for_injectiontest_reranked/chunk2_deontic_stages/rea-02#2.json
- used_reg_ids: REG-070, REG-092, REG-048

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
id: REA-02#2
text: "These are for your convenience so that you do not have to fill in your details again when you leave another comment."
slots:
actor: User
modal: 
action: have
actions: have
object: your convenience
temporal: when you leave another comment
condition: when you leave another comment
manner: 

MAIN REG MATCHES
1. REG-070
clause: Art13(4)
text: "Paragraphs 1, 2 and 3 shall not apply where and insofar as the data subject already has the information."
slots:
actor: 2 and 3
modal: 
action: apply
actions: apply
object: where and insofar as the data subject already has the information.
temporal: 
condition: where and insofar as the data subject already has the information
manner: 
graph_context:
- id: REG-055
  edge_type: REFERENCES
  direction: outgoing
  hop_count: 1
  relation_path: REG-070 -> REG-055
  text: "Where personal data relating to a data subject are collected from the data subject, the controller shall, at the time when personal data are obtained, provide the data subject with all of the following information:"
- id: REG-062
  edge_type: REFERENCES
  direction: outgoing
  hop_count: 1
  relation_path: REG-070 -> REG-062
  text: "In addition to the information referred to in paragraph 1, the controller shall, at the time when personal data are obtained, provide the data subject with the following further information necessary to ensure fair and transparent processing:"
- id: REG-069
  edge_type: REFERENCES
  direction: outgoing
  hop_count: 1
  relation_path: REG-070 -> REG-069
  text: "Where the controller intends to further process the personal data for a purpose other than that for which the personal data were collected, the controller shall provide the data subject prior to that further processing with information on that other purpose and with any relevant further information as referred to in paragraph 2."

2. REG-092
clause: Art14(5(a))
text: "Paragraphs 1 to 4 shall not apply where and insofar as: (a) the data subject already has the information;"
slots:
actor: Paragraphs 1 to 4
modal: 
action: apply
actions: apply
object: where and insofar as: (a) the data subject already has the information;
temporal: 
condition: where and insofar as
manner: 
graph_context:
- id: REG-071
  edge_type: REFERENCES
  direction: outgoing
  hop_count: 1
  relation_path: REG-092 -> REG-071
  text: "Where personal data have not been obtained from the data subject, the controller shall provide the data subject with the following information:"
- id: REG-091
  edge_type: PARENT_CHILD
  direction: incoming
  hop_count: 1
  relation_path: REG-091 -> REG-092
  text: "Paragraphs 1 to 4 shall not apply where and insofar as:"
- id: REG-093
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-092 <- REG-091 -> REG-093
  text: "Paragraphs 1 to 4 shall not apply where and insofar as: (b) the provision of such information proves impossible or would involve a disproportionate effort, in particular for processing for archiving purposes in the public interest, scientific or historical research purposes or statistical purposes, subject to the conditions and safeguards referred to in Article 89(1) or in so far as the obligation referred to in paragraph 1 of this Article is likely to render impossible or seriously impair the achievement of the objectives of that processing."
- id: REG-094
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-092 <- REG-091 -> REG-094
  text: "In such cases the controller shall take appropriate measures to protect the data subject's rights and freedoms and legitimate interests, including making the information publicly available;"
- id: REG-095
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-092 <- REG-091 -> REG-095
  text: "Paragraphs 1 to 4 shall not apply where and insofar as: (c) obtaining or disclosure is expressly laid down by Union or Member State law to which the controller is subject and which provides appropriate measures to protect the data subject's legitimate interests or"
- id: REG-096
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-092 <- REG-091 -> REG-096
  text: "Paragraphs 1 to 4 shall not apply where and insofar as: (d) where the personal data must remain confidential subject to an obligation of professional secrecy regulated by Union or Member State law, including a statutory obligation of secrecy."

3. REG-048
clause: Art12(5)
text: "Where requests from a data subject are manifestly unfounded or excessive, in particular because of their repetitive character, the controller may either:"
slots:
actor: the controller
modal: 
action: either
actions: either
object: :
temporal: 
condition: Where requests from a data subject are manifestly unfounded or excessive
manner: 
graph_context:
- id: REG-049
  edge_type: PARENT_CHILD
  direction: outgoing
  hop_count: 1
  relation_path: REG-048 -> REG-049
  text: "Where requests from a data subject are manifestly unfounded or excessive, in particular because of their repetitive character, the controller may either: (a) charge a reasonable fee taking into account the administrative costs of providing the information or communication or taking the action requested; or"
- id: REG-050
  edge_type: PARENT_CHILD
  direction: outgoing
  hop_count: 1
  relation_path: REG-048 -> REG-050
  text: "Where requests from a data subject are manifestly unfounded or excessive, in particular because of their repetitive character, the controller may either: (b) refuse to act on the request. The controller shall bear the burden of demonstrating the manifestly unfounded or excessive character of the request."
- id: REG-047
  edge_type: SEQUENCE
  direction: outgoing
  hop_count: 1
  relation_path: REG-048 -> REG-047
  text: "Information provided under Articles 13 and 14 and any communication and any actions taken under Articles 15 to 22 and 34 shall be provided free of charge."

REQUIRED REG IDS
REG-070, REG-092, REG-048

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
  "id": "REA-02#2",
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
