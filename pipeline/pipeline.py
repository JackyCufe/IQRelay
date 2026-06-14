"""
pipeline.py — 6-Agent Pipeline Orchestrator
Stages: Gatekeeping → Value Transform → Scenario Test → Release Review
         → Feedback Analysis → Process Analysis
Integrates Azure AI Search (Foundry IQ) knowledge base.
"""
from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from pipeline.agent_runner import (
    run_agent,
    extract_gatekeeping_result,
    extract_value_transform_result,
    extract_json_from_response,
)
from pipeline.schema_builder import (
    build_schema1,
    build_schema2,
    build_schema4_verdict,
    calc_satisfaction_rate,
    calc_health_score,
    validate_and_repair,
)
from pipeline.foundry_iq import search_similar, write_lesson, archive_to_iq, seed_demo_data
from config.config import DEMO_MODE


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _gen_id(prefix: str = "req") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# ─── Pipeline State ────────────────────────────────────

class PipelineState:
    """Tracks the complete state of a single requirement through the pipeline."""
    def __init__(self, original_text: str, submitted_by: str = "user"):
        self.requirement_id = _gen_id()
        self.original_text = original_text
        # accumulated_input keeps the full multi-round context for Stage 1.
        # original_text stays immutable (schema contract); supplements are appended here.
        self.accumulated_input = original_text
        self.gatekeeping_rounds = 0  # incremented each time Stage 1 runs
        self.submitted_by = submitted_by
        self.submitted_at = _now()
        self.requirement_title = ""  # AI generated after Stage 1
        self.schemas: dict[int, dict] = {}
        self.foundry_iq_results: list[dict] = []
        self.log: list[str] = []
        self.stage_timestamps: dict[int, dict] = {}

    def _stage_start(self, stage: int) -> None:
        self.stage_timestamps.setdefault(stage, {})["started_at"] = _now()

    def _stage_end(self, stage: int) -> None:
        now = _now()
        ts = self.stage_timestamps.setdefault(stage, {})
        ts["completed_at"] = now
        if "started_at" in ts:
            start = datetime.fromisoformat(ts["started_at"])
            end = datetime.fromisoformat(now)
            seconds = (end - start).total_seconds()
            ts["duration_seconds"] = seconds
            ts["duration_minutes"] = round(seconds / 60, 1)

    def log_event(self, msg: str) -> None:
        self.log.append(f"[{_now()}] {msg}")
        print(f"  [pipeline] {msg}")

    def archive(self, entry_type: str, stage: int, content: dict,
                author: str = "system", tags: list[str] | None = None,
                status: str = "active", revision: int = 1,
                retraction: dict[str, Any] | None = None) -> str:
        """Write pipeline artifact to Foundry IQ."""
        return archive_to_iq(
            entry_type=entry_type,
            requirement_id=self.requirement_id,
            requirement_title=self.requirement_title or self.original_text[:80],
            stage=stage, author=author, content=content,
            tags=tags, revision=revision, status=status,
            retraction=retraction,
        )


# ─── Tools for Agents ──────────────────────────────────

def _tool_search_similar(args: dict) -> dict:
    """Agent tool: search Foundry IQ for similar historical requirements."""
    query = args.get("query", "")
    top = args.get("top", 5)
    filter_expr = args.get("filter")
    results = search_similar(query, top, filter_expr)
    # Flatten new unified schema for agent compatibility
    flat = []
    for r in results:
        content = r.get("content") or {}
        flat.append({
            "id": r.get("id", ""),
            "requirement": r.get("requirement_title") or content.get("requirement", ""),
            "type": content.get("type", "unknown"),
            "problem": content.get("problem", ""),
            "resolution": content.get("resolution", ""),
            "pitfalls": content.get("pitfalls", []),
            "push_back_reason": content.get("reason", ""),
            "stage": f"Stage {r.get('stage', '?')}",
            "entry_type": r.get("entry_type", ""),
        })
    return {"results": flat, "count": len(flat)}


