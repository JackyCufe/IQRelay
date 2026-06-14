"""
foundry_iq.py — Azure AI Search integration module
Handles: similar requirement search, pitfall recording, experience lookup
"""
from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizableTextQuery

from config.config import (
    AI_SEARCH_ENDPOINT,
    AI_SEARCH_KEY,
    AI_SEARCH_INDEX,
    DEMO_MODE,
)


def _get_client() -> SearchClient:
    return SearchClient(
        endpoint=AI_SEARCH_ENDPOINT,
        index_name=AI_SEARCH_INDEX,
        credential=AzureKeyCredential(AI_SEARCH_KEY),
    )


def search_similar(
    query: str,
    top: int = 5,
    filter_expr: str | None = None,
) -> list[dict[str, Any]]:
    """Search historical requirements by semantic similarity.

    Args:
        query: Search text (requirement description, question, etc.)
        top: Number of results to return
        filter_expr: OData filter expression, e.g. "type eq 'bug_report'"

    Returns:
        [{"id": ..., "requirement": ..., "pitfalls": [...], ...}, ...]
    """
    if DEMO_MODE:
        return _demo_search(query, top)

    try:
        client = _get_client()
        results = client.search(
            search_text=query,
            top=top,
            filter=filter_expr,
            select=["id", "requirement_id", "requirement_title", "entry_type",
                    "stage", "revision", "status", "author", "timestamp",
                    "last_modified", "tags", "searchable_text", "content"],
        )
        out = []
        for r in results:
            d = dict(r)
            # content/retraction are stored as JSON strings — parse back to dict
            for key in ("content", "retraction"):
                v = d.get(key)
                if isinstance(v, str) and v.strip():
                    try:
                        d[key] = json.loads(v)
                    except (json.JSONDecodeError, ValueError):
                        pass
            out.append(d)
        return out
    except Exception as e:
        print(f"[foundry_iq] search failed, falling back to demo: {e}")
        return _demo_search(query, top)


def write_lesson(record: dict[str, Any]) -> str:
    """Write an experience record to Foundry IQ (used by Stage6 retrospective).

    Args:
        record: Experience record with requirement, type, pitfalls, etc.

    Returns:
        ID of the written record
    """
    if DEMO_MODE:
        doc_id = record.get("id") or f"demo-{uuid.uuid4().hex[:8]}"
        _DEMO_STORE[doc_id] = record
        print(f"[foundry_iq] DEMO: wrote lesson {doc_id}")
        return doc_id

    return archive_to_iq(
        entry_type="retrospective",
        requirement_id=record.get("id", f"req-{uuid.uuid4().hex[:8]}"),
        requirement_title=record.get("requirement", ""),
        stage=99,  # retrospective
        author="system",
        content={
            "requirement": record.get("requirement", ""),
            "type": record.get("type", "unknown"),
            "problem": record.get("problem", ""),
            "resolution": record.get("resolution", ""),
            "pitfalls": record.get("pitfalls", []),
            "push_back_reason": record.get("push_back_reason", ""),
            "stage_label": record.get("stage", ""),
        },
        tags=[record.get("type", "unknown"), record.get("category", "")],
        doc_id=record.get("id"),
    )


# ─── Unified Archive Function ───────────────────────────

