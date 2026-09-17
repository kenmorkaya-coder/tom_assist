# Full-document retrieval: actual results

The unchanged native Stream1 tree processed all 501 passages from the 129-page M12 Interface Agreement. Every passage and query used all 4,066 signed 32 x 32 branch matrices. The expected answer locations and questions were fixed before retrieval.

**Complete answer first: 6/10. Complete answer within the first three matches: 10/10.** These are ten controlled questions, not an estimate of production accuracy.

The two original insurance query fields reproduced exactly. Every candidate was routed before scoring; there was no shortlist, lexical reranking, learning or branch cutoff. This exercises the full-field diagnostic matcher with the app’s existing passage splitter, not the desktop retrieval endpoint.

| Question | Expected clause | First complete-answer rank |
|---|---|---|
| Can we enter a SAS Interface Zone without giving notice if an emergency requires us to be there? | 4.2(b) | 1 |
| When must TfNSW tell SM that the M12 Works will not comply with the approved design or technical requirements? | 5.7(a) | 1 |
| After the M12 Works are complete, who coordinates delivery with the provider for new non-contestable utilities in a SAS Interface Zone? | 18(c)(ii) | 1 |
| TfNSW has received a media request for comment about the SMWSA Activities. Who must it pass the request to, and how quickly? | 27.3(b) | 1 |
| SM has received a media request for comment about the M12 Activities. Who must it pass the request to, and how quickly? | 27.4(b) | 1 |
| How soon after becoming aware of a dispute must a party issue its Notice of Dispute? | 28.1(a)(ii) | 1 |
| After a Notice of Dispute is received, when must the TfNSW and SM representatives meet? | 28.1(b) | 2 |
| What is required to formally change this deed? | 31.6 | 2 |
| What insurance payments must TfNSW make, and when must it make them? | 23.2 | 2 |
| What insurance payments must SM make, and when must it make them? | 24.2 | 3 |

## Four misses: one-variable diagnosis

Only the correct candidate’s surrounding text was removed. The question, tree and every other candidate were fixed. Answer locations were known for this diagnostic; this is not a deployable answer-selection method or a revised original success rate.

| Question | Original rank | Compact passage rank | Whole-tree score, before to after |
|---|---|---|---|
| After a Notice of Dispute is received, when must the TfNSW and SM representatives meet? | 2 | 1 | 0.763525 to 0.820638 |
| What is required to formally change this deed? | 2 | 2 | 0.604459 to 0.631087 |
| What insurance payments must TfNSW make, and when must it make them? | 2 | 1 | 0.691366 to 0.702207 |
| What insurance payments must SM make, and when must it make them? | 3 | 3 | 0.626016 to 0.632941 |

Passage context contributed to the dispute-meeting and TfNSW-premium misses. It did not resolve the amendment or SM-premium misses. In the two close misses, incoming matrix agreement ranked the correct passage first, while the current complete-tree-field score ranked it second. This identifies a ranking failure; it does not establish its full cause or justify changing the native tree.

![Actual signed branch patterns](/Users/kenmorkaya/PycharmProjects/ToM_assist/validation/runs/stream1-full-document-miss-patterns.png)

The first dispute-meeting match is a special 48-hour rule for a design dispute; the general five-Business-Day rule is second. The first amendment match contains further-acts/general provisions. The first match for both premium questions contains liability-coverage limits, not the premium-payment obligation.

## Exact questions and top three passages

Page numbers below are physical PDF pages. Text is from the unchanged PDF extraction; overlapping chunks may start or finish mid-sentence. “Complete expected evidence” is exact span containment, not merely an overlap.

### Can we enter a SAS Interface Zone without giving notice if an emergency requires us to be there?

Expected: **4.2(b)**, PDF page 23. First full-answer passage: rank **1**.

**Match 1: passage 158, PDF pages 22–23, score 0.695008. Complete expected evidence: yes.

