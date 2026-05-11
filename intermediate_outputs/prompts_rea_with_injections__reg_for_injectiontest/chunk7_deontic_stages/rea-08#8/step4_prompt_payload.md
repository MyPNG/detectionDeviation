# Deviation Prompt

- id: REA-08#8
- top_k: 3
- reranked_json: /Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_01_rea_with_injections__reg_for_injectiontest_reranked/chunk7_deontic_stages/rea-08#8.json
- used_reg_ids: REG-094, REG-089, REG-071

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

Deviation Taxonomy:
If a deviation is found, classify it into exactly one of these categories:
- Data deviation: The specific scope, state, or category of data/processing is subtly altered or narrowed.
  (Example 1: GDPR grants access to data "being processed", but the policy limits it to data "stored" at rest.
   Example 2: GDPR grants the right to object specifically to "profiling," but the policy only mentions general "processing".)
- Severity deviation: The policy is over-compliant (stricter about constraints than the GDPR requires).
  (Example: GDPR requires informing within 72h, while policy states within 24h.)
- Execution style deviation: The method or phrasing of how a task is executed differs.
  (Example: regulation says "gluing parts together", policy says "weld the parts".)
- Negation deviation: The constraints are similar but logically negated.
  (Example: regulation requires contacting by phone, policy states not to use phone.)
- Responsibility deviation: The entity/resource/role specified to execute a task differs.
  (Example: regulation assigns Resource A, policy assigns Resource B.)
- Time deviation: The timeframe or deadline differs (and it is not an over-compliant severity deviation).
  (Example: regulation requires one day, policy allows two days.)
- Task execution order deviation: The required sequence of actions differs.
  (Example: regulation requires A-B-C, policy states B-A-C.)