def archive_to_iq(
    entry_type: str,
    requirement_id: str,
    requirement_title: str,
    stage: int,
    author: str,
    content: dict[str, Any],
    tags: list[str] | None = None,
    doc_id: str | None = None,
    revision: int = 1,
    status: str = "active",
    retraction: dict[str, Any] | None = None,
) -> str:
    """Unified archive: write a pipeline artifact to Foundry IQ.

    Uses merge_or_upload_documents — same ID = update, not duplicate.
    Every pipeline stage output, human correction, and rejection is one document.

    Args:
        entry_type: One of stage_output | human_correction | rejection_feedback |
                    survey_design | feedback_analysis | retrospective
        requirement_id: Parent requirement ID (e.g., req_f3eb1d27)
        requirement_title: Human-readable title
        stage: Pipeline stage number (1-6)
        author: Who produced this (user name or "system")
        content: Stage-specific payload
        tags: Search facet tags
        doc_id: Explicit document ID (auto-generated if None)
        revision: Revision counter (increments on re-submission)
        status: active | retracted
        retraction: If retracted, {retracted_at_stage, retracted_by, reason}

    Returns:
        Document ID written
    """
    if DEMO_MODE:
        doc_id = doc_id or f"{requirement_id}-s{stage}-{entry_type}-{uuid.uuid4().hex[:8]}"
        _DEMO_STORE[doc_id] = {
            "id": doc_id, "requirement_id": requirement_id,
            "entry_type": entry_type, "stage": stage, "content": content,
        }
        print(f"[foundry_iq] DEMO: archived {doc_id}")
        return doc_id

    doc_id = doc_id or f"{requirement_id}-s{stage}-{entry_type}"
    now = datetime.now(timezone.utc).isoformat()

    # Build searchable text from content
    searchable = _build_searchable_text(entry_type, requirement_title, content)

    doc = {
        "id": doc_id,
        "requirement_id": requirement_id,
        "requirement_title": requirement_title,
        "entry_type": entry_type,
        "stage": stage,
        "revision": revision,
        "status": status,
        "author": author,
        "timestamp": now,
        "last_modified": now,
        "tags": tags or [],
        "searchable_text": searchable,
        "content": content,
    }

    if retraction:
        doc["retraction"] = retraction

    try:
        client = _get_client()
        # Azure index stores content/retraction as JSON strings (no nested object type)
        azure_doc = dict(doc)
        if isinstance(azure_doc.get("content"), (dict, list)):
            azure_doc["content"] = json.dumps(azure_doc["content"], ensure_ascii=False)
        if isinstance(azure_doc.get("retraction"), (dict, list)):
            azure_doc["retraction"] = json.dumps(azure_doc["retraction"], ensure_ascii=False)
        client.merge_or_upload_documents([azure_doc])
        print(f"[foundry_iq] archived: {doc_id} (type={entry_type}, stage={stage}, rev={revision})")
    except Exception as e:
        print(f"[foundry_iq] archive failed (Azure unavailable), saved to demo store: {e}")
        _DEMO_STORE[doc_id] = doc

    return doc_id


def _build_searchable_text(entry_type: str, title: str, content: dict) -> str:
    """Build a searchable text blob from content for semantic retrieval."""
    parts = [title]

    if entry_type == "stage_output":
        gk = content.get("gatekeeping", {})
        if gk:
            parts.extend([
                gk.get("customer_who", ""),
                gk.get("problem", ""),
                gk.get("expected_outcome", ""),
            ])
        parts.extend([
            content.get("pm_core_value", ""),
            content.get("pm_feature_def", ""),
            content.get("rd_tech_plan", ""),
            content.get("release_value", ""),
        ])

    elif entry_type == "rejection_feedback":
        parts.extend([
            content.get("reason", ""),
            content.get("lesson", ""),
        ])

    elif entry_type == "human_correction":
        corrections = content.get("corrections", [])
        for c in corrections:
            parts.append(f"Field {c.get('field','')} changed from {c.get('old','')} to {c.get('new','')}")

    elif entry_type == "feedback_analysis":
        clusters = content.get("complaint_clusters", [])
        for c in clusters:
            parts.append(c.get("theme", ""))
            parts.append(c.get("description", ""))

    elif entry_type == "retrospective":
        entries = content.get("knowledge_entries_written", [])
        for e in entries:
            parts.append(e.get("summary", ""))

    # Filter empty and join
    return " | ".join(p for p in parts if p)


def search_by_id(doc_id: str) -> dict[str, Any] | None:
    """Look up a record by exact ID."""
    if DEMO_MODE:
        return _demo_get(doc_id)

    client = _get_client()
    try:
        return dict(client.get_document(doc_id))
    except Exception:
        return None


# ─── Demo fallbacks ─────────────────────────────────────

_DEMO_STORE: dict[str, dict[str, Any]] = {}


def _demo_search(query: str, top: int) -> list[dict[str, Any]]:
    """Demo mode: simple keyword matching."""
    results = []
    for doc in _DEMO_STORE.values():
        if query.lower() in doc.get("requirement", "").lower():
            results.append(doc)
    return results[:top]


def _demo_get(doc_id: str) -> dict[str, Any] | None:
    return _DEMO_STORE.get(doc_id)