```text
in accordance with clause 14.2 or clause 15.2;

             (iv)    an inspection,

             that requires that party to be on the relevant SAS Interface Zone:

             (v)     the party requiring access must promptly notify the other party in writing,
                     setting out the purpose of the access and the proposed date and time of
                     access;

             (vi)    the other party must promptly respond in writing by agreeing to the date and
                     time of access or proposing an alternative date or time; and

             (vii)   the parties must cooperate to ensure that access is provided in a timely
                     manner and at a time which is convenient to both parties.


                                                17

[PDF page break]
      (b)   A party may access a SAS Interface Zone under this clause 4.2, in the event of an
            emergency that requires that party to be on the relevant SAS Interface Zone, without
            providing notice.
```

**Match 2: passage 159, PDF pages 23–23, score 0.636948. Complete expected evidence: no.

```text
Interface Zone under this clause 4.2, in the event of an
            emergency that requires that party to be on the relevant SAS Interface Zone, without
            providing notice.

      (c)   The parties acknowledge and agree that they will grant each other rights of access
            to the SAS Interface Zones for the permitted purposes, and in accordance with the
            requirements and conditions, set out in Part B of the Site Access Schedule.

4.3   Obligations during access

      In accessing a SAS Interface Zone:

      (a)   SM must comply with, and procure that the SMWSA Contractors comply with; and

      (b)   TfNSW must comply with, and procure the M12 Contractor complies with,

      the conditions for accessing the relevant land in any applicable construction licence, any
      relevant Approvals and the requirements in the Site Access Arrangements, and
```

**Match 3: passage 217, PDF pages 36–37, score 0.548486. Complete expected evidence: no.

```text
SAS Interface Zone (or other obligation);

             (ii)    the extension of time required to the Handover Date;

             (iii)   reasons for the delay; and

             (iv)    any mitigating actions which are being taken to achieve the relevant Handover
                     Date, and to otherwise minimise the delay.




                                               31

[PDF page break]
       (b)    Following the issue of a notice under clause 11.2(a), the Executive Group must meet
              as soon reasonably practicable to review and discuss the matters set out in that
              notice.

11.3   Handover Plan and Mitigation Plan

       (a)    Where, following a meeting of the Executive Group, the Executive Group determines
              that, in respect of a SAS Interface Zone, a party (the Delayed Party) is not
              reasonably likely to hand over the relevant SAS Interface Zone by the relevant
              Handover Date, the Executive Group may direct:
```


### When must TfNSW tell SM that the M12 Works will not comply with the approved design or technical requirements?

Expected: **5.7(a)**, PDF page 25. First full-answer passage: rank **1**.

**Match 1: passage 169, PDF pages 25–25, score 0.811358. Complete expected evidence: yes.

```text
into account and address SM's comments,
            in accordance with clause 5.4; or

      (c)   SM's Representative agrees otherwise in writing.

5.7   Notification of non-compliance with M12 Design Documentation or Sydney Metro’s
      M12 Technical Requirements

      (a)   TfNSW must immediately notify SM if the M12 Works are not, or will not be,
            constructed (or the M12 Activities are not, or will not be, carried out) in accordance
            with:

            (i)     the M12 100% Design Documentation;

            (ii)    M12 Design Documentation that TfNSW is entitled to use for construction
                    purposes pursuant to clause 5.6; or

            (iii)   Sydney Metro’s M12 Technical Requirements.
```

**Match 2: passage 171, PDF pages 26–26, score 0.728881. Complete expected evidence: no.

```text
c)   Unless TfNSW demonstrates to SM's reasonable satisfaction that such non-
            compliance the subject of clause 5.7(a) or 5.7(b) has no, or will have no, material
            adverse effect on the SMWSA Works or Sydney Metro Western Sydney Airport,
            TfNSW must comply with a direction by SM to rectify, or avoid, the non-compliance
            with the M12 Design Documentation or Sydney Metro’s M12 Technical Requirements.

5.8   Sydney Metro’s M12 Technical Requirements

      TfNSW must:

      (a)   ensure that the M12 Design Documentation, the M12 Contract and the M12
            Specification is in compliance with the Sydney Metro’s M12 Technical Requirements
            in Exhibit 1; and

      (b)   ensure that the M12 Contractor complies with the M12 Contract (including the M12
            Specification) and Sydney Metro’s M12 Technical Requirements.
```