def _tool_submit_gatekeeping(args: dict) -> dict:
    """Agent tool: submit gatekeeping result (recorded by Pipeline)."""
    return {"status": "received", "message": "Gatekeeping result submitted to pipeline"}


_PIPELINE_TOOLS = [
    {
        "name": "submit_gatekeeping_result",
        "description": "Submit gatekeeping verdict with extracted fields. Params: verdict (approved|rejected|info_needed), requirement_type, source_traceable (bool), customer_who, usage_scenario, problem, expected_outcome, followup_questions, reject_reason, requirement_source",
        "parameters": {
            "type": "object",
            "properties": {
                "verdict": {"type": "string", "enum": ["approved", "rejected", "info_needed"]},
                "requirement_type": {"type": "string"},
                "source_traceable": {"type": "boolean"},
                "customer_who": {"type": ["string", "null"]},
                "usage_scenario": {"type": ["string", "null"]},
                "problem": {"type": ["string", "null"]},
                "expected_outcome": {"type": ["string", "null"]},
                "followup_questions": {"type": "array", "items": {"type": "string"}},
                "reject_reason": {"type": ["string", "null"]},
                "requirement_source": {"type": "string"},
            },
            "required": ["verdict"],
        },
    },
    {
        "name": "search_similar_requirements",
        "description": "Search Foundry IQ knowledge base for similar historical requirements, returning past pitfalls and solutions",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keywords"},
                "top": {"type": "integer", "description": "Number of results to return"},
                "filter": {"type": "string", "description": "OData filter expression"},
            },
            "required": ["query"],
        },
    },
]

_TOOL_HANDLERS = {
    "submit_gatekeeping_result": _tool_submit_gatekeeping,
    "search_similar_requirements": _tool_search_similar,
}


# ─── AI Title Generation ──────────────────────────────

def _generate_title(state: PipelineState) -> str:
    """Generate an 8-10 word descriptive English title from the gatekeeping result."""
    s1 = state.schemas[1].get("gatekeeping", {})
    prompt_data = {
        "who": s1.get("customer_who") or "Internal",
        "scenario": s1.get("usage_scenario") or "unspecified",
        "problem": s1.get("problem") or state.original_text[:100],
        "expected": s1.get("expected_outcome") or "unspecified",
    }
    try:
        result = run_agent(
            agent_file="02-value-transform.md",
            user_message=(
                "You are a title generator ONLY. Do NOT act as Value Transform agent. "
                "Generate an 8-10 word English descriptive title for this requirement. "
                "Format: who + what + how. Be specific, use precise nouns, no abbreviations.\n\n"
                f"Data: {json.dumps(prompt_data, ensure_ascii=False)}"
            ),
            extra_context={},
        )
        title = result["text"].strip().strip('"').strip("'")
        # Fallback: use first 80 chars of original text
        if not title or len(title) < 5:
            return state.original_text[:80]
        return title
    except Exception:
        return state.original_text[:80]


# ─── Pipeline Stages ───────────────────────────────────