def seed_demo_data() -> None:
    """Seed demo data for Foundry IQ knowledge base (unified schema)."""
    demos = [
        {
            "id": "mfg-req-001-s4-stage_output",
            "requirement_id": "mfg-req-001",
            "requirement_title": "QC inspection photo auto-classification of defects",
            "entry_type": "stage_output",
            "stage": 4,
            "revision": 1,
            "status": "active",
            "author": "system",
            "timestamp": "2026-05-15T10:00:00Z",
            "last_modified": "2026-05-15T10:00:00Z",
            "tags": ["customer_reported", "qc", "defect-classification"],
            "searchable_text": "QC inspection photo auto-classification of defects | "
                "Factory QC Operator Wang | Taking photos on assembly line | "
                "Operators manually classify defect types 30 seconds per photo | "
                "AI auto-classify scratch dent discoloration defects in under 2 seconds",
            "content": {
                "requirement": "QC inspection line photo auto-classification of defects",
                "type": "customer_reported",
                "problem": "Manual classification takes 30s per photo, bottleneck at 500 units/hr",
                "resolution": "AI vision system classifies scratch/dent/discoloration in <2s",
                "pitfalls": [
                    "Vision AI defect classifiers fail in dim factory lighting when trained only on well-lit lab photos",
                    "Acceptance criteria did not mandate factory-lighting training data",
                ],
            },
        },
        {
            "id": "mfg-req-002-s4-stage_output",
            "requirement_id": "mfg-req-002",
            "requirement_title": "Inventory sync 30-second delay fix",
            "entry_type": "stage_output",
            "stage": 4,
            "revision": 2,
            "status": "active",
            "author": "system",
            "timestamp": "2026-04-20T14:00:00Z",
            "last_modified": "2026-05-01T09:00:00Z",
            "tags": ["internal_improvement", "inventory"],
            "searchable_text": "Inventory sync delay fix 30 second lag | MES warehouse double-picking | "
                "ETag conflict retries cascading timeouts | Partition key redesigned per-bin v2.0",
            "content": {
                "requirement": "Inventory sync 30-second delay fix",
                "type": "internal_improvement",
                "problem": "30-second lag causing double-picking of items",
                "resolution": "Released v2.1: merged 3 API calls into single transactional batch",
                "pitfalls": [
                    "First fix only reduced polling from 30s to 10s, race condition still occurred",
                    "ETag conflict retries caused cascading timeouts when 5 concurrent pickers hit same bin",
                ],
            },
        },
        {
            "id": "mfg-req-003-s6-stage_output",
            "requirement_id": "mfg-req-003",
            "requirement_title": "ISO 9001 three-year traceable audit log",
            "entry_type": "stage_output",
            "stage": 6,
            "revision": 1,
            "status": "active",
            "author": "system",
            "timestamp": "2026-03-10T08:00:00Z",
            "last_modified": "2026-03-10T08:00:00Z",
            "tags": ["compliance", "iso9001", "audit"],
            "searchable_text": "ISO 9001 traceable audit log 3 years | "
                "Compliance requirement for auto parts supplier certification",
            "content": {
                "requirement": "ISO 9001 three-year traceable audit log",
                "type": "compliance",
                "resolution": "Audit log system with 3-year retention, indexed by lot number and timestamp",
                "pitfalls": ["Initial design stored logs in append-only without indexing, search took minutes"],
            },
        },
        {
            "id": "mfg-req-001-s2-rejection_feedback",
            "requirement_id": "mfg-req-001",
            "requirement_title": "QC inspection photo auto-classification of defects",
            "entry_type": "rejection_feedback",
            "stage": 2,
            "revision": 1,
            "status": "active",
            "author": "PM Wang",
            "timestamp": "2026-05-14T16:00:00Z",
            "last_modified": "2026-05-14T16:00:00Z",
            "tags": ["rejection", "stage2"],
            "searchable_text": "Rejection feedback Stage 2 | Missing factory lighting conditions | "
                "Always include environmental conditions as a test criterion",
            "content": {
                "action": "send_back",
                "reason": "Acceptance criteria missing factory lighting conditions — AI model trained on lab photos fails in dim factory",
                "lesson": "Always include environmental conditions (lighting, temperature, noise) as acceptance criteria for vision AI requirements",
            },
        },
        {
            "id": "ref-edi-001-stage_output",
            "requirement_id": "ref-edi-001",
            "requirement_title": "EDI 850 integration guide for Bosch",
            "entry_type": "stage_output",
            "stage": 1,
            "revision": 1,
            "status": "active",
            "author": "system",
            "timestamp": "2026-02-01T12:00:00Z",
            "last_modified": "2026-02-01T12:00:00Z",
            "tags": ["reference", "edi", "bosch"],
            "searchable_text": "EDI 850 integration Bosch purchasing orders electronic | "
                "Parse EDI 850 file create sales orders in SAP send EDI 855 acknowledgment",
            "content": {
                "requirement": "EDI 850 integration for Bosch purchasing orders",
                "type": "competitive",
                "resolution": "Standard EDI 850-to-SAP adapter with 855 acknowledgment within 5 minutes",
                "pitfalls": ["Missing EDI format version specification caused parsing failures"],
            },
        },
    ]
    for doc in demos:
        _DEMO_STORE[doc["id"]] = doc