**Match 3: passage 192, PDF pages 30–30, score 0.713526. Complete expected evidence: no.

```text
the SMWSA
                   Activities are not, or will not be, carried out) in accordance with the TfNSW’s
                   SMWSA Technical Requirements.

      (c)   Unless SM demonstrates to TfNSW's reasonable satisfaction that such non-
            compliance the subject of clause 7.7(a) or 7.7(b) has no, or will have no, material
            adverse effect on the M12 Works or the M12, SM must comply with a direction by
            TfNSW to rectify, or avoid, the non-compliance with the SMWSA Design
            Documentation or TfNSW’s SMWSA Technical Requirements.

7.8   SMWSA Specification

      SM must:

      (a)   ensure that each SMWSA Contract and SMWSA Specification is in compliance with
            the TfNSW’s SMWSA Technical Requirements in Exhibit 1; and
```


### After the M12 Works are complete, who coordinates delivery with the provider for new non-contestable utilities in a SAS Interface Zone?

Expected: **18(c)(ii)**, PDF page 49. First full-answer passage: rank **1**.

**Match 1: passage 268, PDF pages 49–49, score 0.686790. Complete expected evidence: yes.

```text
consequence of the SMWSA Works in Interface Zone
             0 and Interface Zone 2 in accordance with each of TfNSW's and SM's requirements.

       (c)   In respect of any new non-contestable utility or capital works by a utility provider
             required to be carried out in a SAS Interface Zone:

             (i)     prior to Completion of the M12 Works, TfNSW will co-ordinate utility delivery
                     with the relevant utility provider;

             (ii)    after Completion of the M12 Works, SM will co-ordinate utility delivery with
                     the relevant utility provider; and

             (iii)   as required, TfNSW and SM will review designs of utility providers to ensure
                     the requirements of each party are met.
```

**Match 2: passage 318, PDF pages 60–61, score 0.636891. Complete expected evidence: no.

```text
Zone 3 by TfNSW to SM,

             the Executive Group must meet at least monthly to review and discuss matters
             relating to each SAS Interface Zone, including:

             (iii)   reviewing the progress of the M12 Works and SMWSA Works (as applicable)
                     in that SAS Interface Zone, including by reference to any Handover Plan or
                     Mitigation Plan which has been prepared in respect of any SAS Interface Zone;

             (iv)    considering whether the M12 Works and SMWSA Works (as applicable) in that
                     SAS Interface Zone have been progressed to a point (having regard to the
                     applicable construction programs) that, in the opinion of the Executive Group,
                     the party undertaking works in that SAS Interface Zone will be able to hand

                                               55

[PDF page break]
                     over the SAS Interface Zone to the other party by the relevant Handover
                     Date; and
```

**Match 3: passage 159, PDF pages 23–23, score 0.604564. Complete expected evidence: no.

```text
Interface Zone under this clause 4.2, in the event of an
            emergency that requires that party to be on the relevant SAS Interface Zone, without
            providing notice.

      (c)   The parties acknowledge and agree that they will grant each other rights of access
            to the SAS Interface Zones for the permitted purposes, and in accordance with the
            requirements and conditions, set out in Part B of the Site Access Schedule.

4.3   Obligations during access

      In accessing a SAS Interface Zone:

      (a)   SM must comply with, and procure that the SMWSA Contractors comply with; and

      (b)   TfNSW must comply with, and procure the M12 Contractor complies with,

      the conditions for accessing the relevant land in any applicable construction licence, any
      relevant Approvals and the requirements in the Site Access Arrangements, and
```


