# Deviation Prompt

- id: REA-10#1
- top_k: 3
- reranked_json: /Users/my/Documents/projects/detectionDeviation/intermediate_results/02_processing/01_retrieval/reranker/artifact_01_rea__reg_reranked/chunk8_deontic_stages/rea-10#1.json
- used_reg_ids: REG-022, REG-043, REG-025

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
id: REA-10#1
text: "The Controller is based on Art 6 para 1 lit f) GDPR for processing this personal data."
slots:
actor: The Controller
modal: Mandatory
action: base
actions: base
object: Art 6 para 1 lit f )
temporal: 
condition: 
manner: 

MAIN REG MATCHES
1. REG-022
clause: Art13(1(d))
text: "The Controller SHALL provide the data subject with all of the following information: (d) where the processing is based on point (f) of Article 6(1), the legitimate interests pursued by The Controller or by a third party,"
slots:
actor: The Controller
modal: Mandatory
action: provide
actions: provide
object: the data subject with all of the following information: (d) where the processing is based on point (f) of Article 6(1), the legitimate interests pursued by The Controller or by a third party,
temporal: following information
condition: where the processing is based on point (f) of Article 6(1)
manner: by The Controller or by a third party

2. REG-043
clause: Art14(2(b))
text: "In addition to the information referred to in paragraph 1, the controller shall provide the data subject with the following information necessary to ensure fair and transparent processing in respect of the data subject: (b) where the processing is based on point (f) of Article 6(1), the legitimate interests pursued by the controller or by a third party;"
slots:
actor: the controller
modal: Mandatory
action: provide
actions: provide
object: the data subject with the following information necessary to ensure fair and transparent processing in respect of the data subject: (b) where the processing is based on point (f) of Article 6(1), the legitimate interests pursued by the controller or by a third party;
temporal: following information necessary to ensure fair
condition: where the processing is based on point (f) of Article 6(1)
manner: by the controller or by a third party

3. REG-025
clause: Art13(2)
text: "The Controller SHALL provide the data subject with the following further information necessary to ensure fair and transparent processing at the time when personal data are obtained."
slots:
actor: The Controller
modal: Mandatory
action: provide
actions: provide
object: the data subject with the following further information necessary to ensure fair and transparent processing at the time when personal data are obtained.
temporal: following further information necessary to ensure
condition: when personal data are obtained
manner: 

REQUIRED REG IDS
REG-022, REG-043, REG-025

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
  "id": "REA-10#1",
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
