# Personal Loan Eligibility Model (India)

## Project status

This is a **rule-based screening prototype**, not a trained machine-learning model and not a lender approval system. It uses public, product-specific eligibility information to identify published criteria an applicant appears to meet, criteria they fail, and cases where public information is incomplete or conflicting.

**Research snapshot:** 12 October 2026. Search/indexed official page content was checked on this date. Before final academic submission, open each source URL directly and recheck the product terms and page date. Rules marked `conflict_needs_recheck`, `not_published`, or `guideline` must not be presented as definitive lender underwriting rules.

## Lender shortlist

The working shortlist contains 20 lenders: SBI, Bank of Baroda, PNB, Bank of India, HDFC Bank, Axis Bank, Kotak Mahindra Bank, Bajaj Finance, Canara Bank, IndusInd Bank, YES BANK, Federal Bank, South Indian Bank, Aditya Birla Finance, L&T Finance, Tata Capital, SMFG India Credit, Piramal Finance, IDFC FIRST Bank, and ICICI Bank. ICICI Bank replaces DMI Finance in the working list to retain exactly 20 lenders. DMI's six preliminary v1 research rows are retained in `data/extra_lenders_not_in_20.csv` and are not counted in the main shortlist.

The list is a practical shortlist of major public/private banks and NBFCs that advertise personal-loan products. It is **not a statistically ranked “top 20”** because a current, consistent market-share/ranking dataset was not established as part of this prototype. The project should state this limitation rather than claiming a definitive ranking.

## Files

- `data/lender_master.csv` — canonical list of 20 lenders and research caveats.
- `data/lender_rules.csv` — long-format source-backed rules with product category, rule type, source URL, research date, evidence status and notes.
- `data/input_variables.csv` — cleaned variable definitions and assignment-aligned source labels (`bureau`, `applicant`, `document`).
- `data/test_profiles.csv` — 12 synthetic profiles covering edge cases.
- `data/test_outputs.csv` — one row per profile/lender, produced by the model.
- `data/test_recommendations.csv` — indicative public-rate candidate per synthetic profile, where a cautious comparison is possible.
- `data/research_log.csv` — source URL and scope notes for each lender.
- `data/lender_rules_starter_original.csv`, `data/lender_rules_research_v1_original.csv` — preserved originals for audit trail.
- `data/extra_lenders_not_in_20.csv` — DMI preliminary research retained outside the main shortlist.
- `src/eligibility_model.py` — screening logic.
- `tests/test_eligibility_model.py` — basic automated tests.

## Method

1. Select a lender and a specific product/scheme where the official page provides one.
2. Store each criterion as a separate rule with its own source, date and evidence status.
3. Automatically check only explicit hard criteria that can be evaluated from the available applicant inputs.
4. Treat a preference (for example, a “preferred” credit score) as advisory rather than an automatic rejection rule.
5. Surface unknowns, missing inputs and source conflicts instead of inventing a value.
6. Do not describe a public-criteria pass as approval. Lenders apply private underwriting, bureau, fraud, documentation and policy checks that this prototype cannot reproduce.

## Run the web UI

A Streamlit interface is included in `app.py`. It collects applicant inputs, runs the existing rule engine, shows a lender-by-lender comparison with reasons/unknowns/source conflicts, estimates EMI using published advertised rates where available, and allows a CSV download. EMI figures are illustrative and exclude fees, insurance, APR differences and lender-specific pricing.

Python 3.10+ is recommended. From the project folder:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Streamlit will print a local URL (usually `http://localhost:8501`) to open in your browser. The app uses the same research CSV files and screening logic as the command-line prototype.

## Run the command-line model

```bash
python src/eligibility_model.py
```

This reads the synthetic profiles in `data/test_profiles.csv` and writes `data/test_outputs.csv`.

To run tests:

```bash
pytest -q
```

To evaluate a one-row CSV, use the same applicant column names as `data/test_profiles.csv`:

```bash
python src/eligibility_model.py --profile path/to/applicant.csv --output applicant_results.csv
```

## Output meanings

