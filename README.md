# IQ Relay — AI Requirement Pipeline Agent

> **Agents League Hackathon 2026 — Reasoning Agents Track**
> 6-Agent collaborative pipeline. AI structures. Humans decide. The organization gets smarter every run.

---

## The Problem

When requirements move from Sales → PM → R&D → Release → Feedback, two things always go wrong:

1. **Information decays across handoffs** — by the time R&D gets it, the original customer pain is lost
2. **The same mistakes repeat** — no one knows that a similar requirement failed 6 months ago for the exact same reason

## The Solution

IQ Relay routes every requirement through 6 AI Agents in sequence. At each stage:
- AI pre-fills structured forms from unstructured input
- A human reviews, edits, and confirms via interactive Adaptive Card
- The decision (and any corrections) are written to **Foundry IQ** (Azure AI Search)

Next time a similar requirement arrives, the system surfaces historical pitfalls before Stage 1 even starts.

---

## Pipeline (6 Agents)

```
User Input
    ↓
S1  Gatekeeper        → AI extracts Who/Scenario/Problem/Expected, human confirms
    ↓
S2  Value Transform   → AI generates acceptance criteria + test cases, human edits
    ↓
S3  Scenario Test     → Human fills technical plan; AI analyzes self-test results
    ↓
S4  Release Review    → AI pre-assesses; HARD GATE blocks if scenario not verified
    ↓
S5  Feedback Collect  → AI drafts survey; human pastes responses; AI clusters results
    ↓
S6  Retrospective     → AI analyzes rework patterns → writes knowledge to Foundry IQ
```

| Stage | Agent | AI Role | Human Role |
|---|---|---|---|
| S1 | Gatekeeper | Extract 4Q, judge verdict | Edit extraction, confirm or reject |
| S2 | Value Transform | Generate acceptance criteria, test cases | Edit, set priority, confirm |
| S3 | Scenario Test | Analyze self-test results | Fill tech plan, report self-test, approve/reject/defer |
| S4 | Release Review | Pre-assess release readiness | Fill release info — **blocked if scenario unverified** |
| S5 | Feedback Collect | Draft survey questions, cluster feedback | Publish survey, paste responses |
| S6 | Retrospective | Analyze rework patterns, write knowledge entry | Review, confirm archival |

---

## Key Features

### Self-Improving Knowledge Loop (Foundry IQ)
- **13+ write points** across all 6 stages — every stage output archived to Azure AI Search
- Stage 1 automatically searches for similar historical requirements and shows pitfall alerts
- Stage 6 retrospective writes structured knowledge entries (lessons learned, root causes)
- Each new run makes the system smarter without retraining any model

### Human-in-the-Loop at Every Stage
- All stages use interactive **Adaptive Cards** — AI pre-fills, humans verify and correct
- **Stage 4 Hard Gate**: `scenario_verified = false` → code-level block, cannot proceed
- **3-round info_needed limit**: if Gatekeeper asks for more info 3 times with no resolution → forced rejection
- Rollback chain: reject at any stage → notify previous stage owner → retry / escalate / abandon

### Multi-Person Handoff Support
- Every card includes a "next person" field — tracks who owns each stage
- Rework counter tracked per requirement in Foundry IQ
- Full audit trail: every decision logged with stage, person, timestamp

---

## Microsoft Technologies

| Technology | How It's Used |
|---|---|
| **Foundry IQ** (Azure AI Search) | Organizational memory — semantic search, pitfall alerts, knowledge archival |
| **Azure Bot Service** | Bot hosting and Teams channel integration |
| **Bot Framework SDK (Python)** | Activity routing, Adaptive Card dispatch, session state |
| **Adaptive Cards** (Teams-compatible) | Interactive editable forms at every stage — 17 cards total |
| **Microsoft Teams / Web Chat** | Only interface — all input and output flows through chat |
| **DeepSeek API** (OpenAI-compatible) | Powers all 6 Agent LLM calls |

---

## Architecture

