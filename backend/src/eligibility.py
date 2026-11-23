"""Can this user join this event? Plain code, no LLM.

Why no LLM here: the rules are simple comparisons (age, level, fee...), code
is free, fast, and gives the same answer every time, so it's easy to test.

The golden rule from the brief: when we're not sure, answer "unsure" and
explain why. Never hide an event on weak evidence.
"""

from datetime import date

from src.models import EligibilityResult, Event, UserProfile

# Below this, Claude itself wasn't sure it read the conditions right.
MIN_CONFIDENCE = 0.5

# Very small alias table so "ไทย", "Thai" and "Thailand" all mean the same.
# Anything not in here can't be compared safely, so it becomes "unsure".
NATIONALITY_ALIASES = {
    "thai": "TH", "thailand": "TH", "ไทย": "TH", "สัญชาติไทย": "TH",
    "singapore": "SG", "singaporean": "SG", "สิงคโปร์": "SG",
    "malaysia": "MY", "malaysian": "MY", "มาเลเซีย": "MY",
    "lao": "LA", "laos": "LA", "ลาว": "LA",
    "myanmar": "MM", "burmese": "MM", "เมียนมา": "MM",
    "china": "CN", "chinese": "CN", "จีน": "CN",
}

LEVEL_NAMES_TH = {
    "high_school": "ม.ปลาย",
    "vocational": "ปวช./ปวส.",
    "undergraduate": "ป.ตรี",
    "postgraduate": "ป.โท/เอก",
    "working": "คนทำงาน",
    "other": "อื่น ๆ",
}


def _nationality_code(text: str) -> str | None:
    return NATIONALITY_ALIASES.get(text.strip().lower())


