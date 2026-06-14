# Architecture: Requirement Chain Agent — Microsoft Version

> Track: Reasoning Agents (Microsoft Foundry + Foundry IQ)
> IM Layer: Microsoft Teams (Adaptive Cards)
> Core Principle: "IM as the only interface — AI handles everything in between"
> Self-Improvement: Human feedback loop → writes back to Foundry IQ → system gets smarter over time

---

## System Architecture Diagram

```mermaid
graph TD
    subgraph INPUT["📥 Input Layer — Teams Only"]
        A1["👤 Sales / PM / Tester<br/>sends message in Teams chat"]
        A2["🤖 Teams Bot<br/>Bot Framework WebSocket"]
    end

    subgraph REASONING["🧠 Reasoning Layer — 6-Agent Pipeline"]
        B1["01 Gatekeeper Agent<br/>Who / Scenario / Problem / Expected Outcome<br/>❌ Blocks vague requirements"]
        B2["02 Value Transform Agent<br/>Measurable acceptance criteria<br/>e.g. success rate ≥ 95%, steps ≤ 3"]
        B3["03 Scenario Test Agent<br/>Customer-perspective test cases<br/>not feature-point testing"]
        B4["04 Release Review Agent<br/>Checks all acceptance criteria<br/>✅ Approve / 🚫 Block release"]
        B5["05 Feedback Collect Agent<br/>Structured customer feedback questionnaire"]
        B6["06 Retrospective Agent<br/>ROI analysis + next version suggestions<br/>evidence-backed, cited from real feedback"]
    end

    subgraph IQ["🔍 Foundry IQ — Organizational Memory"]
        C1["Knowledge Base<br/>Historical requirements · Past pitfalls<br/>Pushback records · How it was resolved"]
        C2["Agentic Retrieval<br/>Retrieves relevant history before each Agent runs<br/>Returns cited, grounded context"]
        C3["⚠️ Pitfall Alert<br/>Similar requirement failed before<br/>Here's what broke + who resolved it + citation"]
    end

    subgraph FEEDBACK["🔄 Self-Improvement Loop"]
        F1["Human taps 'Push Back' in Teams card<br/>+ types reason"]
        F2["Feedback Writer<br/>Structures the pushback:<br/>requirement_id · stage · reason · resolution"]
        F3["Writes back to Foundry IQ<br/>Next similar requirement retrieves this record<br/>Agent adjusts without repeating the mistake"]
    end

    subgraph OUTPUT["📤 Output Layer — Teams Only"]
        D1["📋 Adaptive Card — Approval<br/>One-click: Approve / Push back / Add info<br/>All decisions logged with timestamp + who"]
        D2["⚠️ Adaptive Card — Pitfall Alert<br/>Shown before requirement enters pipeline<br/>Includes citation: req_id · version · resolver"]
        D3["📊 Adaptive Card — Report<br/>Release verdict / Retrospective summary<br/>Deep link for full detail"]
    end

    subgraph STORAGE["💾 State & Audit Trail"]
        E1["Azure Storage<br/>Requirement state · Approval records<br/>Full JSON schema per stage"]
        E2["Azure AI Search<br/>Index backing Foundry IQ retrieval<br/>Free tier: 3 indexes · 10k docs"]
    end

    A1 --> A2
    A2 --> B1

    B1 -- "info_needed → push back card" --> D1
    B1 -- "approved" --> B2
    B2 -- "draft criteria → approval card" --> D1
    D1 -- "human approved" --> B3
    B3 --> B4
    B4 -- "blocked → alert" --> D2
    B4 -- "approved → report" --> D3
    B4 --> B5
    B5 --> B6
    B6 --> D3

    B1 & B2 & B3 --> C2
    C2 <--> C1
    C1 --> C3
    C3 --> D2

    D1 -- "push back + reason" --> F1
    F1 --> F2
    F2 --> F3
    F3 --> C1

    B1 & B2 & B3 & B4 & B5 & B6 --> E1
    E1 <--> E2
    E2 <--> C1
```

---

## The Self-Improvement Loop (Key Differentiator)

```
Normal flow:
  Requirement in → Agent reasons + Foundry IQ retrieves history → Card pushed to human

When human pushes back:
  Human taps "Push Back" + types reason in Teams card
          ↓
  Feedback Writer structures it:
  {
    "requirement_id": "req_001",
    "stage": "value_transform",
    "pushback_reason": "acceptance criteria too vague, missing metric",
    "resolution": "added: response time ≤ 2s, measured by p95 latency",
    "resolved_by": "PM Jackie",
    "timestamp": "2026-06-10T14:00:00+08:00"
  }
          ↓
  Written back into Foundry IQ knowledge base
          ↓
  Next time a similar requirement comes in:
  Agent retrieves: "Last time a similar req had vague criteria,
  PM pushed back asking for latency metric. Final version: ≤ 2s p95."
          ↓
  Agent pre-empts the problem. Fewer push backs over time.
```

**This is the "organizational memory" effect**: the system gets smarter with every human correction, without retraining any model.

---

## Layer Summary

| Layer | Responsibility | Technology |
|---|---|---|
| **Input** | Only entry point: Teams chat | Teams Bot Framework |
| **Reasoning** | 6-Agent multi-step pipeline | Azure OpenAI GPT-4o |
| **Foundry IQ** | Retrieve history with citations, surface pitfall alerts | Azure AI Foundry + AI Search |
| **Self-Improvement** | Human pushback → structured → written back to knowledge base | Feedback Writer module |
| **Output** | Only output: Adaptive Cards in Teams | Teams Adaptive Cards |
| **Storage** | State, audit trail, JSON schema per stage | Azure Storage + AI Search |

---

## Differentiation: Why This Isn't "Just Meeting Summary"

| Capability | Feishu AI / M365 Copilot | Requirement Chain Agent |
|---|---|---|
| Meeting / chat summary | ✅ | Not the focus |
| Record decisions | ✅ | ✅ |
| **Track if decisions actually resolved** | ❌ | ✅ |
| **Detect info loss across handoffs** | ❌ | ✅ Gatekeeper + JSON schema contracts |
| **"We tried this before, here's what broke"** | ❌ | ✅ Foundry IQ pitfall retrieval + citation |
| **Block release if criteria unmet** | ❌ | ✅ Release Review Agent |
| **Gets smarter from human corrections** | ❌ | ✅ Human feedback → Foundry IQ write-back |

---

## Microsoft IQ Compliance

✅ **Foundry IQ** integrated as organizational memory backbone
- Every agent queries Foundry IQ before reasoning
- Every pitfall alert includes citation (req_id, version, resolver)
- Human feedback writes back to Foundry IQ, closing the learning loop

Satisfies hard requirement: **at least one Microsoft IQ layer integrated**.
