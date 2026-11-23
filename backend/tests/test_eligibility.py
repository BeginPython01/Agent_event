"""Tests for src/eligibility.py: every status, plus the tricky edges."""

from datetime import date

from src.eligibility import check_eligibility
from src.models import Eligibility, Event, FieldConfidence, UserProfile

TODAY = date(2026, 11, 23)

# A first-year undergrad, born 2007, Thai, budget 500 baht.
STUDENT = UserProfile(birth_year=2007, level="undergraduate", major="Software Engineering",
                      nationality="ไทย", max_fee=500)


def make_event(confidence: float = 0.9, fee: float | None = None, start: date | None = date(2027, 2, 20), **conditions) -> Event:
    return Event(
        name="Test event",
        category="workshop",
        event_start=start,
        fee_amount=fee,
        fee_currency="THB" if fee is not None else None,
        eligibility=Eligibility(**conditions),
        confidence=FieldConfidence(registration_deadline=1.0, event_dates=1.0, eligibility=confidence),
    )


# --- eligible ----------------------------------------------------------------
def test_no_conditions_is_eligible():
    result = check_eligibility(make_event(), STUDENT, TODAY)
    assert result.status == "eligible"


def test_matching_level_and_nationality_is_eligible():
    event = make_event(allowed_levels=["undergraduate"], nationality=["Thai"], student_only=True)
    assert check_eligibility(event, STUDENT, TODAY).status == "eligible"


def test_fee_within_budget_is_eligible():
    assert check_eligibility(make_event(fee=300), STUDENT, TODAY).status == "eligible"


# --- not_eligible ------------------------------------------------------------
def test_wrong_level_is_not_eligible():
    # e.g. the MFU nursing course: for working nurses only
    event = make_event(allowed_levels=["working"], allowed_majors=["Nursing"])
    result = check_eligibility(event, STUDENT, TODAY)
    assert result.status == "not_eligible"
    assert any("คนทำงาน" in r for r in result.reasons)


def test_too_old_is_not_eligible():
    # born 2007 -> 19 or 20 in 2027; max 17 is clearly out
    event = make_event(age_max=17)
    assert check_eligibility(event, STUDENT, TODAY).status == "not_eligible"


def test_fee_over_budget_is_not_eligible():
    result = check_eligibility(make_event(fee=1500), STUDENT, TODAY)
    assert result.status == "not_eligible"
    assert any("เกินงบ" in r for r in result.reasons)


def test_other_nationality_is_not_eligible():
    event = make_event(nationality=["Singaporean"])
    assert check_eligibility(event, STUDENT, TODAY).status == "not_eligible"


# --- unsure ------------------------------------------------------------------
def test_age_on_the_boundary_is_unsure():
    # born 2007 -> 19 or 20 in 2027 depending on birthday; min 20 can't be decided
    event = make_event(age_min=20)
    assert check_eligibility(event, STUDENT, TODAY).status == "unsure"


def test_missing_profile_data_is_unsure():
    event = make_event(age_min=18)
    result = check_eligibility(event, UserProfile(), TODAY)
    assert result.status == "unsure"
    assert any("ปีเกิด" in r for r in result.reasons)


def test_major_name_mismatch_is_unsure_not_blocked():
    event = make_event(allowed_majors=["Computer Science"])
    assert check_eligibility(event, STUDENT, TODAY).status == "unsure"


def test_unknown_nationality_name_is_unsure():
    event = make_event(nationality=["ASEAN"])
    assert check_eligibility(event, STUDENT, TODAY).status == "unsure"


def test_low_confidence_blocker_becomes_unsure():
    # The rule says "no", but Claude wasn't confident it read the rule right.
    event = make_event(confidence=0.3, allowed_levels=["postgraduate"])
    result = check_eligibility(event, STUDENT, TODAY)
    assert result.status == "unsure"
    assert "AI ไม่มั่นใจ" in result.reasons[0]


def test_other_conditions_are_shown_as_a_note():
    event = make_event(other_conditions="ต้องมีพื้นฐาน Python")
    result = check_eligibility(event, STUDENT, TODAY)
    assert result.status == "eligible"
    assert any("Python" in r for r in result.reasons)