### TfNSW has received a media request for comment about the SMWSA Activities. Who must it pass the request to, and how quickly?

Expected: **27.3(b)**, PDF page 64. First full-answer passage: rank **1**.

**Match 1: passage 333, PDF pages 64–64, score 0.724407. Complete expected evidence: yes.

```text
employees, professional advisers,
                     auditors and consultants.

27.3   SMWSA Publicity

       (a)   Subject to clauses 27.3(c) and 27.3(d), TfNSW shall not issue any information,
             publication, document or article for publication concerning the SMWSA Activities in
             any media without prior written approval of SM (acting reasonably) and only in a
             manner approved by SM (acting reasonably).

       (b)   Subject to clauses 27.3(c) and 27.3(d), if TfNSW receives a direct request from the
             media for comment in respect of any aspect of the SMWSA Activities, TfNSW must,
             and must ensure that any of its subcontractors, promptly provide details of such
             request to SM.
```

**Match 2: passage 334, PDF pages 64–64, score 0.693488. Complete expected evidence: no.

```text
SMWSA Activities, TfNSW must,
             and must ensure that any of its subcontractors, promptly provide details of such
             request to SM.

       (c)   TfNSW may provide information to the public in relation to any traffic adjustments
             as a result of the SMWSA Activities in a timely manner and by such methods as it
             considers appropriate and SM must not provide any such information to the public
             without prior consultation with TfNSW.

       (d)   TfNSW may issue any information, publication, document or article for publication
             concerning the SMWSA Activities to the extent it is required to do so to comply with
             Law.

27.4   M12 Publicity

       (a)   Subject to clauses 27.4(c) and 27.
```

**Match 3: passage 335, PDF pages 64–64, score 0.672903. Complete expected evidence: no.

```text
it is required to do so to comply with
             Law.

27.4   M12 Publicity

       (a)   Subject to clauses 27.4(c) and 27.4(d), SM shall not issue any information,
             publication, document or article for publication concerning the M12 Activities in any
             media without prior written approval of TfNSW (acting reasonably) and only in a
             manner approved by TfNSW (acting reasonably).

       (b)   Subject to clauses 27.4(c) and 27.4(d), if SM receives a direct request from the
             media for comment in respect of any aspect of the M12 Activities, SM must, and
             must ensure that any of its subcontractors, promptly provide details of such request
             to TfNSW.
```


### SM has received a media request for comment about the M12 Activities. Who must it pass the request to, and how quickly?

Expected: **27.4(b)**, PDF page 64. First full-answer passage: rank **1**.

**Match 1: passage 335, PDF pages 64–64, score 0.634453. Complete expected evidence: yes.

```text
it is required to do so to comply with
             Law.

27.4   M12 Publicity

       (a)   Subject to clauses 27.4(c) and 27.4(d), SM shall not issue any information,
             publication, document or article for publication concerning the M12 Activities in any
             media without prior written approval of TfNSW (acting reasonably) and only in a
             manner approved by TfNSW (acting reasonably).

       (b)   Subject to clauses 27.4(c) and 27.4(d), if SM receives a direct request from the
             media for comment in respect of any aspect of the M12 Activities, SM must, and
             must ensure that any of its subcontractors, promptly provide details of such request
             to TfNSW.
```

**Match 2: passage 336, PDF pages 64–65, score 0.566196. Complete expected evidence: no.

```text
the M12 Activities, SM must, and
             must ensure that any of its subcontractors, promptly provide details of such request
             to TfNSW.

       (c)   SM may provide information to the public in relation to any traffic adjustments as a
             result of the M12 Activities in a timely manner and by such methods as it considers
             appropriate and TfNSW must not provide any such information to the public without
             prior consultation with SM.

       (d)   SM may issue any information, publication, document or article for publication
             concerning the M12 Activities to the extent it is required to do so to comply with Law.




                                               59

[PDF page break]
27.5   Disclosure and Release

       (a)   The parties acknowledge that each of them may be required by Law to disclose the
             contents of, or certain information concerning, this Deed (including in accordance
             with section 9 or sections 27 to 35 of the Government Information (Public Access)
             Act 2009 (NSW)).
```