Return JSON only using this exact schema:
{
  "id": "REA-XX#Y",
  "per_reg_comparisons": [
    {
      "reg_id": "REG-XXX",
      "deviation": true,
      "type": "Time deviation",
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
id: REA-08#8
text: "In the event of a data breach, we will first issue a press release to the public media, and subsequently notify the supervisory authority."
slots:
actor: we
modal: Mandatory(will)
action: first
actions: first
object: issue a press release to the public media, and subsequently notify the supervisory authority.
temporal: subsequently notify the supervisory authority
condition: in the event of a data breach
manner: 

MAIN REG MATCHES
1. REG-094
clause: Art14(5(b))
text: "In such cases the controller shall take appropriate measures to protect the data subject's rights and freedoms and legitimate interests, including making the information publicly available;"
slots:
actor: In such cases the controller
modal: 
action: take
actions: take
object: appropriate measures to protect the data subject's rights and freedoms and legitimate interests, including making the information publicly available;
temporal: 
condition: 
manner: 
graph_context:
- id: REG-093
  edge_type: SEQUENCE
  direction: outgoing
  hop_count: 1
  relation_path: REG-094 -> REG-093
  text: "Paragraphs 1 to 4 shall not apply where and insofar as: (b) the provision of such information proves impossible or would involve a disproportionate effort, in particular for processing for archiving purposes in the public interest, scientific or historical research purposes or statistical purposes, subject to the conditions and safeguards referred to in Article 89(1) or in so far as the obligation referred to in paragraph 1 of this Article is likely to render impossible or seriously impair the achievement of the objectives of that processing."
- id: REG-091
  edge_type: PARENT_CHILD
  direction: incoming
  hop_count: 1
  relation_path: REG-091 -> REG-094
  text: "Paragraphs 1 to 4 shall not apply where and insofar as:"
- id: REG-092
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-094 <- REG-091 -> REG-092
  text: "Paragraphs 1 to 4 shall not apply where and insofar as: (a) the data subject already has the information;"
- id: REG-095
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-094 <- REG-091 -> REG-095
  text: "Paragraphs 1 to 4 shall not apply where and insofar as: (c) obtaining or disclosure is expressly laid down by Union or Member State law to which the controller is subject and which provides appropriate measures to protect the data subject's legitimate interests or"
- id: REG-096
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-094 <- REG-091 -> REG-096
  text: "Paragraphs 1 to 4 shall not apply where and insofar as: (d) where the personal data must remain confidential subject to an obligation of professional secrecy regulated by Union or Member State law, including a statutory obligation of secrecy."

2. REG-089
clause: Art14(3(c))
text: "The controller shall provide the information referred to in paragraphs 1 and 2: (c) if a disclosure to another recipient is envisaged, at the latest when the personal data are first disclosed."
slots:
actor: The controller
modal: 
action: provide
actions: provide
object: the information referred to in paragraphs 1 and 2: (c) if a disclosure to another recipient is envisaged, at the latest when the personal data are first disclosed.
temporal: at the latest when the personal data are
condition: if a disclosure to another recipient is envisaged
manner: 
graph_context:
- id: REG-071
  edge_type: REFERENCES
  direction: outgoing
  hop_count: 1
  relation_path: REG-089 -> REG-071
  text: "Where personal data have not been obtained from the data subject, the controller shall provide the data subject with the following information:"
- id: REG-078
  edge_type: REFERENCES
  direction: outgoing
  hop_count: 1
  relation_path: REG-089 -> REG-078
  text: "In addition to the information referred to in paragraph 1, the controller shall provide the data subject with the following information necessary to ensure fair and transparent processing in respect of the data subject:"
- id: REG-086
  edge_type: PARENT_CHILD
  direction: incoming
  hop_count: 1
  relation_path: REG-086 -> REG-089
  text: "The controller shall provide the information referred to in paragraphs 1 and 2:"
- id: REG-087
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-089 <- REG-086 -> REG-087
  text: "The controller shall provide the information referred to in paragraphs 1 and 2: (a) within a reasonable period after obtaining the personal data, but at the latest within one month, having regard to the specific circumstances in which the personal data are processed;"
- id: REG-088
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-089 <- REG-086 -> REG-088
  text: "The controller shall provide the information referred to in paragraphs 1 and 2: (b) if the personal data are to be used for communication with the data subject, at the latest at the time of the first communication to that data subject; or"

3. REG-071
clause: Art14(1)
text: "Where personal data have not been obtained from the data subject, the controller shall provide the data subject with the following information:"
slots:
actor: the controller
modal: 
action: provide
actions: provide
object: the data subject with the following information:
temporal: following information
condition: Where personal data have not been obtained from the data subject
manner: 
graph_context:
- none

REQUIRED REG IDS
REG-094, REG-089, REG-071

INSTRUCTIONS
1. Compare the REA and REG primarily using the raw text.
2. Use the slots only as checklist hints (actor/modal/action/object/condition/temporal/manner/sequence/negation).
3. For each REG, decide if there is a quote-supported deviation.
4. If deviation=true, set exactly one 'type' from this taxonomy only:
   Data deviation | Severity deviation | Execution style deviation | Negation deviation | Responsibility deviation | Time deviation | Task execution order deviation
5. Every deviation claim must include evidence spans from both REA and REG.
6. Do not assume that shared verbs imply the same constraint.
7. Only classify a deviation when quoted REA and REG spans clearly express the same or directly conflicting constraint.
8. Do not treat omission alone as a deviation.
9. If evidence is ambiguous or weak for a REG comparison, set deviation=false, confidence=low, and needs_more_context=true for that REG.
10. Return exactly one per_reg_comparisons entry for each REG ID listed under REQUIRED REG IDS. No missing IDs and no extra IDs.
11. Return JSON only in this schema:

{
  "id": "REA-08#8",
  "per_reg_comparisons": [
    {
      "reg_id": "REG-XXX",
      "deviation": true,
      "type": "Data deviation | Severity deviation | Execution style deviation | Negation deviation | Responsibility deviation | Time deviation | Task execution order deviation",
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
