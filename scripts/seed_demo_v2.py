"""Seed Foundry IQ with diverse demo data (v2)."""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from config.config import AI_SEARCH_ENDPOINT, AI_SEARCH_KEY, AI_SEARCH_INDEX

client = SearchClient(AI_SEARCH_ENDPOINT, AI_SEARCH_INDEX, AzureKeyCredential(AI_SEARCH_KEY))

seeds = [
    # ── After-sales: survey response rate ──
    {
        "id": "cs-req-001-s6-stage_output",
        "requirement_id": "cs-req-001",
        "requirement_title": "Post-service survey response rate below 10%",
        "entry_type": "retrospective",
        "stage": 99,
        "revision": 1,
        "status": "active",
        "author": "Sarah Chen (After-sales Lead, resigned Nov 2025)",
        "timestamp": "2025-11-20T09:00:00Z",
        "last_modified": "2025-11-20T09:00:00Z",
        "tags": ["after-sales", "survey", "customer-feedback", "low-response-rate"],
        "searchable_text": "Post-service survey response rate low customer feedback collection after-sales WeChat QR code reminder timing incentive questionnaire",
        "content": json.dumps({
            "requirement": "Improve post-service survey response rate from 8% to 30%+",
            "type": "internal_improvement",
            "resolution": "Switched from email to WeChat mini-program survey. Added 48h delay before sending (not immediately after service). Response rate reached 34% within 6 weeks.",
            "pitfalls": [
                "Sending survey immediately after service closes gets ignored — customer is still processing the experience. Wait 24-48 hours.",
                "Long surveys (10+ questions) get abandoned at question 3. Cut to 3 core questions with optional follow-up.",
                "Discount coupons as incentive attracted low-quality responses — customers click randomly. Use lucky draw entry instead."
            ],
            "rework_count": 2,
            "stage_rejected_at": 3,
            "rejection_reason": "S3 self-test: email channel open rate was 3%, far below target. Entire channel strategy had to be rebuilt."
        }),
        "retraction": None,
    },
    # ── HR: knowledge transfer on resignation ──
    {
        "id": "hr-req-001-s5-stage_output",
        "requirement_id": "hr-req-001",
        "requirement_title": "Critical knowledge loss when senior engineers resign",
        "entry_type": "stage_output",
        "stage": 5,
        "revision": 1,
        "status": "active",
        "author": "Mike Zhang (Engineering Lead)",
        "timestamp": "2025-09-10T14:00:00Z",
        "last_modified": "2025-09-10T14:00:00Z",
        "tags": ["knowledge-transfer", "onboarding", "offboarding", "institutional-memory"],
        "searchable_text": "Senior engineer resign offboarding knowledge transfer institutional memory onboarding new hire documentation tribal knowledge experience loss",
        "content": json.dumps({
            "requirement": "Prevent critical process knowledge loss when senior team members leave the company",
            "type": "internal_improvement",
            "resolution": "Structured exit knowledge capture in final 2 weeks. All runbooks and decision logs moved to Foundry IQ. New hires query the knowledge base before asking colleagues.",
            "pitfalls": [
                "Exit interviews in the last 2 days are useless — the person is mentally checked out. Start knowledge capture 2 weeks before last day.",
                "Wiki pages go stale immediately after the author leaves. Storing knowledge as searchable Q&A entries keeps it discoverable and maintainable.",
                "New hires do not know what they do not know — they cannot search for answers to questions they have not thought of yet. Give Foundry IQ access on day 1 and assign a buddy for 30 days."
            ],
            "rework_count": 1,
            "stage_rejected_at": None,
            "rejection_reason": None
        }),
        "retraction": None,
    },
    # ── Mobile performance: checkout latency ──
    {
        "id": "app-req-002-s4-stage_output",
        "requirement_id": "app-req-002",
        "requirement_title": "Mobile checkout page load 8s — target under 2s",
        "entry_type": "stage_output",
        "stage": 4,
        "revision": 3,
        "status": "active",
        "author": "system",
        "timestamp": "2025-08-05T11:00:00Z",
        "last_modified": "2025-10-01T09:00:00Z",
        "tags": ["mobile", "performance", "checkout", "page-load", "latency"],
        "searchable_text": "Mobile app checkout page load time slow performance optimization image compression API latency BFF Redis cache response time",
        "content": json.dumps({
            "requirement": "Reduce mobile checkout page load from 8s to under 2s",
            "type": "customer_reported",
            "resolution": "Lazy-loaded product images, merged 6 sequential API calls into 1 BFF endpoint, added Redis cache for cart data. Final load time: 1.4s.",
            "pitfalls": [
                "First fix only compressed images — load time dropped to 5s, still failing. Root cause was 6 sequential API calls blocking the render, not image size.",
                "BFF endpoint had no circuit breaker — became a single point of failure. Caused P0 incident on release day.",
                "Redis cache TTL set to 24h — users saw stale cart prices after promotions updated. Cart TTL must be 5 minutes or less."
            ],
            "rework_count": 3,
            "stage_rejected_at": 4,
            "rejection_reason": "Release Review blocked twice: missing circuit breaker on first attempt, cache TTL issue on second."
        }),
        "retraction": None,
    },
    # ── Hospitality: kiosk check-in latency (similar to robot demo) ──
    {
        "id": "hosp-req-001-s6-stage_output",
        "requirement_id": "hosp-req-001",
        "requirement_title": "Lobby self-check-in kiosk 15s per transaction — guests abandon",
        "entry_type": "retrospective",
        "stage": 99,
        "revision": 1,
        "status": "active",
        "author": "system",
        "timestamp": "2025-07-12T08:00:00Z",
        "last_modified": "2025-07-12T08:00:00Z",
        "tags": ["hospitality", "kiosk", "check-in", "response-time", "guest-experience"],
        "searchable_text": "Hotel lobby kiosk self check-in timeout slow response guest complaints front desk hospitality latency transaction time PMS",
        "content": json.dumps({
            "requirement": "Self-check-in kiosk takes 15s per transaction, guests queue at front desk instead",
            "type": "customer_reported",
            "resolution": "Root cause: synchronous PMS API blocked on room inventory lock. Switched to async pre-assignment job at 6am daily. Transaction time reduced to 2.1s.",
            "pitfalls": [
                "Kiosk vendor blamed network latency — actual root cause was synchronous PMS API lock. Always profile the full call chain before accepting vendor diagnosis.",
                "Async pre-assignment breaks for same-day walk-in bookings. Fallback path took 2 additional sprint cycles to implement.",
                "Error message said 'System busy' which caused guest anxiety and front desk escalations. Changed to a progress indicator — complaint rate dropped 60% before the fix even shipped."
            ],
            "rework_count": 2,
            "stage_rejected_at": 3,
            "rejection_reason": "S3 self-test did not cover walk-in booking path. Caused production incident on launch day."
        }),
        "retraction": None,
    },
]

result = client.upload_documents(documents=seeds)
for r in result:
    status = "OK" if r.succeeded else f"FAILED: {r.errors}"
    print(f"  {r.key}: {status}")
print(f"\nDone — {len(seeds)} records uploaded")