- `does_not_meet_published_criteria`: at least one applicable, verified hard criterion fails. This means the profile does not meet that published criterion; it is not a formal lender rejection.
- `insufficient_information`: the public rules are partial, inputs are missing, or there is an unresolved source/product conflict. This is the expected conservative result for most lenders until research coverage improves.
- `meets_checked_published_criteria` is reserved for a future version with a documented, complete criteria set. This current prototype does not claim that any applicant meets every internal underwriting rule.

The model can return an **indicative public-rate candidate** when the applicant has no failed checked hard criteria and a lender has a non-conflicting advertised starting rate, maximum amount and maximum tenure that cover the requested amount/tenure. It ranks only the public values it can compare. This is not a guaranteed “best lender,” not proof of eligibility, and not a guaranteed maximum loan amount. Rates and maximum amounts are advertised/product-level values and may not match an applicant's offer. Compare official personalised offer letters using APR, processing fees, net disbursal, EMI, tenure and prepayment terms before choosing.

## Key research caveats

- SBI's current indexed official page and an earlier capture disagree on the maximum loan amount and salary multiple. These fields are marked as conflicting and must not drive a loan amount estimate until reconciled.
- PNB's public FAQ covers specific categories such as certain permanent employees, LIC agents and doctors; it should not be generalized to all applicants.
- Kotak's eligibility page contains inconsistent age and credit-score descriptions. The conflict is preserved.
- HDFC's headline maximum is ₹50 lakh, with a page note that up to ₹75 lakh may be available subject to eligibility. These are separate values, not guaranteed entitlements.
- Canara Ready Cash is a specific digital scheme for existing salaried customers; it is not interchangeable with Canara Budget.
- Federal Bank rules refer to FedPremia, a salaried product.
- South Indian Bank page snippets show differences in advertised maximum amount and starting rate across pages/products.
- Piramal Finance's product and calculator pages show differing criteria. The rule rows identify the selected page and flag conflicts.
- Minimum CIBIL score, income and age may vary by product, applicant type, employer category, customer relationship and city. A published preference is not automatically a hard cutoff.
- FOIR/EMI affordability cannot be calculated reliably for all lenders because the required lender-specific ratio, pricing and underwriting inputs are not consistently public. No universal FOIR threshold is assumed.

## Findings this prototype can support

The reviewed public pages show that lender criteria vary substantially: examples include a required SBI salary-package account for its named scheme, employer/service-category differences at PNB and Bank of Baroda, a score threshold on South Indian Bank's published page, and separate salaried/self-employed conditions at SMFG India Credit. Some lenders publish starting rates and maximum tenures, while others leave key variables to an eligibility calculator or internal assessment. These differences justify storing product-specific rules rather than one generic rule per brand.

Do not claim a statistic such as “which rule rejects the most applicants” until the model has a complete, consistent rule set and all test profiles have been run against it. Synthetic profiles are illustrative only and are not evidence about real-world rejection rates.

## Limitations and next steps

1. Re-open all official pages and capture direct page dates/screenshots or archived source notes for submission.
2. Resolve the conflicts flagged in `lender_rules.csv`.
3. Add lender-specific FOIR/EMI calculations only when published formulas and rate assumptions are supported.
4. Add explicit product categories and branch/city variants where applicable.
5. Expand automated tests for each lender's exact scheme rules and the age-at-maturity calculation.
6. Improve and user-test the included Streamlit front end after the rules and tests are stable.
7. Never train a machine-learning model without appropriate, lawful, consented, representative approval data.

## Disclaimer

For educational use only. This tool is not financial advice, credit underwriting, a credit bureau report, a loan offer or a guarantee of approval. Applicants must confirm all current terms with the lender. Do not enter real personal identifiers into the synthetic test files or public repository.

## Prototype test run (12 synthetic profiles)

The bundled run evaluates 12 synthetic profiles against 20 lenders, producing 240 profile/lender rows. The current run recorded 103 `does_not_meet_published_criteria` results and 137 `insufficient_information` results. These counts are **only a software smoke-test summary** of the chosen synthetic profiles and partial rule set; they are not real-world rejection statistics and should not be presented as such.

A readable source-by-source research summary is in `data/research_notes_2026-10-12.md`.
