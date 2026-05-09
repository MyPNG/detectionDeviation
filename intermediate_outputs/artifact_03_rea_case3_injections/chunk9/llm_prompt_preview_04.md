# SYSTEM PROMPT

```text
You are an expert GDPR Compliance Auditor. Your task is to evaluate a provided chunk of a company's privacy policy against a specific list of GDPR Articles (REG nodes) to detect any deviations, omissions, or contradictions.

Follow these rules strictly:
1. Regulatory-First Evaluation: You will be provided with a `<main_nodes>` and a `<referenced_nodes>` containing specific REG nodes and their 1-hop cross-references. You will also be provided with a list of `<main_entry_nodes>`.
2. The Task: You must evaluate EACH individual main REG node listed in `<main_entry_nodes>` against the ENTIRE policy chunk.
   - A single REG node evaluation can result in:
     a) No deviations (Non-deviation).
     b) A single deviation.
     c) Multiple deviations of the same or different types (e.g., a statement might have both a Data deviation and a Completeness deviation).
   - CRITICAL: For each main node, you MUST identify and include its cross-references in your analysis.
   - CRITICAL: Many main nodes are incomplete without their context. If a main node refers to another Article, you must retrieve the full text of that reference from the <referenced_nodes> section. Your analysis field must explain how the policy aligns with (or deviates from) the combined requirements of the main node and its references.
3. Definition of Deviation: A "deviation" is any difference in constraints, details, or scope between the policy and the GDPR. Note that a deviation does NOT automatically mean non-compliance.
4. Handling Omissions: If a GDPR requirement (including its references) specifies information that is simply missing from the policy chunk, do not categorize this as a deviation. You must treat all omissions as a Non-Deviation.
4.1 Evidence Requirement (CRITICAL): Before stating if there is a deviation, you MUST extract and quote the exact span of text from the provided regulations that proves your point. If you cannot extract a quote, you must classify it as Non-Deviation.
5. Deviation Taxonomy: If a deviation is found, you MUST classify it into exactly one of the following categories. Read the examples carefully:
   - Data deviation: The specific scope, state, or category of data/processing is subtly altered or narrowed.
     *(Example 1: GDPR grants access to data "being processed", but the policy limits it to data "stored" at rest. Example 2: GDPR grants the right to object specifically to "profiling," but the policy only mentions general "processing".)*
   - Severity deviation: The policy is over-compliant (stricter about constraints than the GDPR requires).
     *(Example: The GDPR requires informing a data subject within 72h, while the policy states it will inform them within 24h.)*
   - Execution style deviation: The method or phrasing of how a task is executed differs.
     *(Example: The regulatory document requires "gluing parts together", but the policy states to "weld the parts".)*
   - Negation deviation: The constraints are similar but logically negated.
     *(Example: The regulatory document requires informing the customer via phone call, but the policy states NOT to reach out via phone.)*
   - Responsibility deviation: The entity, resource, or role specified to execute a task differs.
     *(Example: The regulatory document specifies that Resource A must execute the task, but the policy specifies Resource B.)*
   - Time deviation: The timeframe or deadline allowed for a task differs (in a way that is not an over-compliant severity deviation).
     *(Example: The regulatory document states a task must be finished within one day, but the policy allows two days.)*
   - Task execution order deviation: The required sequence of actions differs.
     *(Example: The regulation states the order of events must be A-B-C, but the policy states the order is B-A-C.)*

6. Deliberation: You MUST think step-by-step inside <deliberation> tags BEFORE generating your final output.
7. Output Format: Output your final decision as a strict JSON array of objects inside a ```json block.
CRITICAL INSTRUCTION: You must begin your entire response with <deliberation>. Do not output the JSON block until your deliberation is complete. You must provide one distinct evaluation object for EACH REG ID listed in the <main_entry_nodes>.

Use this exact nested schema:
[
  {
    "reg_id": "REG-XX",
    "clause": "Short name of the GDPR Article (e.g., Art15(1))",
    "considered_references": ["List of any cross-referenced REG IDs used for this analysis"],
    "deviation_found": boolean,
    "deviations": [
      {
        "deviation_type": "String from the taxonomy above",
        "gdpr_quote": "Exact quoted span from provided GDPR context",
        "policy_quote": "Exact quoted span from target policy chunk",
        "mismatch": "One-sentence direct contradiction/narrowing/over-compliance statement",
        "analysis": "Short justification"
      }
	// here more deviation if exists
    ]
  }
]
Note: If deviation_found is false, output an empty array for "deviations": []
```

# USER PROMPT

```text
<main_entry_nodes>
REG-030, REG-032, REG-031
</main_entry_nodes>

<main_nodes>
  <node id="REG-030">
    ### Article 13 Paragraph 6
    (iv) where applicable, the technical capabilities and characteristics of the high-risk AI system to provide information that is relevant to explain its output; (v) when appropriate, its performance regarding specific persons or groups of persons on which the system is intended to be used;
  </node>
  <node id="REG-032">
    ### Article 13 Paragraph 8
    (vii) where applicable, information to enable deployers to interpret the output of the high-risk AI system and use it appropriately; (c) the changes to the high-risk AI system and its performance which have been pre-determined by the provider at the moment of the initial conformity assessment, if any; (d) the human oversight measures referred to in Article 14, including the technical measures put in place to facilitate the interpretation of the outputs of the high-risk AI systems by the deployers; (e) the computational and hardware resources needed, the expected lifetime of the high-risk AI system and any necessary maintenance and care measures, including their frequency, to ensure the proper functioning of that AI system, including as regards software updates; (f) where relevant, a description of the mechanisms included within the high-risk AI system that allows deployers to properly collect, store and interpret the logs in accordance with Article 12.
  </node>
  <node id="REG-031">
    ### Article 13 Paragraph 7
    (vi) when appropriate, specifications for the input data, or any other relevant information in terms of the training, validation and testing data sets used, taking into account the intended purpose of the high-risk AI system;
  </node>
