"""Transparent and conservative screening for Indian personal-loan products.

The engine evaluates only verified, published hard rules and treats missing or
conflicting data as limitations rather than approvals.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = ROOT / "data" / "lender_rules.csv"


def _num(value: Any) -> float | None:
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def calculate_emi(principal: Any, annual_rate_pct: Any, months: Any) -> float | None:
    """Return the standard reducing-balance EMI for a valid positive loan."""
    principal_value = _num(principal)
    rate_value = _num(annual_rate_pct)
    months_value = _num(months)

    if principal_value is None or principal_value <= 0:
        return None
    if months_value is None or months_value <= 0:
        return None
    if rate_value is None or rate_value < 0:
        return None

    monthly_rate = rate_value / 1200.0
    if monthly_rate == 0:
        return principal_value / months_value

    q = 1 + monthly_rate
    return principal_value * monthly_rate * (q ** months_value) / ((q ** months_value) - 1)


def validate_profile(profile: dict) -> list[str]:
    errors: list[str] = []

    age = _num(profile.get("age_years"))
    if age is not None and (age < 18 or age > 100):
        errors.append("age_years must be between 18 and 100")

    for field in (
        "monthly_net_income",
        "existing_monthly_emi",
        "requested_loan_amount",
        "requested_tenure_months",
        "business_vintage_months",
        "annual_net_income",
        "net_take_home_after_emi",
        "monthly_gross_income",
        "monthly_business_income",
    ):
        value = _num(profile.get(field))
        if value is not None and value < 0:
            errors.append(f"{field} must be a non-negative number")

    loan_amount = _num(profile.get("requested_loan_amount"))
    if loan_amount is not None and loan_amount <= 0:
        errors.append("requested_loan_amount must be greater than zero")

    tenure = _num(profile.get("requested_tenure_months"))
    if tenure is not None and tenure <= 0:
        errors.append("requested_tenure_months must be greater than zero")

    score = _num(profile.get("cibil_score"))
    score_missing = str(profile.get("cibil_score_missing", False)).lower() in {"true", "1", "yes"}
    if score is not None and not 300 <= score <= 900:
        errors.append("cibil_score must be 300-900 or blank")
    if score_missing and score is not None:
        errors.append("if cibil_score_missing is true, cibil_score should be blank")

    return errors


def _is_salaried(profile: dict) -> bool:
    employment = str(profile.get("employment_type", "")).strip().lower()
    return employment in {"salaried", "doctor", "professional", "lic_agent"}


def _is_self_employed(profile: dict) -> bool:
    employment = str(profile.get("employment_type", "")).strip().lower()
    return employment in {"self_employed", "self_employed_business", "business_owner"}


def _rule_applies(rule_name: str, profile: dict, is_salaried: bool, is_self_employed: bool) -> bool:
    name = rule_name.lower()

    if "self_employed" in name and not is_self_employed:
        return False
    if "salaried" in name and not is_salaried and "self_employed" not in name:
        return False

    if "government_defence" in name and str(profile.get("employer_category", "")).lower() not in {"government", "defence", "psu"}:
        return False
    if "corporate" in name and str(profile.get("employer_category", "")).lower() in {"government", "defence", "psu"}:
        return False
    if "salary_account" in name and "kotak" in str(profile.get("salary_account_lender", "")).lower():
        if "non_salary_account" in name:
            return False
    if "salary_account" in name and "non_salary_account" in name and "kotak" in str(profile.get("salary_account_lender", "")).lower():
        return False
    if "salary_account" in name and "salary_account" in name and "kotak" not in str(profile.get("salary_account_lender", "")).lower():
        if "non_salary_account" not in name:
            return False

    if name in {"min_agency_months"} and str(profile.get("profession", "")).lower() != "lic_agent":
        return False

    if name == "eligible_employment_types":
        allowed = str(profile.get("allowed_employment", "")).lower()
        return True

    return True


def _compare_rule(rule_name: str, profile: dict, rule_value: Any) -> tuple[str, str | float | int | None, str | float | int | None, str | None]:
    """Return the evaluation status, actual value, threshold and the unit for a rule."""
    name = rule_name.lower()

    if name == "required_salary_account_lender":
        actual = str(profile.get("salary_account_lender", "")).strip().lower()
        expected = str(rule_value).strip().lower()
        return ("passed" if actual == expected else "failed", actual, expected, "lender")

    if name in {"min_age", "min_age_salaried", "min_age_self_employed"}:
        actual = _num(profile.get("age_years"))
        threshold = _num(rule_value)
        return ("passed" if actual is not None and threshold is not None and actual >= threshold else ("unknown" if actual is None or threshold is None else "failed"), actual, threshold, "years")

    if name in {"max_age", "max_age_salaried", "max_age_self_employed"}:
        actual = _num(profile.get("age_years"))
        threshold = _num(rule_value)
        return ("passed" if actual is not None and threshold is not None and actual <= threshold else ("unknown" if actual is None or threshold is None else "failed"), actual, threshold, "years")

    if name in {"max_age_at_application", "max_age_at_maturity", "max_age_salaried_at_maturity", "max_age_self_employed_at_maturity"}:
        age = _num(profile.get("age_years"))
        tenure = _num(profile.get("requested_tenure_months"))
        threshold = _num(rule_value)
        actual = None if age is None or tenure is None else age + (tenure / 12.0)
        return ("passed" if actual is not None and threshold is not None and actual <= threshold else ("unknown" if actual is None or threshold is None else "failed"), actual, threshold, "years")

    if name in {"min_total_work_experience_months", "min_work_experience_months", "min_continuous_service_months", "min_service_months_government_defence", "min_service_months_corporate", "min_current_employer_months", "min_current_job_years", "min_business_vintage_months", "min_agency_months"}:
        actual = _num(profile.get("total_work_experience_months"))
        if name in {"min_current_employer_months", "min_current_job_years"}:
            actual = _num(profile.get("current_employer_months"))
        if name in {"min_business_vintage_months"}:
            actual = _num(profile.get("business_vintage_months"))
        if name in {"min_agency_months"}:
            actual = _num(profile.get("business_vintage_months"))
        threshold = _num(rule_value)
        return ("passed" if actual is not None and threshold is not None and actual >= threshold else ("unknown" if actual is None or threshold is None else "failed"), actual, threshold, "months")

    if name in {"min_monthly_net_income", "min_monthly_net_income_salaried", "min_monthly_net_income_government_defence", "min_monthly_net_income_corporate", "min_monthly_net_income_salary_account", "min_monthly_net_income_non_salary_account", "min_monthly_net_income_bank_employee", "min_monthly_income", "min_monthly_salary", "min_salary_credit"}:
        actual = _num(profile.get("monthly_net_income"))
        threshold = _num(rule_value)
        return ("passed" if actual is not None and threshold is not None and actual >= threshold else ("unknown" if actual is None or threshold is None else "failed"), actual, threshold, "INR/month")

    if name in {"min_cibil_score", "min_cibil_score_salaried", "min_cibil_score_self_employed"}:
        actual = _num(profile.get("cibil_score"))
        threshold = _num(rule_value)
        if actual is None and str(profile.get("cibil_score_missing", False)).lower() in {"true", "1", "yes"}:
            return ("unknown", None, threshold, "score")
        return ("passed" if actual is not None and threshold is not None and actual >= threshold else ("unknown" if actual is None or threshold is None else "failed"), actual, threshold, "score")

    if name in {"min_loan_amount"}:
        actual = _num(profile.get("requested_loan_amount"))
        threshold = _num(rule_value)
        return ("passed" if actual is not None and threshold is not None and actual >= threshold else ("unknown" if actual is None or threshold is None else "failed"), actual, threshold, "INR")

    if name in {"max_loan_amount", "max_loan_amount_inr"}:
        actual = _num(profile.get("requested_loan_amount"))
        threshold = _num(rule_value)
        return ("passed" if actual is not None and threshold is not None and actual <= threshold else ("unknown" if actual is None or threshold is None else "failed"), actual, threshold, "INR")

    if name in {"min_tenure_months", "min_loan_tenure_months"}:
        actual = _num(profile.get("requested_tenure_months"))
        threshold = _num(rule_value)
        return ("passed" if actual is not None and threshold is not None and actual >= threshold else ("unknown" if actual is None or threshold is None else "failed"), actual, threshold, "months")

    if name in {"max_tenure_months", "max_tenure_months_salary_account_bob", "max_tenure_months_salary_account_other_bank"}:
        actual = _num(profile.get("requested_tenure_months"))
        threshold = _num(rule_value)
        return ("passed" if actual is not None and threshold is not None and actual <= threshold else ("unknown" if actual is None or threshold is None else "failed"), actual, threshold, "months")

    if name == "min_net_take_home_after_emi":
        actual = _num(profile.get("net_take_home_after_emi"))
        threshold = _num(rule_value)
        return ("passed" if actual is not None and threshold is not None and actual >= threshold else ("unknown" if actual is None or threshold is None else "failed"), actual, threshold, "INR/month")

    if name == "min_annual_income_self_employed":
        actual = _num(profile.get("annual_net_income"))
        threshold = _num(rule_value)
        return ("passed" if actual is not None and threshold is not None and actual >= threshold else ("unknown" if actual is None or threshold is None else "failed"), actual, threshold, "INR/year")

    if name == "min_salary_multiple":
        income = _num(profile.get("monthly_gross_income"))
        actual = _num(profile.get("requested_loan_amount"))
        threshold = _num(rule_value)
        if income is None or threshold is None or actual is None:
            return ("unknown", actual, threshold, "INR")
        return ("passed" if actual <= income * threshold else "failed", actual, income * threshold, "INR")

    if name == "eligible_employment_types":
        allowed = str(rule_value).lower()
        employment = str(profile.get("employment_type", "")).lower()
        if "salaried" in allowed and employment in {"salaried", "doctor", "professional", "lic_agent"}:
            return ("passed", employment, allowed, "category")
        if "self-employed" in allowed and employment in {"self_employed", "self_employed_business", "business_owner"}:
            return ("passed", employment, allowed, "category")
        return ("failed", employment, allowed, "category")

    return ("unknown", None, None, "unknown")


def evaluate_applicant(profile: dict, rules_path: Path = RULES_PATH) -> dict:
    errors = validate_profile(profile)
    if errors:
        return {
            "profile_id": profile.get("profile_id", "unknown"),
            "profile_name": profile.get("profile_name", ""),
            "results": [],
            "validation_errors": errors,
            "recommendation": {"type": "no_defensible_candidate", "lender_name": None, "reason": "Input validation failed.", "caution": "Correct the profile before screening."},
        }

    rules = pd.read_csv(rules_path).fillna("")
    results: list[dict[str, Any]] = []
    is_salaried = _is_salaried(profile)
    is_self_employed = _is_self_employed(profile)

    for (lender_id, lender_name), group in rules.groupby(["lender_id", "lender_name"], sort=False):
        checks: list[dict[str, Any]] = []
        failed_reasons: list[str] = []
        missing_information: list[str] = []
        conflicting_rules: list[str] = []
        notes: list[str] = []
        advisory: list[str] = []

        for _, row in group.iterrows():
            rule_name = str(row.get("rule_name", ""))
            rule_type = str(row.get("rule_type", "")).lower()
            evidence_status = str(row.get("evidence_status", "")).strip().lower()
            note = str(row.get("research_notes", "")).strip()
            if note:
                notes.append(note)

            if evidence_status in {"conflict_needs_recheck", "stale", "needs_recheck", "pending"}:
                conflicting_rules.append(rule_name)

            if rule_type in {"preference", "guideline", "advertised"}:
                advisory.append(f"{rule_name}: {row.get('rule_value')} ({row.get('unit', '')})")
                continue

            if evidence_status != "verified_current":
                continue

            if not _rule_applies(rule_name, profile, is_salaried, is_self_employed):
                continue

            status, actual, threshold, unit = _compare_rule(rule_name, profile, row.get("rule_value"))
            if status == "failed":
                failed_reasons.append(f"{rule_name}: actual {actual} vs threshold {threshold} {unit}")
            elif status == "unknown":
                missing_information.append(f"{rule_name} cannot be evaluated without the required input")
            else:
                checks.append({
                    "rule": rule_name,
                    "actual": actual,
                    "threshold": threshold,
                    "unit": unit,
                    "passed": True,
                })

        if failed_reasons:
            status = "does_not_meet_published_criteria"
        elif conflicting_rules:
            status = "verification_required"
        elif missing_information:
            status = "insufficient_information"
        elif checks:
            status = "potential_match"
        else:
            status = "insufficient_information"

        def published_value(name: str):
            matches = group[group["rule_name"].astype(str).eq(name)]
            if matches.empty:
                return None
            value = matches.iloc[0].get("rule_value")
            if str(matches.iloc[0].get("evidence_status", "")).strip().lower() != "verified_current":
                return None
            return _num(value)

        results.append({
            "lender_id": lender_id,
            "lender_name": lender_name,
            "status": status,
            "checks": checks,
            "failed_reasons": failed_reasons,
            "missing_information": sorted(set(missing_information)),
            "conflicting_rules": sorted(set(conflicting_rules)),
            "advisory_preferences": sorted(set(advisory)),
            "published_max_loan_amount_inr": published_value("max_loan_amount"),
            "published_min_loan_amount_inr": published_value("min_loan_amount"),
            "advertised_starting_rate_pct": published_value("min_interest_rate_pct"),
            "advertised_max_rate_pct": published_value("max_interest_rate_pct"),
            "published_min_tenure_months": published_value("min_tenure_months"),
            "published_max_tenure_months": published_value("max_tenure_months"),
            "notes": sorted(set(notes))[:8],
            "source_urls": sorted(set(filter(None, group["source_url"].astype(str).dropna().tolist()))),
        })

    requested_amount = _num(profile.get("requested_loan_amount"))
    requested_tenure = _num(profile.get("requested_tenure_months"))
    candidates = []
    for item in results:
        if item["status"] != "potential_match":
            continue
        if item["advertised_starting_rate_pct"] is None:
            continue
        max_amount = item.get("published_max_loan_amount_inr")
        max_tenure = item.get("published_max_tenure_months")
        if max_amount is None or max_tenure is None:
            continue
        if requested_amount is not None and requested_amount > max_amount:
            continue
        if requested_tenure is not None and requested_tenure > max_tenure:
            continue
        candidates.append(item)

    candidates.sort(key=lambda item: item.get("advertised_starting_rate_pct") or float("inf"))
    if candidates:
        best = candidates[0]
        rec = {
            "type": "indicative_public_rate_candidate",
            "lender_id": best["lender_id"],
            "lender_name": best["lender_name"],
            "reason": f"Lowest advertised starting rate of {best['advertised_starting_rate_pct']}% p.a. among lenders with a matching potential profile and no failed hard rule.",
            "caution": "This is an indicative screening result only and not a confirmation of approval, a personalized quote, or a final lender decision.",
        }
    else:
        rec = {
            "type": "no_defensible_candidate",
            "lender_id": None,
            "lender_name": None,
            "reason": "No lender had enough non-conflicting published evidence to support a defensible candidate for this profile.",
            "caution": "Obtain current, lender-specific offers and verify product details before choosing a lender.",
        }

    return {
        "profile_id": profile.get("profile_id", "unknown"),
        "profile_name": profile.get("profile_name", ""),
        "validation_errors": [],
        "results": results,
        "recommendation": rec,
    }


def main():
    ap = argparse.ArgumentParser(description="Evaluate a profile against published lender rules.")
    ap.add_argument("--profile", help="Path to applicant CSV input")
    ap.add_argument("--output", help="Output CSV path")
    args = ap.parse_args()

    if args.profile:
        frame = pd.read_csv(args.profile)
    else:
        frame = pd.read_csv(ROOT / "data" / "test_profiles.csv")

    rows: list[dict[str, Any]] = []
    recommendations: list[dict[str, Any]] = []
    for profile in frame.to_dict(orient="records"):
        result = evaluate_applicant(profile)
        recommendation = result.get("recommendation", {})
        recommendations.append({
            "profile_id": result.get("profile_id", "unknown"),
            "profile_name": result.get("profile_name", ""),
            "recommendation_type": recommendation.get("type"),
            "indicative_candidate_lender": recommendation.get("lender_name"),
            "reason": recommendation.get("reason"),
            "caution": recommendation.get("caution"),
        })
        for lender in result.get("results", []):
            rows.append({
                "profile_id": result.get("profile_id", "unknown"),
                "profile_name": result.get("profile_name", ""),
                "lender_id": lender["lender_id"],
                "lender_name": lender["lender_name"],
                "status": lender["status"],
                "failed_reasons": " | ".join(lender["failed_reasons"]),
                "missing_information": " | ".join(lender["missing_information"]),
                "conflicting_rules": " | ".join(lender["conflicting_rules"]),
                "published_max_loan_amount_inr": lender.get("published_max_loan_amount_inr"),
                "advertised_starting_rate_pct": lender.get("advertised_starting_rate_pct"),
                "published_max_tenure_months": lender.get("published_max_tenure_months"),
            })

    output_path = Path(args.output) if args.output else ROOT / "data" / "test_outputs.csv"
    pd.DataFrame(rows).to_csv(output_path, index=False)
    rec_path = ROOT / "data" / "test_recommendations.csv"
    pd.DataFrame(recommendations).to_csv(rec_path, index=False)

    print(f"Wrote {len(rows)} lender-profile evaluations to {output_path}")
    print(f"Wrote {len(recommendations)} profile recommendations to {rec_path}")


if __name__ == "__main__":
    main()

