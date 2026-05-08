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
REG-031, REG-035, REG-017, REG-013, REG-028
</main_entry_nodes>

<main_nodes>
  <node id="REG-031">
    ### Article 20 Paragraph 1
    The data subject shall have the right to receive the personal data concerning him or her, which he or she has provided to a controller, in a structured, commonly used and machine-readable format and have the right to transmit those data to another controller without hindrance from the controller to which the personal data have been provided, where: (a) the processing is based on consent pursuant to point (a) of Article 6(1) or point (a) of Article 9(2) or on a contract pursuant to point (b) of Article 6(1); and (b) the processing is carried out by automated means.
  </node>
  <node id="REG-035">
    ### Article 21 Paragraph 1
    The data subject shall have the right to object, on grounds relating to his or her particular situation, at any time to processing of personal data concerning him or her which is based on point (e) or (f) of Article 6(1), including profiling based on those provisions. The controller shall no longer process the personal data unless the controller demonstrates compelling legitimate grounds for the processing which override the interests, rights and freedoms of the data subject or for the establishment, exercise or defence of legal claims.
  </node>
  <node id="REG-017">
    ### Article 14 Paragraph 2
    In addition to the information referred to in paragraph 1, the controller shall provide the data subject with the following information necessary to ensure fair and transparent processing in respect of the data subject: (a) the period for which the personal data will be stored, or if that is not possible, the criteria used to determine that period; (b) where the processing is based on point (f) of Article 6(1), the legitimate interests pursued by the controller or by a third party; (c) the existence of the right to request from the controller access to and rectification or erasure of personal data or restriction of processing concerning the data subject and to object to processing as well as the right to data portability; (d) where processing is based on point (a) of Article 6(1) or point (a) of Article 9(2), the existence of the right to withdraw consent at any time, without affecting the lawfulness of processing based on consent before its withdrawal; (e) the right to lodge a complaint with a supervisory authority; (f) from which source the personal data originate, and if applicable, whether it came from publicly accessible sources; (g) the existence of automated decision-making, including profiling, referred to in Article 22(1) and (4) and, at least in those cases, meaningful information about the logic involved, as well as the significance and the envisaged consequences of such processing for the data subject.
  </node>
  <node id="REG-013">
    ### Article 13 Paragraph 2
    In addition to the information referred to in paragraph 1, the controller shall, at the time when personal data are obtained, provide the data subject with the following further information necessary to ensure fair and transparent processing: (a) the period for which the personal data will be stored, or if that is not possible, the criteria used to determine that period; (b) the existence of the right to request from the controller access to and rectification or erasure of personal data or restriction of processing concerning the data subject or to object to processing as well as the right to data portability; (c) where the processing is based on point (a) of Article 6(1) or point (a) of Article 9(2), the existence of the right to withdraw consent at any time, without affecting the lawfulness of processing based on consent before its withdrawal; (d) the right to lodge a complaint with a supervisory authority; (e) whether the provision of personal data is a statutory or contractual requirement, or a requirement necessary to enter into a contract, as well as whether the data subject is obliged to provide the personal data and of the possible consequences of failure to provide such data; (f) the existence of automated decision-making, including profiling, referred to in Article 22(1) and (4) and, at least in those cases, meaningful information about the logic involved, as well as the significance and the envisaged consequences of such processing for the data subject.
  </node>
  <node id="REG-028">
    ### Article 18 Paragraph 1
    The data subject shall have the right to obtain from the controller restriction of processing where one of the following applies: (a) the accuracy of the personal data is contested by the data subject, for a period enabling the controller to verify the accuracy of the personal data; (b) the processing is unlawful and the data subject opposes the erasure of the personal data and requests the restriction of their use instead; (c) the controller no longer needs the personal data for the purposes of the processing, but they are required by the data subject for the establishment, exercise or defence of legal claims; (d) the data subject has objected to processing pursuant to Article 21(1) pending the verification whether the legitimate grounds of the controller override those of the data subject.
  </node>
</main_nodes>