**Match 3: passage 230, PDF pages 40–40, score 0.562162. Complete expected evidence: no.

```text
plies with each M12 Stakeholder
                     Interface Plan as revised in accordance with this clause, including any
                     instructions issued under clause 13(c)(ii).

       (d)   SM acknowledges and agrees that it is only entitled to make comments under
             clause 13(c)(i) relating to the M12 Stakeholder Interface Plan provided in accordance
             with clause 13(a) to the extent that:

             (i)     it is inconsistent with the Sydney Metro’s M12 Technical Requirements;

             (ii)    performance of the M12 Activities in accordance with the relevant M12
                     Stakeholder Interface Plan:

                     (A)   would be in breach of this Deed; or

                     (B)   may have a material adverse impact on the SMWSA Activities.

       (e)   If any M12 Stakeholder Interface Plan in respect of which SM is entitled to comment
             is amended after SM has provided comments under clause 13(c)(i):
```


### How soon after becoming aware of a dispute must a party issue its Notice of Dispute?

Expected: **28.1(a)(ii)**, PDF page 65. First full-answer passage: rank **1**.

**Match 1: passage 338, PDF pages 65–65, score 0.738723. Complete expected evidence: yes.

```text
Dispute; and

             (ii)   be issued within 10 Business Days after Party A first became aware of the
                    fact, matter or thing on which the Dispute is based.

       (b)   Within 5 Business Days of receiving a Notice of Dispute, TfNSW's Representative and
             SM's Representative will meet in good faith to resolve the Dispute.

28.2   Referral to Project Group

       If the Dispute is not resolved within 10 Business Days of receiving the Notice of Dispute,
       then a Dispute must be referred to the Project Group for resolution as soon as reasonably
       practicable unless the parties agree otherwise.

28.3   Escalation to Executive Group

       If the Dispute is not resolved by the Project Group:

       (a)   at the next meeting of the Project Group following the issue of the Notice of Dispute;
             or

       (b)   within 20 Business Days of the Notice of Dispute,

       (whichever is earlier), the parties must within 5 Business Days of:
```

**Match 2: passage 339, PDF pages 65–66, score 0.669654. Complete expected evidence: no.

```text
of Dispute;
             or

       (b)   within 20 Business Days of the Notice of Dispute,

       (whichever is earlier), the parties must within 5 Business Days of:

       (c)   the meeting of the Project Group; or

       (d)   the expiry of the period specified in clause 28.3(b),

       (as applicable), prepare and provide to the Executive Group a joint paper clearly describing
       the issue and requesting a resolution.

28.4   Escalation to senior executives

       If the Dispute is not resolved by the Executive Group:

       (a)   at the next meeting of the Executive Group following the issue of the Notice of
             Dispute; or

       (b)   within 30 Business Days of the Notice of Dispute,

       (whichever is earlier), the parties must within 5 Business Days of:
                                               60

[PDF page break]
       (c)    the meeting of the Executive Group; or

       (d)    the expiry of the period specified in clause 28.4(b),
```

**Match 3: passage 337, PDF pages 65–65, score 0.648839. Complete expected evidence: yes.

```text
information concerning, this Deed (including in accordance
             with section 9 or sections 27 to 35 of the Government Information (Public Access)
             Act 2009 (NSW)).

       (b)   Each party consents to, and releases the other, in respect of any such disclosure.

28.    DISPUTE RESOLUTION

28.1   Dispute Notice

       (a)   If a dispute arises out of or in any way connected with this Deed (a Dispute), then
             the disputing party (Party A) must give to the other party (Party B) a notice
             identifying and providing details of the subject of the Dispute (Notice of Dispute).
             The Notice of Dispute must:

             (i)    provide brief particulars of the issues in Dispute; and

             (ii)   be issued within 10 Business Days after Party A first became aware of the
                    fact, matter or thing on which the Dispute is based.
```