def run_stage1_gatekeeper(state: PipelineState) -> dict:
    """Stage 1: Gatekeeper — extract four questions, block pseudo-requirements.

    Multi-round safe: uses accumulated_input (all rounds joined) so supplements
    add to — never overwrite — earlier information. Previously extracted fields
    are carried forward when the current round returns null for them.
    """
    state._stage_start(1)
    state.gatekeeping_rounds += 1
    state.log_event(f"Stage 1: Gatekeeper started (round {state.gatekeeping_rounds})")

    # Full multi-round context (not just the latest message)
    full_input = state.accumulated_input or state.original_text

    # Search Foundry IQ for similar historical requirements
    results = search_similar(full_input, top=3)
    # Flatten new unified schema for agent compatibility
    state.foundry_iq_results = []
    for r in results:
        c = r.get("content") or {}
        state.foundry_iq_results.append({
            "id": r.get("id", ""),
            "requirement": r.get("requirement_title") or c.get("requirement", ""),
            "type": c.get("type", "unknown"),
            "problem": c.get("problem", ""),
            "resolution": c.get("resolution", ""),
            "pitfalls": c.get("pitfalls", []),
            "push_back_reason": c.get("reason", ""),
            "stage_label": f"Stage {r.get('stage', '?')}",
            "entry_type": r.get("entry_type", ""),
        })

    # Carry forward fields already extracted in previous rounds (if any)
    prev_gk = state.schemas.get(1, {}).get("gatekeeping", {})

    context = {
        "requirement_id": state.requirement_id,
        "foundry_iq_similar": state.foundry_iq_results,
        "max_rounds": 3,
        "current_round": state.gatekeeping_rounds,
        "previously_extracted": {
            "customer_who": prev_gk.get("customer_who"),
            "usage_scenario": prev_gk.get("usage_scenario"),
            "problem": prev_gk.get("problem"),
            "expected_outcome": prev_gk.get("expected_outcome"),
        },
    }

    result = run_agent(
        agent_file="01-gatekeeper.md",
        user_message=full_input,
        extra_context=context,
        tools=_PIPELINE_TOOLS,
        tool_handlers=_TOOL_HANDLERS,
    )

    gate_result = extract_gatekeeping_result(result["tool_calls"]) or {}

    # Some models emit the literal string "null"/"none"/"n/a" instead of real null.
    def _clean(v):
        if v is None:
            return None
        s = str(v).strip()
        if s.lower() in ("null", "none", "n/a", "na", "unspecified", "unknown", ""):
            return None
        return s

    # ─── Field-level merge: carry forward prior values when this round is null ───
    def _merge(field: str):
        cur = _clean(gate_result.get(field))
        if cur is None:
            return _clean(prev_gk.get(field))
        return cur

    merged_who = _merge("customer_who")
    merged_scenario = _merge("usage_scenario")
    merged_problem = _merge("problem")
    merged_expected = _merge("expected_outcome")

    # ─── Verdict is decided MECHANICALLY from merged fields, NOT by the model ───
    # (The model often mis-judges "rejected"/"approved" or contradicts itself
    #  across rounds; the pipeline owns the final verdict.)
    req_type = gate_result.get("requirement_type") or prev_gk.get("requirement_type")
    required = [merged_scenario, merged_problem, merged_expected]
    if req_type == "customer_reported" or req_type is None:
        required.append(merged_who)
    filled = [f for f in required if f]

    if len(filled) == 0:
        verdict = "rejected"            # nothing extractable at all
    elif all(required):
        verdict = "approved"            # every required field present
    else:
        verdict = "info_needed"         # some still missing → keep asking

    schema1 = build_schema1(
        verdict=verdict,
        customer_who=merged_who,
        usage_scenario=merged_scenario,
        problem=merged_problem,
        expected_outcome=merged_expected,
        reject_reason=gate_result.get("reject_reason"),
        followup_questions=gate_result.get("followup_questions"),
        requirement_source=gate_result.get("requirement_source") or prev_gk.get("requirement_source"),
        requirement_type=req_type,
        source_traceable=gate_result.get("source_traceable"),
        req_id=state.requirement_id,
        original_text=state.original_text,
        submitted_by=state.submitted_by,
        submitted_at=state.submitted_at,
        rounds=state.gatekeeping_rounds,
    )

    state.schemas[1] = schema1
    state.log_event(f"Stage 1 complete: verdict={schema1['gatekeeping']['verdict']}")
    state._stage_end(1)
    state.archive("stage_output", stage=1, content=schema1,
                  author=schema1["gatekeeping"].get("customer_who") or state.submitted_by,
                  tags=[schema1["gatekeeping"].get("requirement_type", "")])

    # ─── Generate AI title ─────────────────────────
    if schema1["gatekeeping"]["verdict"] in ("approved", "info_needed"):
        state.requirement_title = _generate_title(state)
        state.log_event(f"AI title: {state.requirement_title}")
    else:
        state.requirement_title = state.requirement_id

    return schema1


