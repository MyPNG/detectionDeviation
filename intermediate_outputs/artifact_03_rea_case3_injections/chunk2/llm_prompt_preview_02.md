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
REG-008, REG-030, REG-043
</main_entry_nodes>

<main_nodes>
  <node id="REG-008">
    ### Article 9 Paragraph 6
    High-risk AI systems shall be tested for the purpose of identifying the most appropriate and targeted risk management measures. Testing shall ensure that high-risk AI systems perform consistently for their intended purpose and that they are in compliance with the requirements set out in this Section.
  </node>
  <node id="REG-030">
    ### Article 13 Paragraph 6
    (iv) where applicable, the technical capabilities and characteristics of the high-risk AI system to provide information that is relevant to explain its output; (v) when appropriate, its performance regarding specific persons or groups of persons on which the system is intended to be used;
  </node>
  <node id="REG-043">
    ### Article 26 Paragraph 1
    Deployers of high-risk AI systems shall take appropriate technical and organisational measures to ensure they use such systems in accordance with the instructions for use accompanying the systems, pursuant to paragraphs 3 and 6.
  </node>
</main_nodes>

<referenced_nodes>
  <node id="REG-045">
    ### Article 26 Paragraph 3
    The obligations set out in paragraphs 1 and 2, are without prejudice to other deployer obligations under Union or national law and to the deployer's freedom to organise its own resources and activities for the purpose of implementing the human oversight measures indicated by the provider.
  </node>
  <node id="REG-048">
    ### Article 26 Paragraph 6
    Deployers of high-risk AI systems shall keep the logs automatically generated by that high-risk AI system to the extent such logs are under their control, for a period appropriate to the intended purpose of the high-risk AI system, of at least six months, unless provided otherwise in applicable Union or national law, in particular in Union law on the protection of personal data. Deployers that are financial institutions subject to requirements regarding their internal governance, arrangements or processes under Union financial services law shall maintain the logs as part of the documentation kept pursuant to the relevant Union financial service law.
  </node>
</referenced_nodes>

<target_policy_chunk>
Microsoft AI systems are reviewed to identify systems that may have a significant adverse impact on people, organizations, and society, and additional oversight and requirements are applied to those systems. Applies to: All AI systems. Microsoft AI systems are reviewed to identify systems that may have a significant adverse impact on people, organizations, and society, and additional oversight and requirements are applied to those systems. Review defined Restricted Uses to determine whether the system meets the definition of any Restricted Use. If it does, document this in the Impact Assessment, and follow the requirements for the Restricted Use. If it does, document this in the Impact Assessment, and follow the requirements for the Restricted Use. Answer prompts in the Impact Assessment template to determine whether the system meets the definition of a Sensitive Use. If it does, report it to the Office of Responsible AI, and follow any additional requirements resulting from a Sensitive Uses review. If it does, report it to the Office of Responsible AI, and follow any additional requirements resulting from a Sensitive Uses review. Review your systems at least annually against the definitions for Sensitive Uses and Restricted Uses. If there are systems that meet the criteria for Sensitive Uses, report them to the Office of Responsible AI. If there are systems that meet the criteria for Restricted Uses, notify the Office of Responsible AI.
</target_policy_chunk>
```
