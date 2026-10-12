# Personal Loan Eligibility Model (India)

## Project overview

This project is a transparent, rule-based screening prototype for personal loans from 20 Indian lenders. It compares a synthetic applicant profile with the published criteria currently captured in the research CSV. It does **not** train an ML model and does not make or guarantee a lender's approval decision.

**Research snapshot:** 12 October 2026. The date records the current research snapshot, not proof that every page was directly re-opened on that date. Source provenance and product conflicts remain limitations; review the source URLs and rule evidence statuses before relying on a rule.

## Lender selection criteria

The 20-lender shortlist includes major public-sector and private-sector banks and non-bank financial companies (NBFCs) that advertise personal-loan products and have publicly accessible product, eligibility, FAQ or calculator information. The goal is breadth across lender types and products, not a statistical market-share ranking. No consistent, current ranking dataset was used, so the list is not claimed to be the definitive “top 20” by market share or approvals.

The shortlist is: SBI, Bank of Baroda, Punjab National Bank, Bank of India, HDFC Bank, Axis Bank, Kotak Mahindra Bank, Bajaj Finance, Canara Bank, IndusInd Bank, YES BANK, Federal Bank, South Indian Bank, Aditya Birla Finance, L&T Finance, Tata Capital, SMFG India Credit, Piramal Finance, IDFC FIRST Bank and ICICI Bank. DMI Finance is retained as out-of-scope research in `data/extra_lenders_not_in_20.csv`, not counted in the 20.

## Repository contents

- `data/input_variables.csv` — input variables, definitions, units, types and sources.
- `data/lender_master.csv` — the 20-lender shortlist.
- `data/lender_rules.csv` — long-format lender rules, source URLs, snapshot dates, evidence statuses and research notes.
- `data/test_profiles.csv` — 12 synthetic profiles, including low credit score, high existing EMI, new job, self-employed, missing score, low income and age-edge cases.
- `data/test_outputs.csv` — latest generated profile/lender evaluation output (240 rows).
- `data/test_recommendations.csv` — latest generated per-profile recommendation/decision output.
- `data/research_log.csv` and `data/research_notes_2026-10-12.md` — research trace and source caveats.
- `data/lender_rules_starter_original.csv` and `data/lender_rules_research_v1_original.csv` — preserved source datasets for audit history.
- `src/eligibility_model.py` — screening engine and EMI/affordability calculations.
- `app.py` — Streamlit user interface.
- `tests/test_eligibility_model.py` — automated validation and regression tests.
- `.gitignore` — excludes Python caches, virtual environments and IDE files.

## Approach

1. Collect publicly available product eligibility, amount, rate and tenure rules. A rule is stored with a source URL, snapshot date and evidence status.
2. Check explicit, usable hard rules against the applicant profile. A `preference` or `guideline` is advisory, not an automatic rejection.
3. Keep failures, unknowns and source conflicts separate. A missing value is not treated as a pass.
4. Return an overall screening decision:
   - `potentially_eligible`: at least one lender has a potential match against the hard rules currently checked.
   - `not_eligible_under_checked_published_criteria`: every lender fails at least one checked published hard criterion.
   - `unable_to_determine`: incomplete/conflicting public rules prevent a defensible decision.
5. For each lender, return the checked status and reasons, available advertised product terms, and an indicative applicant-specific maximum amount when the available data supports an estimate.
6. Rank a comparison candidate by advertised starting rate only when the profile has a potential match and the lender has sufficient recorded criteria and product terms. This is not a personalized offer or a guarantee of approval.

## Assumptions and rules not explicitly listed

Lenders do not disclose every underwriting rule. The research file therefore distinguishes `verified_current`, `conflict_needs_recheck`, `not_published`, `guideline` and other evidence statuses. The model only treats verified hard rules as hard screening checks. Conflicting or incomplete rows are surfaced instead of being silently treated as facts.

For affordability, FOIR is the share of monthly income committed to existing and proposed EMI payments. Where a usable lender-specific FOIR is present, the model estimates proposed-loan EMI using the recorded advertised starting rate; if a usable rate is absent, an estimated 18% annual rate is used and noted. For a lender without a usable FOIR, the **50% FOIR value is an explicit model assumption**, not a claim about that lender's policy. These assumptions are also recorded as `estimated_assumption` rows in `data/lender_rules.csv`, with an explanation and no fabricated lender source URL. A missing advertised starting rate may also be replaced with an estimated 18% annual rate solely for indicative amount calculations. The generated result includes notes/flags for these estimates.