### After a Notice of Dispute is received, when must the TfNSW and SM representatives meet?

Expected: **28.1(b)**, PDF page 65. First full-answer passage: rank **2**.

**Match 1: passage 186, PDF pages 29–29, score 0.769920. Complete expected evidence: no.

```text
A Design Documentation regarding
             public safety or a TfNSW Structural Imperative.

      (c)    The parties acknowledge and agree that if a Dispute arises under this clause:

             (i)     the parties must act to resolve the Dispute as expeditiously as possible,
                     including by holding the meeting under clause 28.1(b) within 48 hours of the
                     service of the notice under clause 7.4(a);

             (ii)    the relevant SMWSA Independent Certifier must not issue a certificate in the
                     form set out in Schedule 8 or Schedule 9 (as applicable) under clause
                     7.2(c)(i)(B) in respect of any SMWSA Design Documentation in respect of
                     which TfNSW has issued a notice under clause 7.4(a) until the Dispute is
                     resolved; and

             (iii)   except where TfNSW’s notice under clause 7.
```

**Match 2: passage 338, PDF pages 65–65, score 0.763525. Complete expected evidence: yes.

```text
Dispute; and

             (ii)   be issued within 10 Business Days after Party A first became aware of the
                    fact, matter or thing on which the Dispute is based.

       (b)   Within 5 Business Days of receiving a Notice of Dispute, TfNSW's Representative and
             SM's Representative will meet in good faith to resolve the Dispute.

28.2   Referral to Project Group

       If the Dispute is not resolved within 10 Business Days of receiving the Notice of Dispute,
       then a Dispute must be referred to the Project Group for resolution as soon as reasonably
       practicable unless the parties agree otherwise.

28.3   Escalation to Executive Group

       If the Dispute is not resolved by the Project Group:

       (a)   at the next meeting of the Project Group following the issue of the Notice of Dispute;
             or

       (b)   within 20 Business Days of the Notice of Dispute,

       (whichever is earlier), the parties must within 5 Business Days of:
```

**Match 3: passage 229, PDF pages 39–40, score 0.701602. Complete expected evidence: no.

```text
TfNSW must provide
            such material to SM at the same time as it provides the relevant plan.

      (c)   Subject to clause 13(d):

            (i)     SM may, within 10 Business Days of receipt of a M12 Stakeholder Interface
                    Plan in accordance with clause 13(a), provide written comments to TfNSW on
                    the M12 Stakeholder Interface Plan;


                                              34

[PDF page break]
             (ii)    TfNSW will take into account any comments provided by SM under clause
                     13(c)(i), which may include issuing necessary instructions to its contractors
                     including the M12 Contractor for compliance; and

             (iii)   TfNSW must ensure the M12 Contractor complies with each M12 Stakeholder
                     Interface Plan as revised in accordance with this clause, including any
                     instructions issued under clause 13(c)(ii).
```


### What is required to formally change this deed?

Expected: **31.6**, PDF page 68. First full-answer passage: rank **2**.

**Match 1: passage 347, PDF pages 67–68, score 0.632399. Complete expected evidence: no.

```text
b)    supersedes any prior written or other agreement of the parties,

       in relation to the subject matter of this Deed.

31.2   Remedies cumulative

       The rights, powers and remedies provided in this Deed are cumulative with and not
       exclusive of the rights, powers or remedies provided by Law independently of this Deed.

                                                62

[PDF page break]
31.3   Further acts

       Each party must promptly do all further acts and execute and deliver all further documents
       (in form and content reasonably satisfactory to that party) required by Law or reasonably
       requested by another party to give effect to this Deed.

31.4   Governing law

       This Deed is governed by and must be construed according to the law applying in New South
       Wales.

31.5   Jurisdiction

       Each party irrevocably:
```