def run_stage2_value_transform(state: PipelineState) -> dict | None:
    """Stage 2: Value Transform — structure acceptance criteria."""
    if state.schemas[1]["gatekeeping"]["verdict"] != "approved":
        state.log_event("Stage 2: skipped (Stage 1 did not pass)")
        return None

    state._stage_start(2)
    state.log_event("Stage 2: Value Transform started")

    four_q = {
        "who": state.schemas[1]["gatekeeping"].get("customer_who"),
        "scene": state.schemas[1]["gatekeeping"].get("usage_scenario"),
        "problem": state.schemas[1]["gatekeeping"].get("problem"),
        "expected": state.schemas[1]["gatekeeping"].get("expected_outcome"),
    }

    context = {
        "requirement_id": state.requirement_id,
        "four_q": four_q,
    }

    # Demo mode: mock PM confirmation
    if DEMO_MODE:
        context["pm_core_value"] = "Core value: reduce post-sales support cost, enable self-service configuration"
        context["pm_feature_def"] = "One-sentence config: agency operators complete homepage setup via natural language commands"
        context["pm_priority"] = "P0"
        context["pm_acceptance_criteria_raw"] = (
            "1. Agency operators configure homepage via natural language\n"
            "2. Configuration takes no more than 3 steps\n"
            "3. Configuration success rate >= 95%"
        )

    result = run_agent(
        agent_file="02-value-transform.md",
        user_message=json.dumps(context, ensure_ascii=False),
        extra_context=context,
    )

    schema2_raw = extract_value_transform_result(result["text"])
    if schema2_raw:
        schema2 = build_schema2(
            requirement_id=state.requirement_id,
            four_q=four_q,
            pm_core_value=context.get("pm_core_value", ""),
            pm_feature_def=context.get("pm_feature_def", ""),
            pm_priority=context.get("pm_priority", ""),
            pm_acceptance_criteria_raw=context.get("pm_acceptance_criteria_raw", ""),
            structured_criteria=schema2_raw.get("structured_criteria", []),
            test_cases=schema2_raw.get("test_cases", []),
        )
        state.schemas[2] = schema2
        state.log_event("Stage 2 completed")
        state._stage_end(2)
        state.archive("stage_output", stage=2, content=schema2, author="pm_agent",
                      tags=[schema2.get("pm_priority", "")])
        return schema2

    state.log_event("Stage 2: failed to extract valid Schema")
    return None


def run_stage3_scenario_test(state: PipelineState) -> dict | None:
    """Stage 3: Scenario Test — generate customer-perspective test cases."""
    if 2 not in state.schemas:
        state.log_event("Stage 3: skipped (no Schema 2)")
        return None

    state._stage_start(3)
    state.log_event("Stage 3: Scenario Test started")

    context = state.schemas[2]

    result = run_agent(
        agent_file="03-scenario-test.md",
        user_message=json.dumps(context, ensure_ascii=False),
        extra_context=context,
    )

    schema3 = extract_json_from_response(result["text"]) or {}
    schema3 = validate_and_repair(schema3)
    schema3["requirement_id"] = state.requirement_id
    schema3["stage"] = "testing_complete"

    state.schemas[3] = schema3
    state.log_event("Stage 3 completed")
    state._stage_end(3)
    state.archive("stage_output", stage=3, content=schema3, author="rd_agent",
                  tags=["scenario_test"])
    return schema3


def run_stage4_release_review(state: PipelineState) -> dict | None:
    """Stage 4: Release Review — rule-based release decision."""
    if 3 not in state.schemas:
        state.log_event("Stage 4: skipped (no Schema 3)")
        return None

    state._stage_start(4)
    state.log_event("Stage 4: Release Review started")

    context = state.schemas[3]

    result = run_agent(
        agent_file="04-release-review.md",
        user_message=json.dumps(context, ensure_ascii=False),
        extra_context=context,
    )

    schema4 = extract_json_from_response(result["text"]) or {}

    # Mechanical release_verdict (no AI judgment)
    requirements_list = schema4.get("requirements", [])
    verdict = build_schema4_verdict(requirements_list)

    schema4 = validate_and_repair(schema4)
    schema4["release_verdict"] = verdict
    schema4["requirement_id"] = state.requirement_id

    # If blocked, do NOT write here (Stage6 is sole writer)

    state.schemas[4] = schema4
    state.log_event(f"Stage 4 completed: verdict={verdict}")
    state._stage_end(4)
    state.archive("stage_output", stage=4, content=schema4, author="release_agent",
                  tags=[verdict])
    return schema4


