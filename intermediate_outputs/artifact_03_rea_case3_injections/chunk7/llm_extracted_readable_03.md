# LLM Deviation Review

## REG-101
- Clause: Unknown (text not provided)
- Considered References: None

- No deviations found (non-deviation).

## REG-013
- Clause: Art10(1)
- Considered References: Art13(3)

- Deviation Count: 2

- Deviation 1
  - Type: Severity deviation
  - GDPR Quote: High-risk AI systems which make use of techniques involving the training of AI models with data shall be developed on the basis of training, validation and testing data sets that meet the quality criteria referred to in paragraphs 2 to 5 whenever such data sets are used.
  - Policy Quote: Applies to: All AI systems.
  - Mismatch: The regulation limits the requirement to high-risk AI systems, whereas the policy applies it to all AI systems (over-compliance in scope).
  - Analysis: Article 10(1) scopes obligations to high-risk AI systems; the policy extends these governance requirements to all AI systems, which is stricter than required.
- Deviation 2
  - Type: Data deviation
  - GDPR Quote: Training, validation and testing data sets shall be subject to data governance and management practices appropriate for the intended purpose of the high-risk AI system. Those practices shall concern in particular: (a) the relevant design choices; (b) data collection processes and the origin of data, and in the case of personal data, the original purpose of the data collection; (c) relevant data-preparation processing operations, such as annotation, labelling, cleaning, updating, enrichment and aggregation; (d) the formulation of assumptions, in particular with respect to the information that the data are supposed to measure and represent; (e) an assessment of the availability, quantity and suitability of the data sets that are needed; (f) examination in view of possible biases that are likely to affect the health and safety of persons, have a negative impact on fundamental rights or lead to discrimination prohibited under Union law, especially where data outputs influence inputs for future operations; (g) appropriate measures to detect, prevent and mitigate possible biases identified according to point (f); (h) the identification of relevant data gaps or shortcomings that prevent compliance with this Regulation, and how those gaps and shortcomings can be addressed.
  - Policy Quote: If you plan to use existing data sets to train the system, assess the quantity and suitability of available data sets that will be needed by the system in relation to the data requirements defined in A4.1. A4.3 Document this assessment in the Impact Assessment.
  - Mismatch: The regulation requires assessing availability, quantity and suitability of all needed data sets (covering training, validation and testing), but the policy limits this assessment to cases using existing datasets to train the system.
  - Analysis: Art 10(2) applies governance practices, including the (e) assessment, to training, validation and testing data sets that are needed; the policy narrows this to existing data sets and to the training phase, thereby restricting the data categories and processing stages covered by the assessment.

## REG-091
- Clause: Unknown (text not provided)
- Considered References: None

- No deviations found (non-deviation).
