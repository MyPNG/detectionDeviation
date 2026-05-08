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
REG-031, REG-051, REG-009
</main_entry_nodes>

<main_nodes>
  <node id="REG-031">
    ### Article 13 Paragraph 7
    (vi) when appropriate, specifications for the input data, or any other relevant information in terms of the training, validation and testing data sets used, taking into account the intended purpose of the high-risk AI system;
  </node>
  <node id="REG-051">
    ### Article 26 Paragraph 9
    Where applicable, deployers of high-risk AI systems shall use the information provided under Article 13 of this Regulation to comply with their obligation to carry out a data protection impact assessment under Article 35 of Regulation (EU) 2016/679 or Article 27 of Directive (EU) 2016/680.
  </node>
  <node id="REG-009">
    ### Article 9 Paragraph 7
    Testing procedures may include testing in real-world conditions in accordance with Article 60.
  </node>
</main_nodes>

<referenced_nodes>
  <node id="REG-025">
    ### Article 13 Paragraph 1
    High-risk AI systems shall be designed and developed in such a way as to ensure that their operation is sufficiently transparent to enable deployers to interpret a system's output and use it appropriately. An appropriate type and degree of transparency shall be ensured with a view to achieving compliance with the relevant obligations of the provider and deployer set out in Section 3.
  </node>
  <node id="REG-026">
    ### Article 13 Paragraph 2
    High-risk AI systems shall be accompanied by instructions for use in an appropriate digital format or otherwise that include concise, complete, correct and clear information that is relevant, accessible and comprehensible to deployers.
  </node>
  <node id="REG-027">
    ### Article 13 Paragraph 3
    The instructions for use shall contain at least the following information: (a) the identity and the contact details of the provider and, where applicable, of its authorised representative; (b) the characteristics, capabilities and limitations of performance of the high-risk AI system, including: (i) its intended purpose;
  </node>
  <node id="REG-028">
    ### Article 13 Paragraph 4
    (ii) the level of accuracy, including its metrics, robustness and cybersecurity referred to in Article 15 against which the high-risk AI system has been tested and validated and which can be expected, and any known and foreseeable circumstances that may have an impact on that expected level of accuracy, robustness and cybersecurity;
  </node>
  <node id="REG-029">
    ### Article 13 Paragraph 5
    (iii) any known or foreseeable circumstance, related to the use of the high-risk AI system in accordance with its intended purpose or under conditions of reasonably foreseeable misuse, which may lead to risks to the health and safety or fundamental rights referred to in Article 9(2);
  </node>
  <node id="REG-030">
    ### Article 13 Paragraph 6
    (iv) where applicable, the technical capabilities and characteristics of the high-risk AI system to provide information that is relevant to explain its output; (v) when appropriate, its performance regarding specific persons or groups of persons on which the system is intended to be used;
  </node>
  <node id="REG-032">
    ### Article 13 Paragraph 8
    (vii) where applicable, information to enable deployers to interpret the output of the high-risk AI system and use it appropriately; (c) the changes to the high-risk AI system and its performance which have been pre-determined by the provider at the moment of the initial conformity assessment, if any; (d) the human oversight measures referred to in Article 14, including the technical measures put in place to facilitate the interpretation of the outputs of the high-risk AI systems by the deployers; (e) the computational and hardware resources needed, the expected lifetime of the high-risk AI system and any necessary maintenance and care measures, including their frequency, to ensure the proper functioning of that AI system, including as regards software updates; (f) where relevant, a description of the mechanisms included within the high-risk AI system that allows deployers to properly collect, store and interpret the logs in accordance with Article 12.
  </node>
  <node id="REG-055">
    ### Article 60 Paragraph 1
    Testing of high-risk AI systems in real world conditions outside AI regulatory sandboxes may be conducted by providers or prospective providers of high-risk AI systems listed in Annex III, in accordance with this Article and the real-world testing plan referred to in this Article, without prejudice to the prohibitions under Article 5. The Commission shall, by means of implementing acts, specify the detailed elements of the real-world testing plan. Those implementing acts shall be adopted in accordance with the examination procedure referred to in Article 98(2). This paragraph shall be without prejudice to Union or national law on the testing in real world conditions of high-risk AI systems related to products covered by Union harmonisation legislation listed in Annex I.
  </node>
  <node id="REG-056">
    ### Article 60 Paragraph 2
    Providers or prospective providers may conduct testing of high-risk AI systems referred to in Annex III in real world conditions at any time before the placing on the market or the putting into service of the AI system on their own or in partnership with one or more deployers or prospective deployers.
  </node>
  <node id="REG-057">
    ### Article 60 Paragraph 3
    The testing of high-risk AI systems in real world conditions under this Article shall be without prejudice to any ethical review that is required by Union or national law.
  </node>
  <node id="REG-058">
    ### Article 60 Paragraph 4
    Providers or prospective providers may conduct the testing in real world conditions only where all of the following conditions are met: (a) the provider or prospective provider has drawn up a real-world testing plan and submitted it to the market surveillance authority in the Member State where the testing in real world conditions is to be conducted; (b) the market surveillance authority in the Member State where the testing in real world conditions is to be conducted has approved the testing in real world conditions and the real-world testing plan; where the market surveillance authority has not provided an answer within 30 days, the testing in real world conditions and the real-world testing plan shall be understood to have been approved; where national law does not provide for a tacit approval, the testing in real world conditions shall remain subject to an authorisation; (c) the provider or prospective provider, with the exception of providers or prospective providers of high-risk AI systems referred to in points 1, 6 and 7 of Annex III in the areas of law enforcement, migration, asylum and border control management, and high-risk AI systems referred to in point 2 of Annex III has registered the testing in real world conditions in accordance with Article 71(4) with a Union-wide unique single identification number and with the information specified in Annex IX; the provider or prospective provider of high-risk AI systems referred to in points 1, 6 and 7 of Annex III in the areas of law enforcement, migration, asylum and border control management, has registered the testing in real-world conditions in the secure non-public section of the EU database according to Article 49(4), point (d), with a Union-wide unique single identification number and with the information specified therein; the provider or prospective provider of high-risk AI systems referred to in point 2 of Annex III has registered the testing in real-world conditions in accordance with Article 49(5); (d) the provider or prospective provider conducting the testing in real world conditions is established in the Union or has appointed a legal representative who is established in the Union; (e) data collected and processed for the purpose of the testing in real world conditions shall be transferred to third countries only provided that appropriate and applicable safeguards under Union law are implemented; (f) the testing in real world conditions does not last longer than necessary to achieve its objectives and in any case not longer than six months, which may be extended for an additional period of six months, subject to prior notification by the provider or prospective provider to the market surveillance authority, accompanied by an explanation of the need for such an extension; (g) the subjects of the testing in real world conditions who are persons belonging to vulnerable groups due to their age or disability, are appropriately protected; (h) where a provider or prospective provider organises the testing in real world conditions in cooperation with one or more deployers or prospective deployers, the latter have been informed of all aspects of the testing that are relevant to their decision to participate, and given the relevant instructions for use of the AI system referred to in Article 13; the provider or prospective provider and the deployer or prospective deployer shall conclude an agreement specifying their roles and responsibilities with a view to ensuring compliance with the provisions for testing in real world conditions under this Regulation and under other applicable Union and national law; (i) the subjects of the testing in real world conditions have given informed consent in accordance with Article 61, or in the case of law enforcement, where the seeking of informed consent would prevent the AI system from being tested, the testing itself and the outcome of the testing in the real world conditions shall not have any negative effect on the subjects, and their personal data shall be deleted after the test is performed; (j) the testing in real world conditions is effectively overseen by the provider or prospective provider, as well as by deployers or prospective deployers through persons who are suitably qualified in the relevant field and have the necessary capacity, training and authority to perform their tasks; (k) the predictions, recommendations or decisions of the AI system can be effectively reversed and disregarded.
  </node>
  <node id="REG-059">
    ### Article 60 Paragraph 5
    Any subjects of the testing in real world conditions, or their legally designated representative, as appropriate, may, without any resulting detriment and without having to provide any justification, withdraw from the testing at any time by revoking their informed consent and may request the immediate and permanent deletion of their personal data. The withdrawal of the informed consent shall not affect the activities already carried out.
  </node>
  <node id="REG-060">
    ### Article 60 Paragraph 6
    In accordance with Article 75, Member States shall confer on their market surveillance authorities the powers of requiring providers and prospective providers to provide information, of carrying out unannounced remote or on-site inspections, and of performing checks on the conduct of the testing in real world conditions and the related high-risk AI systems. Market surveillance authorities shall use those powers to ensure the safe development of testing in real world conditions.
  </node>
  <node id="REG-061">
    ### Article 60 Paragraph 7
    Any serious incident identified in the course of the testing in real world conditions shall be reported to the national market surveillance authority in accordance with Article 73. The provider or prospective provider shall adopt immediate mitigation measures or, failing that, shall suspend the testing in real world conditions until such mitigation takes place, or otherwise terminate it. The provider or prospective provider shall establish a procedure for the prompt recall of the AI system upon such termination of the testing in real world conditions.
  </node>
  <node id="REG-062">
    ### Article 60 Paragraph 8
    Providers or prospective providers shall notify the national market surveillance authority in the Member State where the testing in real world conditions is to be conducted of the suspension or termination of the testing in real world conditions and of the final outcomes.
  </node>
  <node id="REG-063">
    ### Article 60 Paragraph 9
    The provider or prospective provider shall be liable under applicable Union and national liability law for any damage caused in the course of their testing in real world conditions.
  </node>
</referenced_nodes>

<target_policy_chunk>
Microsoft AI systems are subject to appropriate data governance and management practices. Applies to: All AI systems. Define and document data requirements with respect to the system's intended uses, stakeholders, and the geographic areas where the system will be deployed. Define and document data requirements with respect to the system's intended uses, stakeholders, and the geographic areas where the system will be deployed. Document these requirements in the Impact Assessment. Define and document procedures for the collection and processing of data, to include annotation, labelling, cleaning, enrichment, and aggregation, where relevant. Define and document procedures for the collection and processing of data, to include annotation, labelling, cleaning, enrichment, and aggregation, where relevant. If you plan to use existing data sets to train the system, assess the quantity and suitability of available data sets that will be needed by the system in relation to the data requirements defined in A4.1. A4.3 Document this assessment in the Impact Assessment. Define and document methods for evaluating data to be used by the system against the requirements defined in A4.1. Define and document methods for evaluating data to be used by the system against the requirements defined in A4.1. Evaluate all data sets using the methods defined in requirement A4.4. Document the results of the evaluation.
</target_policy_chunk>
```
