# WP-42 SCAW sensitivity report and owner cut sheet

**Status:** CONTRACT TEXT HELD OUTSIDE REPOSITORY - OWNER RULING REQUIRED

## Decision boundary

The owner selected the executed SCAW deed as the corpus. This report neither recommends nor rejects any candidate passage. It records exactly what a later corpus-text commit would retain permanently so the owner can decide whether the text may enter Git.

No passage text, definition body or defined-term list is present in this repository. The text-bearing outputs are held at:

`/private/tmp/tom-assist-wp42-scaw-corpus-prep-a9dda3b6/`

The source volume was read only. The source PDF was not copied or modified.

## Source and extraction identity

- Source file: `SCAW D_C Deed - Executed 1 March 2022.pdf`
- Source size: 22,399,742 bytes; 343 PDF pages; SHA-256 `a9dda3b6376d27bd76a01adc4a7692838b4271a9967c53f69fa6883dafc14f99`.
- Extractor: Poppler `pdftotext` 26.03.0 with `-layout -enc UTF-8 -eol unix`.
- Two independent extractions were byte-identical: 1,215,976 bytes; SHA-256 `7d0b79c1fb5403db044f1ea78da3a592707c2169f32fe5bb44ce138006951c12`.

## What a later shortlist commit would add

The held shortlist contains exactly 40 passages and 46,829 characters copied verbatim from the layout extraction. Its text-bearing JSON is 65,243 bytes, SHA-256 `a9502fa24d09f3eb4539d44dcb5b2e8269b069c9ef86603023e331d85459bb65`. The passages range from 149 to 2,590 characters and cover PDF pages 10 through 336.

The shortlist text contains:

- nine occurrences of the name `Sydney Metro`, primarily in the project name;
- 100 references to the role `SCAW Contractor` and 85 references to `Principal` or `Principal's`;
- six references to a Design, Construction or Project Contract Sum; two to Direct Costs; one to Profit Margin; two to liquidated damages; two to a debt due; seven to payment; and eight to a Claim;
- procedural time periods, clause and schedule cross-references, and the date 24 December 2026;
- operational subject matter including traffic, approvals, archaeological artefacts, remediation, design review, delay, suspension, defects, insurance and contract amendment.

The shortlist contains no dollar-denominated amount, ABN, email address, URL, telephone number, personal honorific/name pattern or signature block. It does not spell out `CPB Contractors` or `United Infrastructure`; however, the source deed itself names Sydney Metro, CPB Contractors Pty Limited and United Infrastructure Pty Limited as parties or contracting entities. Omitting their legal names from the shortlist does not make the excerpted obligations anonymous.

The held glossary candidate is separate from the shortlist. It contains 531 human-authored defined-term surface forms from PDF pages 10-69, totalling 12,192 term characters. Its JSON is 16,885 bytes, SHA-256 `9c62712ebb830458199ae71c00fa220c53cbbeaed17c47b24daa4596bb23bb0d`. It contains no definition body or type, but surface forms include `CPB`, `CPB Website`, Sydney Metro project terms and commercial labels such as `Construction Contract Sum`, `Design Contract Sum`, `Initial Payment`, `Offsite Disposal Contingency Sum`, `Delay Costs Maximum Daily Amount` and `Profit Margin`.

The complete 1,215,976-byte extraction is retained outside the repository for offset verification. It is more sensitive than the shortlist because it contains the entire executed deed, including party details, commercial amounts and execution material. It is validation evidence only and is not proposed for a later Git commit.

## Licence and confidentiality boundary

This repository has no `LICENSE`, `LICENCE` or equivalent licence file. Nothing in the repository establishes permission to redistribute the deed or derived excerpts. The deed's disclosure provisions, government provenance or possible public availability are not a software/content licence and are not treated as authorization here. Git history is durable and difficult to purge completely after a push, fork or archive.

The owner should therefore rule separately on:

1. whether the 46,829 characters of shortlisted clause text may be committed;
2. whether the 531 surface terms may be committed;
3. whether the repository's visibility and downstream retention are appropriate for an executed commercial instrument.

Until that ruling, all text-bearing outputs remain outside the repository and the manifest remains hash-only.

## Owner cut sheet - no recommendation

An empty family list marks a deliberately plain narrative/control passage. Family tags describe shortlist construction only; they are not gold parser labels.

