# Personal Loan Eligibility Model (India)

## Status
This repository is at the research/data-schema stage. It is not a completed lender recommendation engine yet.
Research snapshot date: 2026-10-11.

## Files
- `lender_master.csv`: the working 20-lender shortlist and research status.
- `lender_rules_starter.csv`: long-format starter rules with source URLs, source dates, evidence status, and notes.
- `input_variables.csv`: proposed applicant input schema.

## Important data-quality rules
1. `not_yet_verified` means the rule is unknown or not yet fully checked. It does not mean an applicant passes.
2. A preferred credit score is not necessarily a hard rejection threshold.
3. Product-specific criteria must not be mixed across salaried, self-employed, pre-approved, or digital products.
4. Public eligibility estimates are not actual lender approval decisions.
5. Recheck every source before final submission because lender pages and promotional rates can change.
6. Never represent an estimated FOIR, salary multiplier, or minimum credit score as official unless a source explicitly supports it.

## Next steps
1. Replace/verify the final lender shortlist and remove duplicate candidates.
2. Complete source-backed rule rows for every lender.
3. Add rule-level source dates and preserve conflicts between public sources.
4. Implement deterministic eligibility checks, EMI calculations, and tests only after the research table is sufficiently complete.
