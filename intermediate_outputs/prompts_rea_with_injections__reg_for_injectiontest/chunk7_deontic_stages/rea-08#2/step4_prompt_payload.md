# Deviation Prompt

- id: REA-08#2
- top_k: 3
- reranked_json: /Users/my/Documents/projects/detectionDeviation/intermediate_outputs/artifact_01_rea_with_injections__reg_for_injectiontest_reranked/chunk7_deontic_stages/rea-08#2.json
- used_reg_ids: REG-103, REG-113, REG-121

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
id: REA-08#2
text: "All requests for rectification must be handled directly by our third-party server host, and you must contact them directly rather than us."
slots:
actor: All requests for rectification
modal: Mandatory(must)
action: handled
actions: handled
object: directly by our third-party server host, and you must contact them directly rather than us.
temporal: by our third-party server host
condition: 
manner: by our third-party server host

MAIN REG MATCHES
1. REG-103
clause: Art15(1(e))
text: "The data subject shall have the right to obtain from the controller confirmation as to whether or not personal data concerning him or her are being processed, and, where that is the case, access to the personal data and the following information: (e) the existence of the right to request from the controller rectification or erasure of personal data or restriction of processing of personal data concerning the data subject or to object to such processing;"
slots:
actor: The data subject
modal: 
action: have
actions: have
object: the right to obtain from the controller confirmation as to whether or not personal data concerning him or her are being processed, and, where that is the case, access to the personal data and the following information: (e) the existence of the right to request from the controller rectification or erasure of personal data or restriction of processing of personal data concerning the data subject or to object to such processing;
temporal: following information
condition: where that is the case
manner: 
graph_context:
- id: REG-097
  edge_type: PARENT_CHILD
  direction: incoming
  hop_count: 1
  relation_path: REG-097 -> REG-103
  text: "The data subject shall have the right to obtain from the controller confirmation as to whether or not personal data concerning him or her are being processed, and, where that is the case, access to the personal data and the following information:"
- id: REG-098
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-103 <- REG-097 -> REG-098
  text: "The data subject shall have the right to obtain from the controller confirmation as to whether or not personal data concerning him or her are being processed, and, where that is the case, access to the personal data and the following information: (a) the purposes of the processing;"
- id: REG-099
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-103 <- REG-097 -> REG-099
  text: "The data subject shall have the right to obtain from the controller confirmation as to whether or not personal data concerning him or her are being processed, and, where that is the case, access to the personal data and the following information: (b) the categories of personal data concerned;"
- id: REG-100
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-103 <- REG-097 -> REG-100
  text: "The data subject shall have the right to obtain from the controller confirmation as to whether or not personal data concerning him or her are being processed, and, where that is the case, access to the personal data and the following information: (c) the recipients or categories of recipient to whom the personal data have been"
- id: REG-101
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-103 <- REG-097 -> REG-101
  text: "or will be disclosed, in particular recipients in third countries or international organisations;"
- id: REG-102
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-103 <- REG-097 -> REG-102
  text: "The data subject shall have the right to obtain from the controller confirmation as to whether or not personal data concerning him or her are being processed, and, where that is the case, access to the personal data and the following information: (d) where possible, the envisaged period for which the personal data will be stored, or, if not possible, the criteria used to determine that period;"
- id: REG-104
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-103 <- REG-097 -> REG-104
  text: "The data subject shall have the right to obtain from the controller confirmation as to whether or not personal data concerning him or her are being processed, and, where that is the case, access to the personal data and the following information: (f) the right to lodge a complaint with a supervisory authority;"
- id: REG-105
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-103 <- REG-097 -> REG-105
  text: "The data subject shall have the right to obtain from the controller confirmation as to whether or not personal data concerning him or her are being processed, and, where that is the case, access to the personal data and the following information: (g) where the personal data are not collected from the data subject, any available information as to their source;"
- id: REG-106
  edge_type: PARENT_CHILD
  direction: via_parent_outgoing
  hop_count: 2
  relation_path: REG-103 <- REG-097 -> REG-106
  text: "The data subject shall have the right to obtain from the controller confirmation as to whether or not personal data concerning him or her are being processed, and, where that is the case, access to the personal data and the following information: (h) the existence of automated decision-making, including profiling, referred to in Article 22(1) and (4) and, at least in those cases, meaningful information about the logic involved, as well as the significance and the envisaged consequences of such processing for the data subject."

