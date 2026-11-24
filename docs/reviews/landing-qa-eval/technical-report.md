# Landing QA evaluation

- Label basis · technical-provisional (Codex (technical baseline))
- Cases · 24
- Casebook SHA-256 · `4a9c1b5377c194ab33d65bcf6f9081e6c04ac84af67271a94465de7541717da6`
- Manifest digest · `f47ddd7984fc1aa9d4fe3ba325ce917b49e8cfa4d504debd1ad8d7bb58003c9a`
- Runtime fingerprint · `dc3fae426d39398508787d5ddb74fad2612bd4bafa901485abc48b1f1a1c1d9a`

Each case, field and rule counts once. A zero denominator is shown as n/a.

| Role | Rule | Labels + | TP | FP | FN | Precision | Recall |
|---|---|---:|---:|---:|---:|---:|---:|
| content | cta_action | 1 | 1 | 2 | 0 | 33.3% | 100.0% |
| content | brief_alignment | 1 | 1 | 1 | 0 | 50.0% | 100.0% |
| content | brand_alignment | 1 | 1 | 1 | 0 | 50.0% | 100.0% |
| content | audience_alignment | 2 | 2 | 1 | 0 | 66.7% | 100.0% |
| content | offer_alignment | 1 | 1 | 1 | 0 | 50.0% | 100.0% |
| content | brand_instruction | 2 | 1 | 0 | 1 | 100.0% | 50.0% |
| content | claim_evidence | 3 | 0 | 1 | 3 | 0.0% | 0.0% |
| content | quote_context | 3 | 3 | 0 | 0 | 100.0% | 100.0% |
| seo | page_alignment | 3 | 2 | 4 | 1 | 33.3% | 66.7% |
| seo | intent_alignment | 3 | 1 | 2 | 2 | 33.3% | 33.3% |
| seo | metadata_length | 2 | 2 | 0 | 0 | 100.0% | 100.0% |
| seo | duplicate_metadata | 2 | 2 | 0 | 0 | 100.0% | 100.0% |
| seo | claim_evidence | 2 | 2 | 1 | 0 | 66.7% | 100.0% |
| seo | quote_context | 0 | 0 | 0 | 0 | n/a | n/a |
| Both | **Micro** | 26 | 19 | 14 | 7 | 57.6% | 73.1% |

## Disagreements

| Case | Field | Rule | Result |
|---|---|---|---|
| B05 | meta_description | claim_evidence | FP |
| B06 | meta_description | page_alignment | FP |
| B06 | page_title | page_alignment | FP |
| B06 | search_intent | intent_alignment | FP |
| C01 | call_to_action | cta_action | FP |
| C02 | body_copy | claim_evidence | FP |
| G01 | call_to_action | cta_action | FP |
| L01 | body_copy | audience_alignment | FP |
| L01 | body_copy | brand_alignment | FP |
| L01 | body_copy | brief_alignment | FP |
| L01 | body_copy | offer_alignment | FP |
| L04 | meta_description | page_alignment | FP |
| L04 | page_title | page_alignment | FP |
| L04 | search_intent | intent_alignment | FP |
| C05 | page_title | page_alignment | FN |
| C05 | search_intent | intent_alignment | FN |
| G02 | body_copy | claim_evidence | FN |
| G03 | body_copy | claim_evidence | FN |
| G06 | search_intent | intent_alignment | FN |
| L02 | body_copy | brand_instruction | FN |
| L02 | body_copy | claim_evidence | FN |
