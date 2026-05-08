# LLM Deviation Review

## REG-031
- Clause: Art20(1)
- Considered References: Art6(1), Art9(2)

- No deviations found (non-deviation).

## REG-025
- Clause: Art17(1)
- Considered References: Art6(1), Art9(2), Art21(1), Art21(2), Art8(1)

- Deviation Count: 1

- Deviation 1
  - Type: Severity deviation
  - GDPR Quote: the data subject withdraws consent on which the processing is based according to point (a) of Article 6(1), or point (a) of Article 9(2), and where there is no other legal ground for the processing;
  - Policy Quote: if the processing is based on your consent, you have withdrawn your consent.
  - Mismatch: The policy grants erasure upon consent withdrawal without the GDPR caveat that there must be no other legal ground for the processing.
  - Analysis: Article 17(1)(b) conditions erasure on both consent withdrawal and the absence of any other legal basis; the policy omits the latter, over-committing to erase.

## REG-013
- Clause: Art13(2)
- Considered References: Art6(1), Art9(2), Art22(1)

- No deviations found (non-deviation).

## REG-032
- Clause: Art20(2)
- Considered References: Art6(1), Art9(2)

- Deviation Count: 2

- Deviation 1
  - Type: Severity deviation
  - GDPR Quote: the data subject shall have the right to have the personal data transmitted directly from one controller to another, where technically feasible.
  - Policy Quote: as well as the right to have this data transferred to another controller.
  - Mismatch: The policy omits the GDPR’s “where technically feasible” limitation, over-committing to perform transfers in all cases.
  - Analysis: By not conditioning the transfer on technical feasibility, the policy is stricter than GDPR’s minimum requirement.
- Deviation 2
  - Type: Execution style deviation
  - GDPR Quote: the right to have the personal data transmitted directly from one controller to another, where technically feasible.
  - Policy Quote: as well as the right to have this data transferred to another controller.
  - Mismatch: The policy drops the “directly from one controller to another” modality prescribed by GDPR Art20(2).
  - Analysis: GDPR Art20(2) is about direct controller-to-controller transmission; the policy’s phrasing is method-agnostic and may imply indirect transfer.

## REG-028
- Clause: Art18(1)
- Considered References: Art21(1)

- Deviation Count: 1

- Deviation 1
  - Type: Severity deviation
  - GDPR Quote: The data subject shall have the right to obtain from the controller restriction of processing where one of the following applies: (a) the accuracy of the personal data is contested by the data subject, for a period enabling the controller to verify the accuracy of the personal data; (b) the processing is unlawful and the data subject opposes the erasure of the personal data and requests the restriction of their use instead; (c) the controller no longer needs the personal data for the purposes of the processing, but they are required by the data subject for the establishment, exercise or defence of legal claims; (d) the data subject has objected to processing pursuant to Article 21(1) pending the verification whether the legitimate grounds of the controller override those of the data subject.
  - Policy Quote: Right to restrict processing: You have the right to request that we restrict the processing of your personal data.
  - Mismatch: The policy frames restriction as an unconditional right, whereas GDPR limits it to specific conditions in points (a)–(d).
  - Analysis: By not limiting the right to the enumerated grounds, the policy over-commits beyond GDPR’s conditional entitlement.