**Match 2: passage 348, PDF pages 68–68, score 0.604459. Complete expected evidence: yes.

```text
Deed is governed by and must be construed according to the law applying in New South
       Wales.

31.5   Jurisdiction

       Each party irrevocably:

       (a)   submits to the non-exclusive jurisdiction of the courts of New South Wales, and the
             courts competent to determine appeals from those courts, with respect to any
             proceedings which may be brought at any time relating to this Deed.

       (b)   waives any objection it may now or in the future have to the venue of any
             proceedings, and any claim it may now or in the future have that any proceedings
             have been brought in an inconvenient forum, where that venue falls within clause
             31.5(a).

31.6   Amendments

       This Deed may only be varied by an agreement executed by or on behalf of each of the
       parties.

31.7   Waiver
```

**Match 3: passage 349, PDF pages 68–68, score 0.602924. Complete expected evidence: yes.

```text
a).

31.6   Amendments

       This Deed may only be varied by an agreement executed by or on behalf of each of the
       parties.

31.7   Waiver

       (a)   Failure to exercise or enforce or a delay in exercising or enforcing or the partial
             exercise or enforcement of any right, power or remedy provided by Law or under
             this Deed by any party will not in any way preclude, or operate as a waiver of, any
             exercise or enforcement, or further exercise or enforcement of that or any other
             right, power or remedy provided by Law or under this Deed.

       (b)   Except as expressly provided in this Deed, any waiver or consent given by any party
             under this Deed will only be effective and binding on that party if it is given or
             confirmed in writing by that party.
```


### What insurance payments must TfNSW make, and when must it make them?

Expected: **23.2**, PDF page 55. First full-answer passage: rank **2**.

**Match 1: passage 301, PDF pages 56–56, score 0.692571. Complete expected evidence: no.

```text
insurances set out below are effected, either by SM or by the
       SMWSA Contractors, and maintained throughout the respective periods for which they are
       required:

       (a)   (Public and Products Liability) public and products liability insurance which covers
             legal liability for personal injury (including illness, disease or death) and/or property
             damage arising in connection with the SMWSA Works and SMWSA Activities for not
             less than $250 million per occurrence for public liability and $250 million per
             occurrence and in the aggregate for products liability. The policy referred to in this
             clause 24.1(a) must name as an additional insured party TfNSW, and must be
             maintained for a period commencing on the date of execution of the first SMWSA
             Contract and expiring on the date which is 12 months after the date of Completion
             of the SSTOM Works.
```

**Match 2: passage 293, PDF pages 54–55, score 0.691366. Complete expected evidence: yes.

```text
maintained for a period commencing on the date of
             execution of the M12 Contract and expiring 12 months after the date of Completion
             of the M12 Works.

       (d)   (Statutory insurances) TfNSW must ensure that all insurances required under
             statute are effected and maintained by it and the M12 Contractor for a period
             commencing on the date of this Deed and expiring on the date of Completion of the
             M12 Works, including but not limited to workers compensation, employers’ liability
             and motor vehicle compulsory third party insurance.
                                               49

[PDF page break]
23.2   Payment of premiums

       TfNSW must punctually pay or cause to be paid all premiums and other moneys payable in
       respect of any policy of insurance required to be effected under this Deed (including any
       premiums and other moneys payable under any policy of insurance required under clause
       23.1).

23.3   Risk of deductible
```

**Match 3: passage 299, PDF pages 56–56, score 0.683841. Complete expected evidence: no.

```text
TfNSW or by the M12 Contractor which names
       more than one insured under this clause 23 other than the insurances referred to in clauses
       23.1(b) and 23.1(c) must include a cross liability clause which provides that:

       (a)   all insurance agreements and endorsements (with the exception of limits of liability)
             name, and operate as if there was a separate policy of insurance covering each
             insured;

       (b)   failure by any insured to observe and fulfil the terms of the policy does not prejudice
             the insurance of any other insured;

       (c)   any non-disclosure by one insured does not prejudice the right of any other insured
             to claim on the policy;

       (d)   a notice to the insurer by one insured will be deemed to be notice by all insured
             parties; and
```