<referenced_nodes>
  <node id="REG-001">
    ### Article 6 Paragraph 1
    Processing shall be lawful only if and to the extent that at least one of the following applies: (a) the data subject has given consent to the processing of his or her personal data for one or more specific purposes; (b) processing is necessary for the performance of a contract to which the data subject is party or in order to take steps at the request of the data subject prior to entering into a contract; (c) processing is necessary for compliance with a legal obligation to which the controller is subject; (d) processing is necessary in order to protect the vital interests of the data subject or of another natural person; (e) processing is necessary for the performance of a task carried out in the public interest or in the exercise of official authority vested in the controller; (f) processing is necessary for the purposes of the legitimate interests pursued by the controller or by a third party, except where such interests are overridden by the interests or fundamental rights and freedoms of the data subject which require protection of personal data, in particular where the data subject is a child.
  </node>
  <node id="REG-009">
    ### Article 9 Paragraph 2
    Paragraph 1 shall not apply if one of the following applies: (a) the data subject has given explicit consent to the processing of those personal data for one or more specified purposes, except where Union or Member State law provide that the prohibition referred to in paragraph 1 may not be lifted by the data subject; (b) processing is necessary for the purposes of carrying out the obligations and exercising specific rights of the controller or of the data subject in the field of employment and social security and social protection law in so far as it is authorised by Union or Member State law or a collective agreement pursuant to Member State law providing for appropriate safeguards for the fundamental rights and the interests of the data subject; (c) processing is necessary to protect the vital interests of the data subject or of another natural person where the data subject is physically or legally incapable of giving consent; (d) processing is carried out in the course of its legitimate activities with appropriate safeguards by a foundation, association or any other not-for-profit body with a political, philosophical, religious or trade union aim and on condition that the processing relates solely to the members or to former members of the body or to persons who have regular contact with it in connection with its purposes and that the personal data are not disclosed outside that body without the consent of the data subjects; (e) processing relates to personal data which are manifestly made public by the data subject; (f) processing is necessary for the establishment, exercise or defence of legal claims or whenever courts are acting in their judicial capacity; (g) processing is necessary for reasons of substantial public interest, on the basis of Union or Member State law which shall be proportionate to the aim pursued, respect the essence of the right to data protection and provide for suitable and specific measures to safeguard the fundamental rights and the interests of the data subject; (h) processing is necessary for the purposes of preventive or occupational medicine, for the assessment of the working capacity of the employee, medical diagnosis, the provision of health or social care or treatment or the management of health or social care systems and services on the basis of Union or Member State law or pursuant to contract with a health professional and subject to the conditions and safeguards referred to in paragraph 3; (i) processing is necessary for reasons of public interest in the area of public health, such as protecting against serious cross-border threats to health or ensuring high standards of quality and safety of health care and of medicinal products or medical devices, on the basis of Union or Member State law which provides for suitable and specific measures to safeguard the rights and freedoms of the data subject, in particular professional secrecy; (j) processing is necessary for archiving purposes in the public interest, scientific or historical research purposes or statistical purposes in accordance with Article 89(1) based on Union or Member State law which shall be propor­ tionate to the aim pursued, respect the essence of the right to data protection and provide for suitable and specific measures to safeguard the fundamental rights and the interests of the data subject.
  </node>
  <node id="REG-041">
    ### Article 22 Paragraph 1
    The data subject shall have the right not to be subject to a decision based solely on automated processing, including profiling, which produces legal effects concerning him or her or similarly significantly affects him or her.
  </node>
  <node id="REG-016">
    ### Article 14 Paragraph 1
    Where personal data have not been obtained from the data subject, the controller shall provide the data subject with the following information: (a) the identity and the contact details of the controller and, where applicable, of the controller's representative; (b) the contact details of the data protection officer, where applicable; (c) the purposes of the processing for which the personal data are intended as well as the legal basis for the processing; (d) the categories of personal data concerned; (e) the recipients or categories of recipients of the personal data, if any; (f) where applicable, that the controller intends to transfer personal data to a recipient in a third country or internat­ ional organisation and the existence or absence of an adequacy decision by the Commission, or in the case of transfers referred to in Article 46 or 47, or the second subparagraph of Article 49(1), reference to the appropriate or suitable safeguards and the means to obtain a copy of them or where they have been made available.
  </node>
  <node id="REG-012">
    ### Article 13 Paragraph 1
    Where personal data relating to a data subject are collected from the data subject, the controller shall, at the time when personal data are obtained, provide the data subject with all of the following information: (a) the identity and the contact details of the controller and, where applicable, of the controller's representative; (b) the contact details of the data protection officer, where applicable; (c) the purposes of the processing for which the personal data are intended as well as the legal basis for the processing; (d) where the processing is based on point (f) of Article 6(1), the legitimate interests pursued by the controller or by a third party; (e) the recipients or categories of recipients of the personal data, if any; (f) where applicable, the fact that the controller intends to transfer personal data to a third country or international organisation and the existence or absence of an adequacy decision by the Commission, or in the case of transfers referred to in Article 46 or 47, or the second subparagraph of Article 49(1), reference to the appropriate or suitable safeguards and the means by which to obtain a copy of them or where they have been made available.
  </node>
</referenced_nodes>

<target_policy_chunk>
A right to erasure does not exist insofar as • the data may not be deleted due to a legal obligation or must be processed due to a legal obligation; • the data processing is necessary for the assertion, exercise or defence of legal claims. Right to restrict processing: You have the right to request that we restrict the processing of your personal data. Right to data portability: You have the right to receive from us the data you have provided in a structured, common and machine-readable format, as well as the right to have this data transferred to another controller. This right only exists if • you have provided us with the data on the basis of consent or on the basis of a contract concluded with you; • the processing is carried out by automated means. Right to object to processing: If the processing of your data is based on Art 6 para 1 lit f) GDPR, you may object to the processing at any time.
</target_policy_chunk>
```