def check_eligibility(event: Event, user: UserProfile, today: date | None = None) -> EligibilityResult:
    """Compare the event's conditions with the user's profile.

    Each check adds to one of two lists:
    - blockers: a clear reason the user can't join
    - doubts:   we couldn't tell (missing data, names that don't match exactly)
    Then: any blocker -> not_eligible, else any doubt -> unsure, else eligible.
    """
    today = today or date.today()
    el = event.eligibility
    blockers: list[str] = []
    doubts: list[str] = []

    # --- Age -----------------------------------------------------------------
    # We only know the birth YEAR, so the real age is one of two numbers
    # (before or after this year's birthday). If the limit falls between
    # them, we honestly can't tell.
    if el.age_min is not None or el.age_max is not None:
        if user.birth_year is None:
            doubts.append("มีเงื่อนไขอายุ แต่โปรไฟล์ยังไม่มีปีเกิด")
        else:
            year = (event.event_start or today).year
            age_high = year - user.birth_year
            age_low = age_high - 1
            if el.age_min is not None:
                if age_high < el.age_min:
                    blockers.append(f"ต้องอายุอย่างน้อย {el.age_min} ปี")
                elif age_low < el.age_min:
                    doubts.append(f"อายุใกล้เกณฑ์ขั้นต่ำ {el.age_min} ปี ขึ้นกับวันเกิด")
            if el.age_max is not None:
                if age_low > el.age_max:
                    blockers.append(f"ต้องอายุไม่เกิน {el.age_max} ปี")
                elif age_high > el.age_max:
                    doubts.append(f"อายุใกล้เกณฑ์สูงสุด {el.age_max} ปี ขึ้นกับวันเกิด")

    # --- Birth year range ----------------------------------------------------
    if el.birth_year_min is not None or el.birth_year_max is not None:
        if user.birth_year is None:
            doubts.append("มีเงื่อนไขปีเกิด แต่โปรไฟล์ยังไม่มีปีเกิด")
        else:
            if el.birth_year_min is not None and user.birth_year < el.birth_year_min:
                blockers.append(f"ต้องเกิดตั้งแต่ปี {el.birth_year_min}")
            if el.birth_year_max is not None and user.birth_year > el.birth_year_max:
                blockers.append(f"ต้องเกิดไม่เกินปี {el.birth_year_max}")

    # --- Students only -------------------------------------------------------
    if el.student_only:
        if user.level is None:
            doubts.append("รับเฉพาะนักเรียน/นักศึกษา แต่โปรไฟล์ยังไม่มีระดับการศึกษา")
        elif user.level == "working":
            blockers.append("รับเฉพาะนักเรียน/นักศึกษา")

    # --- Education level -----------------------------------------------------
    if el.allowed_levels:
        allowed = "/".join(LEVEL_NAMES_TH.get(level, level) for level in el.allowed_levels)
        if user.level is None:
            doubts.append(f"รับเฉพาะ {allowed} แต่โปรไฟล์ยังไม่มีระดับการศึกษา")
        elif user.level not in el.allowed_levels:
            blockers.append(f"รับเฉพาะ {allowed}")

    # --- Major ---------------------------------------------------------------
    # Major names vary a lot ("CS" vs "Computer Science" vs "วิทยาการคอมพิวเตอร์"),
    # so a non-match is only a doubt, never a blocker.
    if el.allowed_majors:
        majors = ", ".join(el.allowed_majors)
        if user.major is None:
            doubts.append(f"รับเฉพาะสาขา {majors} แต่โปรไฟล์ยังไม่มีสาขา")
        else:
            mine = user.major.lower()
            if not any(m.lower() in mine or mine in m.lower() for m in el.allowed_majors):
                doubts.append(f"รับเฉพาะสาขา {majors} ลองเช็กว่าสาขาของคุณนับไหม")

    # --- Nationality ---------------------------------------------------------
    if el.nationality:
        allowed_codes = [_nationality_code(n) for n in el.nationality]
        my_code = _nationality_code(user.nationality) if user.nationality else None
        listed = ", ".join(el.nationality)
        if user.nationality is None:
            doubts.append(f"รับเฉพาะสัญชาติ {listed} แต่โปรไฟล์ยังไม่มีสัญชาติ")
        elif my_code and my_code in allowed_codes:
            pass  # match
        elif my_code and all(allowed_codes):
            # Every name on the list is one we recognise, and none is ours.
            blockers.append(f"รับเฉพาะสัญชาติ {listed}")
        else:
            doubts.append(f"รับเฉพาะสัญชาติ {listed} เทียบกับโปรไฟล์ไม่ได้แน่ชัด")

    # --- Fee vs budget -------------------------------------------------------
    if user.max_fee is not None and event.fee_amount is not None:
        if event.fee_amount > user.max_fee:
            blockers.append(f"ค่าสมัคร {event.fee_amount:g} {event.fee_currency or ''} เกินงบ {user.max_fee:g}".strip())

    # --- Free-text conditions: show them, don't judge them -------------------
    notes: list[str] = []
    if el.other_conditions:
        notes.append(f"เงื่อนไขอื่น: {el.other_conditions}")

    # --- Decide --------------------------------------------------------------
    low_confidence = event.confidence.eligibility < MIN_CONFIDENCE
    if blockers and not low_confidence:
        return EligibilityResult(status="not_eligible", reasons=blockers + notes)
    if blockers and low_confidence:
        # Clear rule, but Claude wasn't sure it read it right: let the user check.
        reason = "AI ไม่มั่นใจว่าอ่านเงื่อนไขถูก ลองเช็กต้นฉบับ"
        return EligibilityResult(status="unsure", reasons=[reason] + blockers + notes)
    if doubts:
        return EligibilityResult(status="unsure", reasons=doubts + notes)
    if low_confidence:
        return EligibilityResult(status="unsure", reasons=["AI ไม่มั่นใจว่าอ่านเงื่อนไขครบ ลองเช็กต้นฉบับ"] + notes)
    reasons = ["ตรงตามเงื่อนไขที่ประกาศไว้"] if _has_any_condition(event) else ["ประกาศไม่ได้ระบุเงื่อนไขผู้สมัคร"]
    return EligibilityResult(status="eligible", reasons=reasons + notes)


def _has_any_condition(event: Event) -> bool:
    el = event.eligibility
    return any([
        el.age_min, el.age_max, el.birth_year_min, el.birth_year_max, el.student_only,
        el.allowed_levels, el.allowed_majors, el.nationality,
    ])