def run_stage5_feedback_collect(state: PipelineState) -> dict | None:
    """Stage 5: Customer Feedback Analysis — AI analyzes feedback data."""
    if 4 not in state.schemas or state.schemas[4].get("release_verdict") != "approved":
        state.log_event("Stage 5: skipped (not released)")
        return None

    state._stage_start(5)
    state.log_event("Stage 5: Feedback Analysis started")

    # Build context from real pipeline data (not hardcoded mock)
    schema2 = state.schemas.get(2, {})
    schema4 = state.schemas[4]
    criteria = schema2.get("structured_criteria", [])
    test_cases = schema2.get("test_cases", [])

    context = {
        "version": schema4.get("version", "demo"),
        "core_value_statement": schema4.get("core_value_statement", ""),
        "pm_priority": schema2.get("pm_priority", ""),
        "release_value": schema4.get("release_value", ""),
        # Structured criteria from Stage 2 (real pipeline output)
        "acceptance_criteria": [
            {
                "criterion_id": c.get("criterion_id", f"AC-{i+1}"),
                "description": c.get("description", ""),
                "threshold": c.get("threshold", ""),
                "measurement_method": c.get("measurement_method", ""),
            }
            for i, c in enumerate(criteria)
        ] if criteria else [
            {"criterion_id": f"AC-{i+1}", "description": tc.get("expected_result", "")[:100],
             "threshold": "N/A", "measurement_method": "N/A"}
            for i, tc in enumerate(test_cases[:3])
        ],
        # RD self-test results from Stage 3
        "rd_test_results": state.stage3_rd_data if hasattr(state, 'stage3_rd_data') else {},
        # Any human feedback from rejections (self-improvement loop)
        "human_feedback": state.stage_feedback if hasattr(state, 'stage_feedback') else {},
        # Raw feedback data from Stage 5b (CSV or text input)
        "raw_feedback": state.stage5_raw_feedback if hasattr(state, 'stage5_raw_feedback') else "",
        # Survey questions from Stage 5a
        "survey_questions": state.stage5_survey.get("questions", "") if hasattr(state, 'stage5_survey') else "",
    }

    result = run_agent(
        agent_file="05-feedback-collect.md",
        user_message=json.dumps(context, ensure_ascii=False),
        extra_context=context,
    )

    schema5 = extract_json_from_response(result["text"]) or {}
    schema5 = validate_and_repair(schema5)
    schema5["requirement_id"] = state.requirement_id
    schema5["stage"] = "feedback_analyzed"

    state.schemas[5] = schema5
    state.log_event(
        f"Stage 5 completed: {len(schema5.get('complaint_clusters', []))} complaint clusters found"
    )
    state._stage_end(5)
    state.archive("stage_output", stage=5, content=schema5, author="feedback_agent",
                  tags=["customer_feedback"])
    return schema5