| ID | PDF page | Clause | Difficulty | Family tags | Characters | Text SHA-256 |
|---|---:|---|---|---|---:|---|
| SCAW-001 | 10 | Recitals A-D | easy | narrative/control | 703 | `b43773bd82c9943bc325ee2bf735c35b78653439e44b8b0fc1a4eb4f808b15b6` |
| SCAW-002 | 77 | 3.1 | easy | narrative/control | 1,624 | `ef5839d19dcab4c8f19b750317e7e4135428eb66173fda1a27f9e9d716fafcec` |
| SCAW-003 | 78 | 3.2 | medium | narrative/control | 2,251 | `0bb61f2040b69bf794f82c646645ef68f6be839f823970ebeedc9152c2beb825` |
| SCAW-004 | 74 | 1.5 | hard | rule/constraint; supersession | 2,360 | `5e1a712033a32d21ce21e6f704c72cc96e12ec32acc3aa97fb9a29419142296b` |
| SCAW-005 | 75 | 1.6 | medium | causation; supersession | 1,059 | `bcd3cb00616474feeb7912ec9c75f2346b5acb3f988f93089377325eb9eb38a3` |
| SCAW-006 | 77 | 2.4(b)-(c) | medium | causation; dependency; supersession | 1,246 | `3ace04af675fb3a653133704446c0a11c1c36662124036232cf7034075bd93b7` |
| SCAW-007 | 79 | 4.1(a)-(d) | easy | rule/constraint | 1,015 | `28573f8fe88622c3663dbdeaa7ca5c46481299b51d7fc9a47d653b9c69e2a226` |
| SCAW-008 | 86 | 4.5 | easy | rule/constraint | 969 | `d360b060e2a4c40f84f85f0a904fd75343a1ce2c96a6b336224f1a951f235acb` |
| SCAW-009 | 98 | 4.20(a)-(b) | easy | rule/constraint | 626 | `ad28a52b4290e0599db20cfe93322b349909256544e67fc99c8e0ad061493665` |
| SCAW-010 | 106 | 6.6 | easy | rule/constraint | 678 | `15d266e2a0b3b60989d42b2aaffaf1ec49a6a36a7cbe2a61795e81dfa98da47e` |
| SCAW-011 | 109 | 7.3(a)(i) | hard | causation; dependency | 1,501 | `d8f5a66f2b31fc4d9eca8159f30cde17f97e9bc6088199372cd992df3d67e2b9` |
| SCAW-012 | 112 | 7.4(a)(ii)-7.4(b) | hard | dependency; supersession | 1,177 | `0ea8f8766618858963e9e0d67ed58c61ab5bce56ee61bf224ef1bb5f0c27be1e` |
| SCAW-013 | 115 | 7.9 | easy | dependency; rule/constraint | 616 | `47113059194117a721250d8de3f06abb2a7315ed37e7de066dc81dd022d4df73` |
| SCAW-014 | 132 | 11.3 | medium | dependency; supersession | 1,193 | `ae3757f3f9fb918c999e14e73cf1edc855096043579fd3c85c0df1c4eec63c59` |
| SCAW-015 | 134 | 11.4(b) | hard | dependency; supersession | 1,132 | `6f7077dd150bcf51715e9bb0c9e0ca14d0970aaf2f87aedb2a306f48082b25f2` |
| SCAW-016 | 135 | 12.1(b)-(c) | medium | causation; rule/constraint | 1,137 | `0479a250c31804c9cc826b0efe977401ae00f5d30dc34e640ff67b6674e8f8d0` |
| SCAW-017 | 137 | 12.2(b)-(c) | hard | dependency; rule/constraint | 1,220 | `4262de4ecc7f9e4f5f4ef7ce03fe8f6c836947d242d7c7cf1446a985db32fdfc` |
| SCAW-018 | 150 | 12.12 | medium | dependency; rule/constraint | 996 | `26657647c1405675c62d24921453252fab160755903551235a21ef8f59c20b2c` |
| SCAW-019 | 150 | 12.13(a)-(b) | medium | causation; rule/constraint | 1,512 | `2337236142099cc7b27b1a7efe00308a6bcd8e26ae427549b79cbed1a7336eca` |
| SCAW-020 | 164 | 12.19(f)-(g) | medium | dependency; supersession | 1,054 | `b7934a2439455d54ba9de24fcc325c7a94abe46952a480ef104b8f25ad78a900` |
| SCAW-021 | 167 | 12.20(g)-(h) | medium | dependency; supersession | 1,365 | `ae282b28d7c325b1bead2b9298d2691690033cd8545b06754f9754fe564a1a59` |
| SCAW-022 | 167 | 12.20(i) | hard | dependency; rule/constraint | 828 | `799bc6dd85c7c208fa10e3f2e65128c293bb5f629e1b11b1cbe9c6c32bd49204` |
| SCAW-023 | 182 | 12.28(c)(ii)(G)-12.28(d) | hard | causation; supersession | 1,298 | `d5cc3358122989828fc571150161aed13266e207580713fa6809f10ce49de478` |
| SCAW-024 | 193 | 14.4(b)-(c) | medium | dependency; rule/constraint | 832 | `bbf7ed06d2d3b34d3bb85195e52d43ca318c7e6da875b32552b475471ae6b3f1` |
| SCAW-025 | 202 | 15.3(a)-(c) | medium | rule/constraint; supersession | 2,590 | `685e49739ec35f4e20557edce6cc1810f0fefbd5ab0dba36e578b879fc966afd` |
| SCAW-026 | 203 | 15.3(e)-(g) | hard | causation; supersession | 1,545 | `cc4f1630487245bac694e373794c41932624da84da35ef0d64024ab81c240612` |
| SCAW-027 | 210 | 15.10 | medium | dependency; rule/constraint | 1,454 | `d56e45a0970238da9a859d2554cf532741604e643f615be669d4ada49276970a` |
| SCAW-028 | 213 | 16.4(b) | easy | causation; rule/constraint | 688 | `b5a90d3ec3a0fab9225c0d4f0be5912a40580ead31a5d06568c3ef8993c243d1` |
| SCAW-029 | 135 | 12.1(e) | medium | causation; dependency | 1,006 | `4d7148cce4abe7cd8a289385314819e3a6e16c03e8aa49b144444981002cc2cb` |
| SCAW-030 | 221 | 16.13(j)-(k) | hard | dependency; supersession | 1,928 | `2d5d53fd515d59740b3e47e86424be623d99d128cc38e6eece66755650aba935` |
| SCAW-031 | 232 | 17.12 | easy | rule/constraint | 267 | `d04e5e5e5b1b4d6fd7d10384c00b6f0567b08ed84b46dd698f5e779c991543b9` |
| SCAW-032 | 240 | 18.10 | easy | rule/constraint | 825 | `df5f39c5e42c4f7513a5ff6bd06f6d8ba2ed920db97ea8d0ca89c72bfb497a5b` |
| SCAW-033 | 248 | 18.21(c)(ii) | medium | dependency; rule/constraint | 976 | `8af540af2ccda543562425637786f0e9be3c93abf41375474ab3b24469161ec49` |
| SCAW-034 | 250 | 19.5-19.6(a) | medium | causation; dependency | 1,614 | `d52ac28f571230af86983527f224ff2a60ecf2f95c7757949c7497a3f8ce0493` |
| SCAW-035 | 252 | 19.6(e)-(f) | hard | causation; dependency | 854 | `82db80be37b7d6d4e119a04f03ad631422e567530444aed787c972dd866b983c` |
| SCAW-036 | 255 | 19.8 | hard | causation; dependency | 2,406 | `75c49b23786f61639daaf9be65f975529147094630363a7e078b1f3d888428b6` |
| SCAW-037 | 260 | 19.11(d)-(e) | medium | causation; rule/constraint | 1,420 | `9fe1f670972dc08ea6926a2978622926014aee12f07d54344b25f583b5ed06a7` |
| SCAW-038 | 296 | 23.17(b) | easy | causation | 305 | `cda89ab179638a39c999d32d1f497378430178d729b8590bfc7eb5a4f6739d4` |
| SCAW-039 | 334 | 32.6 | easy | rule/constraint; supersession | 149 | `4728a6b3d9faf589b89986a9fa387b78c55740037f0baf8a8f51a54410f8c4ef` |
| SCAW-040 | 336 | 32.11 | easy | rule/constraint; supersession | 410 | `659e5485613023971304f85fc03da6bf35f01261b9871e42a187681b264de4d7` |

Coverage totals are causation **14**, dependency **19**, rule/constraint **21** and supersession **14**. Difficulty totals are easy **13**, medium **16** and hard **11**. The owner may cut any row; no row is recommended over another.
