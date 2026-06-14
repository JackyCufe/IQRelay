"""
schema_builder.py — Pipeline Schema assembly, validation, and arithmetic calculations

Principles:
- AI only does semantic judgment (fills atomic field values)
- This module assembles atomic fields into standard Schema JSON
- All enum validation, null protection, arithmetic here, not in prompts

Public interface:
  build_schema1(...)          → Schema 1 dict
  build_schema2(...)          → Schema 2 dict
  build_schema4_verdict(...) → "approved" | "blocked" (pure rules, replaces Agent 04 AI judgment)
  calc_satisfaction_rate(...) → float (replaces Agent 05 AI calculation)
  calc_health_score(...) → float (replaces Agent 06 AI calculation)
  validate_and_repair(...) → fill missing fields in any schema dict
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

# ─── Valid enum values ──────────────────────────────────────────

VERDICT_VALUES = {"approved", "rejected", "info_needed"}
STAGE1_STAGE_MAP = {
    "approved":   "gatekeeping_approved",
    "rejected":   "gatekeeping_rejected",
    "info_needed": "gatekeeping_pending",
}
REQUIREMENT_SOURCE_VALUES = {"Customer", "Presales", "Internal R&D", "Executive", "Partner", "Unknown"}
REQUIREMENT_TYPE_VALUES = {"customer_reported", "internal_improvement", "compliance", "competitive"}
IMPORTANCE_VALUES = {"P0", "P1", "P2"}
RELEASE_VERDICT_VALUES = {"approved", "blocked"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _coerce_str_or_null(val: Any) -> str | None:
    """Convert value to str, None/empty → None.
    Also treats literal model artifacts like "null"/"none"/"n/a" as None."""
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() in ("null", "none", "n/a", "na", "unspecified", "unknown"):
        return None
    return s


def _coerce_list_of_str(val: Any) -> list[str]:
    """Ensure returns list[str], compatible with None/str/list."""
    if val is None:
        return []
    if isinstance(val, str):
        return [val] if val.strip() else []
    if isinstance(val, list):
        return [str(v) for v in val if v is not None and str(v).strip()]
    return []


def _coerce_bool(val: Any, default: bool = False) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("true", "1", "yes")
    return default


# ─── Schema 1 ────────────────────────────────────────────

def build_schema1(
    *,
    verdict: str,
    customer_who: Any = None,
    usage_scenario: Any = None,
    problem: Any = None,
    expected_outcome: Any = None,
    reject_reason: Any = None,
    followup_questions: Any = None,
    requirement_source: Any = None,
    requirement_type: Any = None,
    source_traceable: Any = None,
    req_id: str,
    original_text: str,
    submitted_by: str = "Presales",
    submitted_at: str | None = None,
    rounds: int = 1,
    confirmed_by: Any = None,
    confirmed_at: Any = None,
) -> dict:
    """
    Assemble Schema 1 JSON.
    - verdict must be valid enum, forced to "info_needed" with warning if invalid
    - requirement_type must be valid enum, defaults to customer_reported
    - All nullable fields set to None (not empty string)
    - stage auto-mapped from verdict, not AI-controlled
    """
    # enum validation
    if verdict not in VERDICT_VALUES:
        print(f"[schema_builder] ⚠️ invalid verdict={verdict!r}，downgraded to info_needed")
        verdict = "info_needed"

    # requirement_source validation
    src = _coerce_str_or_null(requirement_source)
    if src not in REQUIREMENT_SOURCE_VALUES:
        src = "Unknown"

    # requirement_type validation
    rtype = _coerce_str_or_null(requirement_type)
    if rtype not in REQUIREMENT_TYPE_VALUES:
        rtype = "customer_reported"

    # followup_questions only meaningful for info_needed
    fqs = _coerce_list_of_str(followup_questions)
    if verdict != "info_needed":
        fqs = []

    # reject_reason only meaningful for rejected
    rr = _coerce_str_or_null(reject_reason) if verdict == "rejected" else None

    return {
        "schema_version": "1.0",
        "stage": STAGE1_STAGE_MAP[verdict],
        "requirement_id": req_id,
        "original_text": original_text,          # must NOT modify
        "submitted_by": submitted_by,
        "submitted_at": submitted_at or _now_iso(),
        "requirement_source": src,
        "requirement_type": rtype,
        "gatekeeping": {
            "verdict": verdict,
            "rounds": rounds,
            "customer_who": _coerce_str_or_null(customer_who),
            "usage_scenario": _coerce_str_or_null(usage_scenario),
            "problem": _coerce_str_or_null(problem),
            "expected_outcome": _coerce_str_or_null(expected_outcome),
            "source_traceable": _coerce_bool(source_traceable, default=(verdict == "approved")),
            "reject_reason": rr,
            "followup_questions": fqs,
        },
        "confirmed_by": _coerce_str_or_null(confirmed_by),
        "confirmed_at": _coerce_str_or_null(confirmed_at),
    }


# ─── Schema 2 ────────────────────────────────────────────

def _build_criterion(raw: dict) -> dict:
    """Normalize single acceptance criterion, unify field names, fill gaps."""
    return {
        "criterion_id":       _coerce_str_or_null(raw.get("criterion_id")) or "",
        "description":        _coerce_str_or_null(raw.get("description")) or "",
        "metric":             _coerce_str_or_null(raw.get("metric")) or "",
        "threshold":          _coerce_str_or_null(raw.get("threshold")) or "",
        "measurement_method": _coerce_str_or_null(raw.get("measurement_method")) or "",
        "pm_original":        _coerce_str_or_null(raw.get("pm_original")) or "",
    }


def _build_test_case(raw: dict) -> dict:
    """
    Normalize single test case.
    - actual_result/verdict forced null (human fills, AI must not pre-fill)
    - Unify field name: expected_result (compatible with expected_output)
    """
    steps = raw.get("steps", [])
    if isinstance(steps, str):
        steps = [s.strip() for s in steps.split("\n") if s.strip()]

    expected = (
        _coerce_str_or_null(raw.get("expected_result"))
        or _coerce_str_or_null(raw.get("expected_output"))  # compatible with old field name
        or ""
    )
    return {
        "case_id":          _coerce_str_or_null(raw.get("case_id")) or "",
        "criterion_id":     _coerce_str_or_null(raw.get("criterion_id") or raw.get("linked_criterion")) or "",
        "actor":            _coerce_str_or_null(raw.get("actor")) or "",
        "precondition":     _coerce_str_or_null(raw.get("precondition")) or "",
        "steps":            [str(s) for s in steps],
        "expected_result":  expected,
        "actual_result":    None,   # forced null, human fills
        "verdict":          None,   # forced null, human fills
    }


def build_schema2(
    *,
    requirement_id: str,
    four_q: dict,
    pm_core_value: str = "",
    pm_feature_def: str = "",
    pm_priority: str = "",
    pm_acceptance_criteria_raw: str = "",
    structured_criteria: list[dict],
    test_cases: list[dict],
    pm_confirmed_by: Any = None,
    pm_confirmed_at: Any = None,
) -> dict:
    """Assemble Schema 2 JSON. actual_result/verdict forced null."""
    return {
        "schema_version": "2.0",
        "stage": "value_defined",
        "requirement_id": requirement_id,
        "four_q": four_q,                           # pass-through, do not modify
        "pm_core_value": pm_core_value,
        "pm_feature_def": pm_feature_def,
        "pm_priority": pm_priority,
        "pm_acceptance_criteria_raw": pm_acceptance_criteria_raw,
        "structured_criteria": [_build_criterion(c) for c in structured_criteria],
        "test_cases": [_build_test_case(tc) for tc in test_cases],
        "_pending_pm_confirmation": pm_confirmed_by is None,
        "pm_confirmed_by": _coerce_str_or_null(pm_confirmed_by),
        "pm_confirmed_at": _coerce_str_or_null(pm_confirmed_at),
    }


# ─── Schema 4 verdict (pure rules, no AI)────────────────────

def build_schema4_verdict(requirements_list: list[dict]) -> str:
    """
    Mechanical release verdict per rubric rules:
      - Any P0 requirement acceptance_verdict = "fail" → "blocked"
      - Otherwise → "approved"

    This is deterministic logic, not AI judgment.

    requirements_list Each format:
      {"requirement_id": ..., "importance": "P0|P1|P2", "acceptance_verdict": "pass|fail|blocked_by_env"}
    """
    for req in requirements_list:
        importance = (req.get("importance") or "").upper()
        av = (req.get("acceptance_verdict") or "").lower()
        if importance == "P0" and av == "fail":
            print(f"[schema_builder] Release blocked: P0 requirement {req.get('requirement_id')} acceptance_verdict=fail")
            return "blocked"
    return "approved"


def build_bypass_log(requirements_list: list[dict]) -> list[dict]:
    """
    Generate bypass_log: write P1 fails here.
    P2 fail only logs warning, not in bypass_log.
    """
    bypass = []
    for req in requirements_list:
        importance = (req.get("importance") or "").upper()
        av = (req.get("acceptance_verdict") or "").lower()
        if importance == "P1" and av == "fail":
            bypass.append({
                "requirement_id": req.get("requirement_id"),
                "importance": "P1",
                "fail_reason": req.get("block_reason") or "P1 requirement tests failed",
                "bypass_approved_by": None,
            })
    return bypass


# ─── Pure arithmetic: replaces Agent 05/06 calculations ─────────────────────

def calc_satisfaction_rate(satisfied_count: int, unsatisfied_count: int) -> float:
    """
    Satisfaction rate = satisfied / (satisfied + unsatisfied)
    No AI calculation — avoids precision issues and hallucination.
    """
    total = satisfied_count + unsatisfied_count
    if total <= 0:
        return 0.0
    return round(satisfied_count / total, 4)


def calc_health_score(improvement_actions_count: int) -> float:
    """
    Process health = 1.0 - 0.1 per improvement_action, min 0.0
    Rule from 06-retrospective.md, moved to script, no AI calculation.
    """
    return max(0.0, round(1.0 - improvement_actions_count * 0.1, 1))


# ─── Generic Schema repair (safety net)────────────────────────────────

_REQUIRED_FIELDS: dict[str, list[str]] = {
    "1.0_s1": ["schema_version", "stage", "requirement_id", "original_text", "gatekeeping"],
    "2.0_s2": ["schema_version", "stage", "requirement_id", "four_q", "structured_criteria", "test_cases"],
}


def validate_and_repair(schema: dict) -> dict:
    """
    Final safety net for agent-returned schema dict:
    - Fill missing fields with null, no exceptions (pipeline never crashes on partial schema)
    - Return repaired dict (does not modify original)
    """
    import copy
    repaired = copy.deepcopy(schema)
    version = repaired.get("schema_version", "")
    stage = repaired.get("stage", "")

    # determine which schema
    key = None
    if version == "1.0" and "gatekeeping" in stage:
        key = "1.0_s1"
    elif version == "2.0":
        key = "2.0_s2"

    if key and key in _REQUIRED_FIELDS:
        for field in _REQUIRED_FIELDS[key]:
            if field not in repaired:
                print(f"[schema_builder] ⚠️ repaired missing field: {field}")
                repaired[field] = None

    # Schema 1 specific repair
    if key == "1.0_s1" and isinstance(repaired.get("gatekeeping"), dict):
        gk = repaired["gatekeeping"]
        for f in ["verdict", "rounds", "customer_who", "usage_scenario",
                  "problem", "expected_outcome", "source_traceable",
                  "reject_reason", "followup_questions"]:
            if f not in gk:
                gk[f] = [] if f == "followup_questions" else None

    return repaired