2. REG-113
clause: Art17(1)
text: "and the controller shall have the obligation to erase personal data without undue delay where one of the following grounds applies:"
slots:
actor: and the controller
modal: 
action: have
actions: have
object: the obligation to erase personal data without undue delay where one of the following grounds applies:
temporal: following grounds applies
condition: where one of the following grounds applies
manner: 
graph_context:
- id: REG-114
  edge_type: PARENT_CHILD
  direction: outgoing
  hop_count: 1
  relation_path: REG-113 -> REG-114
  text: "The data subject shall have the right to obtain from the controller the erasure of personal data concerning him or her without undue delay"
- id: REG-115
  edge_type: PARENT_CHILD
  direction: outgoing
  hop_count: 1
  relation_path: REG-113 -> REG-115
  text: "and the controller shall have the obligation to erase personal data without undue delay where one of the following grounds applies: (a) the personal data are no longer necessary in relation to the purposes for which they were collected or otherwise processed;"
- id: REG-116
  edge_type: PARENT_CHILD
  direction: outgoing
  hop_count: 1
  relation_path: REG-113 -> REG-116
  text: "The data subject shall have the right to obtain from the controller the erasure of personal data concerning him or her without undue delay"
- id: REG-117
  edge_type: PARENT_CHILD
  direction: outgoing
  hop_count: 1
  relation_path: REG-113 -> REG-117
  text: "and the controller shall have the obligation to erase personal data without undue delay where one of the following grounds applies: (b) the data subject withdraws consent on which the processing is based according to point (a) of Article 6(1), or point (a) of Article 9(2), and where there is no other legal ground for the processing;"
- id: REG-118
  edge_type: PARENT_CHILD
  direction: outgoing
  hop_count: 1
  relation_path: REG-113 -> REG-118
  text: "The data subject shall have the right to obtain from the controller the erasure of personal data concerning him or her without undue delay"
- id: REG-119
  edge_type: PARENT_CHILD
  direction: outgoing
  hop_count: 1
  relation_path: REG-113 -> REG-119
  text: "and the controller shall have the obligation to erase personal data without undue delay where one of the following grounds applies: (c) the data subject objects to the processing pursuant to Article 21(1) and there are no overriding legitimate grounds for the processing, or the data subject objects to the processing pursuant to Article 21(2);"
- id: REG-120
  edge_type: PARENT_CHILD
  direction: outgoing
  hop_count: 1
  relation_path: REG-113 -> REG-120
  text: "The data subject shall have the right to obtain from the controller the erasure of personal data concerning him or her without undue delay"
- id: REG-121
  edge_type: PARENT_CHILD
  direction: outgoing
  hop_count: 1
  relation_path: REG-113 -> REG-121
  text: "and the controller shall have the obligation to erase personal data without undue delay where one of the following grounds applies: (d) the personal data have been unlawfully processed;"
- id: REG-122
  edge_type: PARENT_CHILD
  direction: outgoing
  hop_count: 1
  relation_path: REG-113 -> REG-122
  text: "The data subject shall have the right to obtain from the controller the erasure of personal data concerning him or her without undue delay"
- id: REG-123
  edge_type: PARENT_CHILD
  direction: outgoing
  hop_count: 1
  relation_path: REG-113 -> REG-123
  text: "and the controller shall have the obligation to erase personal data without undue delay where one of the following grounds applies: (e) the personal data have to be erased for compliance with a legal obligation in Union or Member State law to which the controller is subject;"
- id: REG-124
  edge_type: PARENT_CHILD
  direction: outgoing
  hop_count: 1
  relation_path: REG-113 -> REG-124
  text: "The data subject shall have the right to obtain from the controller the erasure of personal data concerning him or her without undue delay"
- id: REG-125
  edge_type: PARENT_CHILD
  direction: outgoing
  hop_count: 1
  relation_path: REG-113 -> REG-125
  text: "and the controller shall have the obligation to erase personal data without undue delay where one of the following grounds applies: (f) the personal data have been collected in relation to the offer of information society services referred to in Article 8(1)."
- id: REG-112
  edge_type: AND
  direction: outgoing
  hop_count: 1
  relation_path: REG-113 -> REG-112
  text: "The data subject shall have the right to obtain from the controller the erasure of personal data concerning him or her without undue delay"

3. REG-121
clause: Art17(1(d))
text: "and the controller shall have the obligation to erase personal data without undue delay where one of the following grounds applies: (d) the personal data have been unlawfully processed;"
slots:
actor: and the controller
modal: 
action: have
actions: have
object: the obligation to erase personal data without undue delay where one of the following grounds applies: (d) the personal data have been unlawfully processed;
temporal: following grounds applies
condition: where one of the following grounds applies
manner: 
graph_context:
- none

REQUIRED REG IDS
REG-103, REG-113, REG-121

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
  "id": "REA-08#2",
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
