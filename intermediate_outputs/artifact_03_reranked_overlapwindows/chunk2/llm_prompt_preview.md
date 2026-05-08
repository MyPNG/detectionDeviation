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
REG-092, REG-093, REG-095
</main_entry_nodes>

<main_nodes>
  <node id="REG-092">
    ### Article 77 Paragraph 1
    Without prejudice to any other administrative or judicial remedy, every data subject shall have the right to lodge a complaint with a supervisory authority, in particular in the Member State of his or her habitual residence, place of work or place of the alleged infringement if the data subject considers that the processing of personal data relating to him or her infringes this Regulation.
  </node>
  <node id="REG-093">
    ### Article 77 Paragraph 2
    The supervisory authority with which the complaint has been lodged shall inform the complainant on the progress and the outcome of the complaint including the possibility of a judicial remedy pursuant to Article 78.
  </node>
  <node id="REG-095">
    ### Article 78 Paragraph 2
    Without prejudice to any other administrative or non-judicial remedy, each data subject shall have the right to a an effective judicial remedy where the supervisory authority which is competent pursuant to Articles 55 and 56 does not handle a complaint or does not inform the data subject within three months on the progress or outcome of the complaint lodged pursuant to Article 77.
  </node>
</main_nodes>

<referenced_nodes>
  <node id="REG-094">
    ### Article 78 Paragraph 1
    Without prejudice to any other administrative or non-judicial remedy, each natural or legal person shall have the right to an effective judicial remedy against a legally binding decision of a supervisory authority concerning them.
  </node>
  <node id="REG-096">
    ### Article 78 Paragraph 3
    Proceedings against a supervisory authority shall be brought before the courts of the Member State where the supervisory authority is established.
  </node>
  <node id="REG-097">
    ### Article 78 Paragraph 4
    Where proceedings are brought against a decision of a supervisory authority which was preceded by an opinion or a decision of the Board in the consistency mechanism, the supervisory authority shall forward that opinion or decision to the court.
  </node>
</referenced_nodes>

<target_policy_chunk>
You have the following rights under applicable data protection law with respect to personal data concerning you. Right of access: You can request information from us at any time about whether and which personal data we store about you. The provision of information is free of charge for you. The right to information does not exist or is subject to limitations if and to the extent that confidential information, such as information that is subject to professional secrecy, would be disclosed. Right to rectification: If your personal data stored by us is inaccurate or incomplete, you have the right to obtain rectification of this data from us at any time. Right to erasure: You have the right to request that we erase your personal data if and to the extent that the data is no longer needed for the purposes for which it was collected or, if the processing is based on your consent, you have withdrawn your consent. In this case, we must stop processing your personal data and remove it from our IT systems and databases. A right to erasure does not exist insofar as • the data may not be deleted due to a legal obligation or must be processed due to a legal obligation; • the data processing is necessary for the assertion, exercise or defence of legal claims. Right to restrict processing: You have the right to request that we restrict the processing of your personal data. Right to data portability: You have the right to receive from us the data you have provided in a structured, common and machine-readable format, as well as the right to have this data transferred to another controller. This right only exists if • you have provided us with the data on the basis of consent or on the basis of a contract concluded with you; • the processing is carried out by automated means. Right to object to processing: If the processing of your data is based on Art 6 para 1 lit f) GDPR, you may object to the processing at any time. You may assert all of the data subject rights described above against PwC Legal by addressing your specific request to the following contact details: By email: DE_Datenschutz@pwc.com By mail: PricewaterhouseCoopers Legal Aktiengesellschaft Rechtsanwaltsgesellschaft Dr Tobias Gräber, Data Protection Officer Friedrich-Ebert-Anlage 35-37 60327 Frankfurt am Main In accordance with Art 77 GDPR, you have the right to lodge a complaint with a data protection supervisory authority if you believe that the processing of your personal data infringes data protection law. Even if partial automatic transmission of data takes place when you call up our website, you are not legally or contractually obliged to provide data in connection with the use of our homepage. In connection with the contact form and contacting us by email, you are free to send us data via these channels, but without providing us your personal data in the context of contacting us in this way we cannot process and answer any enquiries from you in this respect. In connection with the order of high-quality publications (e.g. studies, whitepapers), high-quality customized demo versions of software, high-quality presentation of study results, or high-quality presentation by a specialist, data are required for the conclusion of a contract with us; the provision of this data is also free in this respect, but without the data we cannot conclude a contract with you or provide you the high-quality publications (e.g. studies, whitepapers), high-quality customized demo versions of software or high-quality presentation of study results.
</target_policy_chunk>
```
