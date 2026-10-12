from __future__ import annotations
import sys
import math
from pathlib import Path
import pandas as pd
import streamlit as st
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from eligibility_model import evaluate_applicant  # noqa: E402
st.set_page_config(
    page_title="Personal Loan Eligibility Checker",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown("""
<style>
:root { --navy:#13294b; --blue:#1769e0; --pale:#eef5ff; --line:#e3eaf4; }
.block-container { padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1440px; }
[data-testid="stSidebar"] { background: #f6f9fe; border-right: 1px solid #e5ebf5; }
.hero { padding: 1.5rem 1.7rem; border-radius: 18px; background: linear-gradient(115deg,#eaf3ff 0%,#f7faff 68%,#e7f1ff 100%); border:1px solid #dce9fb; margin-bottom:1rem; }
.hero h1 { color:#13294b; margin:0 0 .45rem 0; font-size:2rem; }
.hero p { color:#526985; margin:0; font-size:1rem; }
.section-title { color:#13294b; font-size:1.2rem; font-weight:700; margin:.4rem 0 .8rem; }
.small-muted { color:#64748b; font-size:.85rem; }
.result-card { padding:1rem; border:1px solid #e1e8f2; border-radius:14px; background:white; min-height:105px; }
.result-label { color:#64748b; font-size:.85rem; }
.result-value { color:#13294b; font-size:1.45rem; font-weight:750; margin-top:.25rem; }
.disclaimer { border-left:4px solid #f0b429; background:#fff9e8; padding:.8rem 1rem; border-radius:8px; color:#6b561b; font-size:.88rem; }
.stButton > button[kind="primary"] { background:#1769e0; border-color:#1769e0; border-radius:10px; font-weight:650; min-height:2.8rem; }
</style>
""", unsafe_allow_html=True)
with st.sidebar:
    st.markdown("## 🏦 LoanLens")
    st.caption("Personal Loan Eligibility Checker")
    page = st.radio("Navigation", ["Check eligibility", "Compare lenders", "About this project"], label_visibility="collapsed")
    st.divider()
    st.markdown("### Included in this prototype")
    st.markdown("- 20 Indian lenders\n- Public-rule screening\n- Reason and conflict explanations\n- Indicative rate comparison")
    st.divider()
    st.caption("Educational prototype • No lender approval guarantee")
st.markdown("""
<div class="hero">
  <h1>Personal Loan Eligibility Checker</h1>
  <p>Enter applicant details to compare them with published criteria across 20 Indian lenders — transparently, with reasons and caveats.</p>
</div>
""", unsafe_allow_html=True)
@st.cache_data
def get_lenders():
    df = pd.read_csv(ROOT / "data" / "lender_master.csv")
    return df["lender_name"].dropna().tolist()
lenders = get_lenders()
def format_inr(value):
    if value is None or pd.isna(value):
        return "Not available"
    return "₹" + format(int(round(float(value))), ",")
def estimate_emi(principal, annual_rate_pct, months):
    """Calculate indicative EMI; this excludes fees, insurance and lender-specific charges."""
    if principal is None or annual_rate_pct is None or months is None or months <= 0:
        return None
    monthly_rate = float(annual_rate_pct) / 1200
    if monthly_rate == 0:
        return float(principal) / int(months)
    factor = (1 + monthly_rate) ** int(months)
    return float(principal) * monthly_rate * factor / (factor - 1)
if page in ("Check eligibility", "Compare lenders"):
    st.markdown('<div class="section-title">1 · Applicant details</div>', unsafe_allow_html=True)
    with st.form("applicant_form"):
        a, b, c = st.columns(3)
        with a:
            age = st.number_input("Age (years)", min_value=18, max_value=100, value=28, step=1)
            employment_label = st.selectbox("Employment type", ["Salaried", "Self-employed"])
            monthly_income = st.number_input("Monthly net income (₹)", min_value=0, value=50000, step=5000)
            existing_emi = st.number_input("Existing monthly EMI (₹)", min_value=0, value=5000, step=1000)
        with b:
            credit_unknown = st.checkbox("I don't know my CIBIL score")
            cibil_score = st.number_input("CIBIL score", min_value=300, max_value=900, value=720, step=5, disabled=credit_unknown)
            job_months = st.number_input("Time with current employer (months)", min_value=0, value=24, step=1)
            work_months = st.number_input("Total work experience (months)", min_value=0, value=36, step=1)
        with c:
            employer_category = st.selectbox("Employer category", ["private_limited", "MNC", "government", "PSU", "defence", "other"])
            profession = st.selectbox("Profession", ["other", "doctor", "LIC agent", "business owner", "professional"])
            salary_account = st.selectbox("Salary account lender", ["none"] + lenders)
            city = st.text_input("City", value="Ahmedabad")
        st.divider()
        st.markdown('<div class="section-title">2 · Loan request</div>', unsafe_allow_html=True)
        d, e, f = st.columns(3)
        with d:
            requested_amount = st.number_input("Requested loan amount (₹)", min_value=10000, max_value=10000000, value=300000, step=25000)
        with e:
            tenure = st.selectbox("Requested tenure (months)", [12, 18, 24, 36, 48, 60, 72, 84], index=3)
        with f:
            residency = st.selectbox("Residency", ["Indian resident", "NRI", "Other / unsure"])
        submitted = st.form_submit_button("🔎 Check published criteria", type="primary", use_container_width=True)
    if submitted:
        profile = {
            "profile_id": "UI-001", "profile_name": "Applicant entered in UI", "age_years": age,
            "employment_type": "self_employed" if employment_label == "Self-employed" else "salaried",
            "monthly_net_income": monthly_income, "monthly_gross_income": None, "monthly_business_income": None,
            "existing_monthly_emi": existing_emi, "cibil_score": None if credit_unknown else cibil_score,
            "cibil_score_missing": bool(credit_unknown), "total_work_experience_months": work_months,
            "current_employer_months": job_months, "employer_category": employer_category,
            "profession": profession, "salary_account_lender": salary_account, "residency_status": residency,
            "city": city, "requested_loan_amount": requested_amount, "requested_tenure_months": tenure,
            "business_vintage_months": None, "annual_net_income": None, "net_take_home_after_emi": None,
        }
        result = evaluate_applicant(profile)
        st.session_state["loan_result"] = result
        st.session_state["loan_profile"] = profile
    result = st.session_state.get("loan_result")
    if result:
        if result.get("validation_errors"):
            st.error("Please correct these fields: " + "; ".join(result["validation_errors"]))
        else:
            rows = result["results"]
            failed = sum(r["status"] == "does_not_meet_published_criteria" for r in rows)
            uncertain = sum(r["status"] == "insufficient_information" for r in rows)
            st.markdown('<div class="section-title">3 · Screening results</div>', unsafe_allow_html=True)
            st.subheader("Overall screening decision: " + str(result.get("profile_decision", "unable_to_determine")).replace("_", " ").title())
            st.write(result.get("profile_decision_reason", "The public-rule dataset is incomplete; verify directly with lenders."))
            k1, k2, k3 = st.columns(3)
            with k1:
                st.metric("Lenders screened", len(rows))
            with k2:
                st.metric("Published criteria not met", failed)
            with k3:
                st.metric("Need more information", uncertain)
            rec = result.get("recommendation", {})
            if rec.get("lender_name"):
                st.success(f"Indicative comparison candidate: {rec['lender_name']} — {rec['reason']}")
            else:
                st.info("No defensible rate-based candidate found for this profile. " + str(rec.get("reason", "")))
            st.markdown('<div class="disclaimer">A “published criteria not met” result means at least one checked public rule failed. “Need more information” does not mean rejection. A clean result is not loan approval; lender underwriting and product-specific conditions still apply.</div>', unsafe_allow_html=True)
            st.write("")
            view = st.radio("Show", ["All lenders", "Potential matches", "Criteria not met", "Need more information", "Verification required"], horizontal=True, key="results_view")
            visible = rows
            if view == "Potential matches":
                visible = [r for r in rows if r["status"] == "potential_match"]
            elif view == "Criteria not met":
                visible = [r for r in rows if r["status"] == "does_not_meet_published_criteria"]
            elif view == "Need more information":
                visible = [r for r in rows if r["status"] == "insufficient_information"]
            elif view == "Verification required":
                visible = [r for r in rows if r["status"] == "verification_required"]
            # Source/evidence lookup keeps the UI transparent about where values came from.
            rules_df = pd.read_csv(ROOT / "data" / "lender_rules.csv").fillna("")
            display_rows = []
            for r in visible:
                start_rate = r["advertised_starting_rate_pct"]
                max_rate = r["advertised_max_rate_pct"]
                emi_low = estimate_emi(requested_amount, start_rate, tenure)
                emi_high = estimate_emi(requested_amount, max_rate, tenure)
                applicant_cap = r.get("indicative_applicant_max_loan_amount_inr")
                if applicant_cap is None or pd.isna(applicant_cap):
                    affordability_note = "Could not estimate affordability from available data"
                elif float(applicant_cap) <= 0:
                    affordability_note = "Estimated affordable amount is ₹0; do not treat as a loan recommendation"
                elif float(applicant_cap) < requested_amount:
                    affordability_note = "Requested amount exceeds the indicative applicant cap"
                else:
                    affordability_note = "Requested amount is within the indicative cap only; not approval"

                display_rows.append({
                    "Lender": r["lender_name"],
                    "Screening result": {
                        "potential_match": "Potential match on checked criteria — not approval",
                        "does_not_meet_published_criteria": "Published criterion not met",
                        "insufficient_information": "Insufficient information",
                        "verification_required": "Verification required",
                    }.get(r["status"], r["status"]),
                    "Affordability note": affordability_note,
                    "Starting rate (% p.a.)": start_rate if start_rate is not None else "Not recorded / verify",
                    "Published max rate (% p.a.)": max_rate if max_rate is not None else "Not recorded / verify",
                    "Indicative EMI at starting rate": format_inr(emi_low) if emi_low is not None else "Cannot estimate",
                    "Indicative EMI at max rate": format_inr(emi_high) if emi_high is not None else "Cannot estimate",
                    "Published product cap": format_inr(r["published_max_loan_amount_inr"]) if r["published_max_loan_amount_inr"] is not None else "Not recorded / verify",
                    "Indicative applicant max": format_inr(r.get("indicative_applicant_max_loan_amount_inr")) if r.get("indicative_applicant_max_loan_amount_inr") is not None else "Not enough data",
                    "Max tenure (months)": r["published_max_tenure_months"] if r["published_max_tenure_months"] is not None else "Not recorded / verify",
                })
            st.caption("Screening status and affordability are different: a lender can match some checked published criteria while the requested amount may exceed the model's indicative applicant cap. This is not approval.")
            st.caption(f"Indicative EMI estimates for {format_inr(requested_amount)} over {tenure} months, using advertised product rates where available. Actual offers, fees, insurance, APR and lender-specific pricing may differ.")
            st.info("‘Not recorded / verify’ means this project’s current research file does not contain a usable verified value. It does NOT mean the lender does not publish the information.")
            display_df = pd.DataFrame(display_rows).astype(str)
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            with st.expander("Audit trail: official source URLs and evidence status"):
                for r in visible:
                    subset = rules_df[rules_df["lender_name"].astype(str) == r["lender_name"]]
                    st.markdown(f"**{r['lender_name']}**")
                    if subset.empty:
                        st.caption("No rule rows found in the current research file.")
                    else:
                        cols = [c for c in ["rule_name", "rule_value", "unit", "evidence_status", "source_date", "source_url", "research_notes"] if c in subset.columns]
                        st.dataframe(subset[cols], use_container_width=True, hide_index=True)
            st.markdown('<div class="section-title">Why did each lender get this result?</div>', unsafe_allow_html=True)
            for r in visible:
                status_label = "Criteria not met" if r["status"] == "does_not_meet_published_criteria" else "Need more information"
                with st.expander(f"{r['lender_name']} · {status_label}"):
                    if r["failed_reasons"]:
                        st.markdown("**Checked criteria that were not met**")
                        for reason in r["failed_reasons"]: st.write("- " + reason)
                    if r["missing_information"]:
                        st.markdown("**Information missing for a reliable check**")
                        for reason in r["missing_information"]: st.write("- " + reason)
                    if r["conflicting_rules"]:
                        st.markdown("**Source conflicts requiring verification**")
                        st.write(", ".join(r["conflicting_rules"]))
                    if r["advisory_preferences"]:
                        st.markdown("**Advisory preferences (not automatic rejection rules)**")
                        for reason in r["advisory_preferences"]: st.write("- " + reason)
                    if r["notes"]:
                        st.markdown("**Research notes**")
                        for note in r["notes"][:4]: st.caption(note)
            export_df = pd.DataFrame(display_rows)
            st.download_button("⬇️ Download this comparison (CSV)", pd.DataFrame(display_rows).to_csv(index=False).encode("utf-8"), "loan_lender_comparison.csv", "text/csv")
elif page == "About this project":
    st.markdown("### About LoanLens")
    st.write("LoanLens is an educational, rule-based screening prototype that compares applicant information against a researched set of published personal-loan criteria for 20 Indian lenders.")
    st.write("It is not a trained machine-learning model, a credit bureau service, a financial adviser, or a lender's approval system. It deliberately surfaces missing information and conflicting sources instead of guessing.")
    st.markdown("### Method")
    st.markdown("1. Applicant enters basic profile and requested loan details.\n2. The Python rule engine checks applicable, verified hard rules.\n3. The app displays failed criteria, unknowns, conflicts and available public product terms.\n4. A rate-based candidate is shown only when the current rule engine can defensibly compare the published values.")
    st.markdown("### Data quality note")
    st.write("The research dataset contains rules that need further source rechecking. ‘Not recorded / verify’ means this dataset does not currently have a usable verified value; it does not claim that the lender does not publish it. A candidate is suppressed when the model detects missing information, failed checks, or unresolved source conflicts. Treat outputs as preliminary screening only and verify each lender's current product terms directly before using the results.")
st.divider()
st.caption("LoanLens • Personal Loan Eligibility Model • Research snapshot: 12 October 2026 • Never enter account numbers, PAN, Aadhaar, passwords or other sensitive identifiers.")
