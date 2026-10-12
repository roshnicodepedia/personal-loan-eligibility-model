import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from eligibility_model import calculate_emi, evaluate_applicant, validate_profile
ROOT=Path(__file__).resolve().parents[1]

def base_profile(**updates):
    p={'profile_id':'TEST','profile_name':'Test','age_years':30,'employment_type':'salaried','monthly_net_income':60000,'monthly_gross_income':75000,'monthly_business_income':None,'existing_monthly_emi':5000,'cibil_score':780,'cibil_score_missing':False,'total_work_experience_months':36,'current_employer_months':24,'employer_category':'private_limited','profession':'other','salary_account_lender':'none','residency_status':'Indian resident','city':'Pune','requested_loan_amount':300000,'requested_tenure_months':36}
    p.update(updates); return p

def test_valid_profile_has_no_validation_errors():
    assert validate_profile(base_profile()) == []

def test_age_out_of_range_rejected():
    assert any('age_years' in e for e in validate_profile(base_profile(age_years=17)))

def test_negative_emi_rejected():
    assert any('existing_monthly_emi' in e for e in validate_profile(base_profile(existing_monthly_emi=-1)))

def test_zero_requested_amount_rejected():
    assert any('greater than zero' in e for e in validate_profile(base_profile(requested_loan_amount=0)))

def test_missing_score_is_allowed_as_unknown():
    assert validate_profile(base_profile(cibil_score=None,cibil_score_missing=True)) == []

def test_score_range_checked():
    assert any('300-900' in e for e in validate_profile(base_profile(cibil_score=950)))

def test_model_returns_20_lenders():
    out=evaluate_applicant(base_profile())
    assert len(out['results']) == 20

def test_conflicts_do_not_become_approval():
    out=evaluate_applicant(base_profile(salary_account_lender='State Bank of India'))
    sbi=next(x for x in out['results'] if x['lender_name']=='State Bank of India')
    assert sbi['status'] == 'verification_required'
    assert sbi['conflicting_rules']

def test_low_score_fails_hard_score_rules_where_applicable():
    out=evaluate_applicant(base_profile(cibil_score=620))
    sib=next(x for x in out['results'] if x['lender_name']=='South Indian Bank')
    assert sib['status'] == 'does_not_meet_published_criteria'

def test_age_below_common_floor_fails_some_lenders():
    out=evaluate_applicant(base_profile(age_years=20))
    hdfc=next(x for x in out['results'] if x['lender_name']=='HDFC Bank')
    assert hdfc['status'] == 'does_not_meet_published_criteria'


def test_recommendation_is_explicitly_indicative():
    out=evaluate_applicant(base_profile(salary_account_lender='none'))
    assert out['recommendation']['type'] in ('indicative_public_rate_candidate','no_defensible_candidate')
    assert 'not a confirmation' in out['recommendation']['caution'] or 'personalised offers' in out['recommendation']['caution']


def test_age_20_has_no_candidate_without_published_age_floor():
    out=evaluate_applicant(base_profile(age_years=20))
    assert out['recommendation']['type'] == 'no_defensible_candidate'


def test_emi_formula_matches_reducing_balance_case():
    emi = calculate_emi(principal=1000000, annual_rate_pct=12.0, months=12)
    assert round(emi, 2) == 88848.79


def test_statuses_include_potential_match_and_verification_required():
    strong_profile = base_profile(age_years=30, monthly_net_income=90000, requested_loan_amount=300000, requested_tenure_months=36)
    out = evaluate_applicant(strong_profile)
    assert any(r["status"] == "potential_match" for r in out["results"])

    conflicted = evaluate_applicant(base_profile(salary_account_lender="State Bank of India"))
    assert any(r["status"] == "verification_required" for r in conflicted["results"])


def test_missing_or_invalid_inputs_are_reported_conservatively():
    out = evaluate_applicant(base_profile(requested_loan_amount=0))
    assert out["validation_errors"]