### What insurance payments must SM make, and when must it make them?

Expected: **24.2**, PDF page 57. First full-answer passage: rank **3**.

**Match 1: passage 301, PDF pages 56–56, score 0.684469. Complete expected evidence: no.

```text
insurances set out below are effected, either by SM or by the
       SMWSA Contractors, and maintained throughout the respective periods for which they are
       required:

       (a)   (Public and Products Liability) public and products liability insurance which covers
             legal liability for personal injury (including illness, disease or death) and/or property
             damage arising in connection with the SMWSA Works and SMWSA Activities for not
             less than $250 million per occurrence for public liability and $250 million per
             occurrence and in the aggregate for products liability. The policy referred to in this
             clause 24.1(a) must name as an additional insured party TfNSW, and must be
             maintained for a period commencing on the date of execution of the first SMWSA
             Contract and expiring on the date which is 12 months after the date of Completion
             of the SSTOM Works.
```

**Match 2: passage 194, PDF pages 31–31, score 0.659001. Complete expected evidence: no.

```text
SM considers to be a suitably qualified independent consultant engineer to
                   perform those services; and

            (ii)   holds:

                   (A)      professional indemnity insurance with:

                            (aa)   a limit of indemnity of not less than $20 million for any single
                                   claim and in the annual aggregate in respect of civil liability
                                   (including, without limitation, in connection with property
                                   damage, personal injury or death) arising from a breach of
                                   professional duty, whether owed in contract or otherwise, by
                                   reason of any act, error or omission by the SMWSA Independent
                                   Certifier or its employees, agents or consultants; and

                            (bb)   a deductible of not more than $1 million; and

                   (B)      workers' compensation insurance in accordance with the requirements
                            of Law; and

                   (C)      public liability insurance with:
```

**Match 3: passage 305, PDF pages 57–57, score 0.626016. Complete expected evidence: yes.

```text
on the date of execution of the
                     relevant SMWSA Contract and expiring on the date of Completion of the last
                     portion of the SCAW Works; and

             (ii)    in respect of the SSTOM Works, commencing on the date which financial close
                     is achieved under the relevant SMWSA Contract and expiring on the date of
                     Completion of the SSTOM Works,

             including but not limited to workers compensation, employers’ liability and motor
             vehicle compulsory third party insurance.

24.2   Payment of premiums

       SM must punctually pay or cause to be paid all premiums and other moneys payable in
       respect of any policy of insurance required to be effected under this Deed (including any
       premiums and other moneys payable under any policy of insurance required under clause
       24.1).

24.3   Risk of deductible
```

## Provenance

- PDF SHA-256: 29383bf63b32d42edebbfafd85adca9e2ce7be9a1b38ad49a0d28f4d859077ba
- Extracted text SHA-256: 8e5fe1b6c3e84d559b0679edec397654d2f1e185fd0dc5a1c07bb255ad7f74e4
- Frozen tree state: 179e4000795d29ccf2da3d64e375fdd69a0ff3e38cdeb7bf703635354385e633
- Full query fields, candidate inputs and all scores: /Volumes/My Passport for Mac/TomAssist/stream1-full-document-retrieval-20260915.npz
- Full signed maps for the four misses: /Volumes/My Passport for Mac/TomAssist/stream1-full-document-miss-fields-20260915.npz
- Full candidate fields were streamed through scoring and their hashes recorded. They can be reproduced exactly from the saved inputs and frozen native readings. Replayed miss candidates matched those hashes exactly.
- Native Stream1 source files and frozen readings remained unchanged. No Gemma generation, tree learning or deployed app changes were made.