The indicative applicant maximum is the minimum of the recorded product cap, a published salary-multiple cap where present, and the FOIR-supported amount where calculable. A maximum amount calculated with estimated FOIR or rate must be read as a scenario estimate, not as an offer. If the necessary income, tenure or product data is unavailable, the model may return no applicant-specific maximum amount.

Unlisted rules are investigated through public product pages, FAQs, eligibility calculators, rate/tenure tables and product terms where available. The current dataset does not prove that every possible rule has been found. In particular, city, employer category, existing EMI, salary multiple and FOIR are not consistently published for all lenders.

## Insights from the current synthetic test run

The latest run evaluates 12 synthetic profiles against 20 lenders, producing 240 profile/lender rows. Status counts are:

| Status | Count |
|---|---:|
| `does_not_meet_published_criteria` | 99 |
| `potential_match` | 74 |
| `verification_required` | 37 |
| `insufficient_information` | 30 |

Across these synthetic outputs, the most frequently recorded failed checked rules are employment-type mismatch (38 rows), current-employer tenure (24), minimum age (14), minimum CIBIL score (7), and total work experience (6). These are counts of rule failures in this hand-built synthetic test set, **not** estimates of real-world lender rejection rates. Counts can include multiple failures for a profile/lender pair.

The dataset shows why rules should be product- and lender-specific: lenders differ in age and service requirements, employer and employment categories, salary-account conditions, minimum income, credit-score criteria, product limits and the amount of information they publish. In this run, the low-score profile (P02), high-existing-EMI profile (P03), and missing-score profile (P07) receive no rate-based candidate rather than being shown a misleading “best lender.” Several lenders have incomplete or conflicting source records, which is why `verification_required` and `insufficient_information` are legitimate outputs.

## Running the project

Python 3.10+ is recommended. From the repository folder:

```bash
pip install -r requirements.txt
python src/eligibility_model.py
pytest -q
streamlit run app.py
```

The model command regenerates `data/test_outputs.csv` and `data/test_recommendations.csv` from `data/test_profiles.csv`. To evaluate a single CSV profile:

```bash
python src/eligibility_model.py --profile path/to/applicant.csv --output applicant_results.csv
```

## Output meanings

- `does_not_meet_published_criteria`: at least one applicable, verified hard criterion failed. This is not a formal lender rejection.
- `potential_match`: no checked hard criterion failed, but this is not proof that all lender rules or internal underwriting conditions are met.
- `insufficient_information`: missing applicant data or incomplete published criteria prevents a reliable conclusion.
- `verification_required`: one or more material source conflicts need review.
- `potentially_eligible`, `not_eligible_under_checked_published_criteria`, and `unable_to_determine` are the profile-level decision labels. The model deliberately avoids forcing a binary decision when the public evidence is insufficient.
- `indicative_public_rate_candidate` identifies the lowest advertised starting rate among candidates that pass the prototype's screening and recorded product checks. It is not a guarantee that the lender will approve the application or offer that rate.

Interest rates, product caps and tenure are advertised product-level values unless explicitly stated otherwise. Applicant-specific amounts are estimates and can depend on assumptions. Actual offers may differ due to underwriting, credit history, employer, city, fees, insurance, APR, documentation and lender policy.

## Limitations and next steps

1. Re-open official sources directly and record the actual access date and relevant page evidence for each rule. The current snapshot date alone does not prove every source was directly verified.
2. Resolve rows marked `conflict_needs_recheck`, and distinguish official lender pages from comparison sites and indexed snippets.
3. Improve coverage for city, employer category, salary-account relationship, FOIR, existing EMI, salary multiples and self-employed applicants.
4. Add more product-specific variants and rules only when supported by a traceable source.
5. Add more regression tests for every rule type and for age-at-maturity, salary-account variants, missing data and estimated affordability.
6. User-test the Streamlit UI and confirm that all status labels, source notes and estimates are clear.
7. Do not train a machine-learning model without appropriate, lawful, representative approval data.

## Disclaimer

For educational use only. This prototype is not financial advice, a credit bureau service, lender underwriting, a loan offer or a guarantee of approval. Verify current product terms directly with lenders. Use synthetic profiles in the repository and do not commit PAN, Aadhaar, account numbers, passwords or other personal identifiers.