def run_stage6_retrospective(state: PipelineState) -> dict | None:
    """Stage 6: Process Analysis — inward-facing, analyzes team collaboration.
    This is the ONLY stage that writes knowledge entries to Foundry IQ.
    """
    state._stage_start(6)
    state.log_event("Stage 6: Process Analysis started")

    # Search for all rejection/feedback records for this requirement (self-improvement loop input)
    rej_records = search_similar(
        state.requirement_title or state.original_text[:100],
        top=10,
        filter_expr=f"requirement_id eq '{state.requirement_id}'",
    )
    rework_summary = {
        "total_rejections": 0, "rejection_stages": [], "reasons": [],
    }
    for r in rej_records:
        if r.get("entry_type") == "rejection_feedback" or "rejection" in str(r.get("tags", [])):
            rework_summary["total_rejections"] += 1
            rework_summary["rejection_stages"].append(f"Stage {r.get('stage','?')}")
            reason = (r.get("content") or {}).get("reason", "")
            if reason:
                rework_summary["reasons"].append(reason)

    context = {
        "schemas": {k: v for k, v in state.schemas.items()},
        "foundry_iq_results": state.foundry_iq_results,
        "feedback_analysis": state.schemas.get(5, {}),
        "human_feedback": state.stage_feedback if hasattr(state, 'stage_feedback') else {},
        "rework_analysis": rework_summary,
        "stage_timestamps": state.stage_timestamps,
    }

    result = run_agent(
        agent_file="06-retrospective.md",
        user_message=json.dumps(context, ensure_ascii=False),
        extra_context=context,
    )

    schema6 = extract_json_from_response(result["text"]) or {}
    schema6 = validate_and_repair(schema6)
    schema6["requirement_id"] = state.requirement_id
    schema6["stage"] = "process_analyzed"

    # Write knowledge entries to Foundry IQ (sole writer)
    knowledge_entries = schema6.get("knowledge_entries_written", [])
    for entry in knowledge_entries:
        write_lesson({
            "id": f"{state.requirement_id}-{entry.get('id', 'ke')}",
            "requirement": state.requirement_title or state.original_text,
            "type": state.schemas[1].get("requirement_type", "unknown"),
            "problem": entry.get("description", ""),
            "resolution": schema6.get("roi_verdict", {}).get("summary", ""),
            "pitfalls": [entry.get("description", "")],
            "stage": "process_analysis",
            "category": entry.get("category", "process_lesson"),
        })

    state.log_event(
        f"Stage 6 completed: {len(knowledge_entries)} knowledge entries → Foundry IQ"
    )
    state.schemas[6] = schema6
    state._stage_end(6)
    state.archive("stage_output", stage=6, content=schema6, author="retrospective_agent",
                  tags=["retrospective"])
    return schema6


# ─── Main Pipeline Entry ───────────────────────────────

def run_pipeline(
    user_input: str,
    submitted_by: str = "user",
) -> PipelineState:
    """Run the complete 6-Agent Pipeline。

    Args:
        user_input: Original requirement text
        submitted_by: Submitter identifier

    Returns:
        PipelineState containing all stage results
    """
    if DEMO_MODE:
        seed_demo_data()

    state = PipelineState(user_input, submitted_by)

    print(f"\n{'#'*60}")
    print(f"  Pipeline: {state.requirement_id}")
    print(f"  Input: {user_input[:80]}...")
    print(f"{'#'*60}")

    run_stage1_gatekeeper(state)
    run_stage2_value_transform(state)
    run_stage3_scenario_test(state)
    run_stage4_release_review(state)
    run_stage5_feedback_collect(state)
    run_stage6_retrospective(state)

    return state


# ─── Quick Query Mode (for Teams Bot) ──────────────────

def query_foundry_iq(question: str) -> str:
    """Quick query mode: search Foundry IQ for historical answers.

    Demo story: new hire encounters problem, asks Teams Bot directly.
    """
    results = search_similar(question, top=3)

    if not results:
        return "No records found in Foundry IQ. Submit a formal requirement to start the Pipeline."

    # Let Agent generate answer based on search results
    context = {
        "question": question,
        "foundry_iq_results": results,
    }

    result = run_agent(
        agent_file="02-value-transform.md",
        user_message=(
            f"You are acting as a knowledge base assistant, NOT as the Value Transform agent. "
            f"Answer the user's question based on the Foundry IQ search results below. "
            f"Be concise, direct, and actionable. Cite your sources.\n\n"
            f"Question: {question}\n\n"
            f"Foundry IQ results: {json.dumps(results, ensure_ascii=False, indent=2)}"
        ),
        extra_context=context,
    )

    return result["text"] or "Sorry, could not find an answer in the knowledge base."