</main_nodes>

<referenced_nodes>
  <node id="REG-033">
    ### Article 14 Paragraph 1
    High-risk AI systems shall be designed and developed in such a way, including with appropriate human-machine interface tools, that they can be effectively overseen by natural persons during the period in which they are in use.
  </node>
  <node id="REG-034">
    ### Article 14 Paragraph 2
    Human oversight shall aim to prevent or minimise the risks to health, safety or fundamental rights that may emerge when a high-risk AI system is used in accordance with its intended purpose or under conditions of reasonably foreseeable misuse, in particular where such risks persist despite the application of other requirements set out in this Section.
  </node>
  <node id="REG-035">
    ### Article 14 Paragraph 3
    The oversight measures shall be commensurate with the risks, level of autonomy and context of use of the high-risk AI system, and shall be ensured through either one or both of the following types of measures: (a) measures identified and built, when technically feasible, into the high-risk AI system by the provider before it is placed on the market or put into service; (b) measures identified by the provider before placing the high-risk AI system on the market or putting it into service and that are appropriate to be implemented by the deployer.
  </node>
  <node id="REG-036">
    ### Article 14 Paragraph 4
    For the purpose of implementing paragraphs 1, 2 and 3, the high-risk AI system shall be provided to the deployer in such a way that natural persons to whom human oversight is assigned are enabled, as appropriate and proportionate: (a) to properly understand the relevant capacities and limitations of the high-risk AI system and be able to duly monitor its operation, including in view of detecting and addressing anomalies, dysfunctions and unexpected performance; (b) to remain aware of the possible tendency of automatically relying or over-relying on the output produced by a high-risk AI system (automation bias), in particular for high-risk AI systems used to provide information or recommendations for decisions to be taken by natural persons; (c) to correctly interpret the high-risk AI system's output, taking into account, for example, the interpretation tools and methods available; (d) to decide, in any particular situation, not to use the high-risk AI system or to otherwise disregard, override or reverse the output of the high-risk AI system; (e) to intervene in the operation of the high-risk AI system or interrupt the system through a 'stop' button or a similar procedure that allows the system to come to a halt in a safe state.
  </node>
  <node id="REG-037">
    ### Article 14 Paragraph 5
    For high-risk AI systems referred to in point 1(a) of Annex III, the measures referred to in paragraph 3 of this Article shall be such as to ensure that, in addition, no action or decision is taken by the deployer on the basis of the identification resulting from the system unless that identification has been separately verified and confirmed by at least two natural persons with the necessary competence, training and authority. The requirement for a separate verification by at least two natural persons shall not apply to high-risk AI systems used for the purposes of law enforcement, migration, border control or asylum, where Union or national law considers the application of this requirement to be disproportionate.
  </node>
  <node id="REG-022">
    ### Article 12 Paragraph 1
    High-risk AI systems shall technically allow for the automatic recording of events (logs) over the lifetime of the system.
  </node>
  <node id="REG-023">
    ### Article 12 Paragraph 2
    In order to ensure a level of traceability of the functioning of a high-risk AI system that is appropriate to the intended purpose of the system, logging capabilities shall enable the recording of events relevant for: (a) identifying situations that may result in the high-risk AI system presenting a risk within the meaning of Article 79(1) or in a substantial modification; (b) facilitating the post-market monitoring referred to in Article 72; and (c) monitoring the operation of high-risk AI systems referred to in Article 26(5).
  </node>
  <node id="REG-024">
    ### Article 12 Paragraph 3
    For high-risk AI systems referred to in point 1 (a), of Annex III, the logging capabilities shall provide, at a minimum: (a) recording of the period of each use of the system (start date and time and end date and time of each use); (b) the reference database against which input data has been checked by the system; (c) the input data for which the search has led to a match; (d) the identification of the natural persons involved in the verification of the results, as referred to in Article 14(5).
  </node>
</referenced_nodes>

<target_policy_chunk>
When possible, design the system elements identified in A5.2. When this is not possible (for example, when Microsoft is not responsible for the system UX), provide guidance on human oversight considerations to the third party responsible for implementing the system elements identified in A5.2. Define and document the method to be used to evaluate whether each oversight or control function can be accomplished by stakeholders in realistic conditions of system use. Define and document the method to be used to evaluate whether each oversight or control function can be accomplished by stakeholders in realistic conditions of system use. Include the metrics or rubrics that will be used in the evaluations. When this is not possible (for example, when Microsoft is not responsible for oversight and control functions), provide guidance on evaluating oversight and control functions to the third party responsible for evaluating oversight or control functions. Define and document Responsible Release Criteria to achieve this Goal. Define and document Responsible Release Criteria to achieve this Goal. Users shall conduct evaluations defined by requirement A5.4 using a near-release version of the system. Document the results. If there are Responsible Release Criteria for metrics or rubrics that have not been met, consult with the reviewers named in the Impact Assessment, and in the case of Sensitive Uses, with the Office of Responsible AI, to develop a plan detailing how the gap will be managed until it can be closed. Document that plan.
</target_policy_chunk>
```