```
Teams / Azure Web Chat Test
         ↓
    bot.py  ── activity routing, session state, card dispatch
         ↓
    pipeline.py  ── 6-stage orchestrator
     ├── agent_runner.py    ── LLM calls (DeepSeek via OpenAI SDK)
     ├── foundry_iq.py      ── Azure AI Search (archive + semantic search)
     ├── work_iq.py         ── Microsoft Graph (user lookup)
     ├── cards.py           ── Adaptive Cards (17 cards, Teams-compatible)
     └── schema_builder.py  ── JSON extraction + schema validation
         ↓
    Foundry IQ (Azure AI Search)
     ── foundry-iq-index: 14-field unified schema
     ── entry_type: stage_output / retrospective / survey_design / rejection_feedback / reference_doc
     ── semantic search on every new requirement (pitfall alert before S1)
```

---

## Foundry IQ Schema

Every record written to Azure AI Search follows a unified 14-field schema:

```json
{
  "id": "req_abc123-s1-stage_output",
  "requirement_id": "req_abc123",
  "requirement_title": "Hotel robot response time under 5s",
  "entry_type": "stage_output",
  "stage": 1,
  "revision": 1,
  "status": "active",
  "author": "system",
  "timestamp": "2026-06-14T15:30:00Z",
  "tags": ["customer_reported", "performance"],
  "searchable_text": "...",
  "content": "{\"resolution\": \"...\", \"pitfalls\": [...]}",
  "retraction": null
}
```

---

## Quick Start

**Prerequisites:** Python 3.10+, ngrok, Azure Bot Service configured

```bash
# 1. Clone and install
git clone https://github.com/JackyCufe/IQ Relay.git
cd IQ Relay
pip install -r requirements.txt

# 2. Configure credentials
cp .env.template .env
# Fill in: DEEPSEEK_API_KEY, AI_SEARCH_ENDPOINT, AI_SEARCH_KEY, MicrosoftAppId, MicrosoftAppPassword

# 3. Start ngrok tunnel
ngrok http 3978
# Copy the https URL → set as Messaging Endpoint in Azure Bot Service

# 4. Start the bot
python bot.py
```

Then open **Azure Portal → Your Bot → Test in Web Chat** and send a requirement.

---

## Usage

**Submit a requirement:**
```
The front-desk receptionist needs the service robot to respond within 5 seconds
during guest check-in, because it currently takes over 20 seconds.
```

**Query the knowledge base:**
```
?hotel robot response time
?defect classification
?EDI integration
```

**Flow:** Foundry IQ alert (historical pitfalls) → S1 editable card → Confirm → S2 → ... → S6 → knowledge archived

---

## Demo Scenario

1. **Query first:** `?defect classification` → shows seed knowledge (QC pitfalls from manufacturing runs)
2. **Submit requirement** → Foundry IQ alert shows similar historical cases before pipeline starts
3. **Walk through all 6 cards** — each one shows AI pre-fill + human edit capability
4. **Stage 4 hard gate** — try submitting with scenario unverified → blocked
5. **Query again after S6** → the just-completed requirement is now in the knowledge base

---

## Project Structure

```
IQ Relay/
├── bot.py                    # Teams Bot entry — routing, session, card dispatch
├── pipeline/
│   ├── pipeline.py           # 6-stage orchestrator
│   ├── agent_runner.py       # LLM engine (DeepSeek via OpenAI SDK)
│   ├── foundry_iq.py         # Azure AI Search — archive + semantic search
│   ├── work_iq.py            # Microsoft Graph — user lookup
│   ├── cards.py              # 17 Adaptive Cards (Teams-compatible)
│   └── schema_builder.py     # JSON extraction + schema validation
├── agents/                   # 6 Agent system prompts (Markdown)
├── config/                   # config.py + pipeline_config.yaml
├── docs/                     # architecture.md + sprint-plan.md
├── scripts/                  # index rebuild + seed data utilities
├── teams-app/manifest.json   # Teams App sideload package
└── test_bot_interactive.py   # E2E test suite
```

---

Built for **Agents League Hackathon 2026** — Reasoning Agents Track
Microsoft Foundry + Azure AI Search + Bot Framework + Adaptive Cards
