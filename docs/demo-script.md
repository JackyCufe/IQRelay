# IQ Relay — Demo Script (5 min)

> **Format:**
> - `[ACTION]` = what you do on screen (don't say this out loud)
> - *Italic* = what you say
> - `// tip` = delivery note to stay natural

---

## SEGMENT 1 — HOOK (0:00–0:45)

`[Screen: empty Web Chat input]`

> *"Let me start with a real scenario."*

`[Type: ?customer feedback survey — hit Enter]`

`// Stay silent while results load — let the card appear`

`[Foundry IQ result card appears]`

> *"This is a knowledge record left by Sarah Chen — our former after-sales lead.
> She spent six months figuring out why customers weren't filling in post-service surveys.
> She cracked it. And then she resigned."*

`// Pause 1 second — let the viewer read the card`

> *"But her knowledge is still here.
> Three pitfalls, documented.
> 'Don't send surveys right after service closes.
> Cut to three questions.
> Never use discount coupons as incentives.'
> A new hire can find this in ten seconds."*

> *"This is what IQ Relay is built for — not just processing requirements,
> but making sure every lesson your team learns stays searchable. Forever.
> Even after the person who learned it has left."*

---

## SEGMENT 2 — WHAT IS REQFLOW (0:45–1:00)

> *"IQ Relay is a six-agent AI pipeline.
> Every requirement goes through six stages —
> Gatekeeping, PM Review, R&D, Release, Feedback, and Retrospective.
> At each stage, AI reasons and pre-fills.
> A human verifies.
> And every decision gets written back to this knowledge base.
> Let me show you the full flow."*

---

## SEGMENT 3 — SUBMIT REQUIREMENT (1:00–1:25)

`[Paste requirement:]`

```
The front-desk receptionist at our hotel needs the service robot to respond
within 5 seconds during guest check-in, because robots currently take over
20 seconds which annoys guests and increases complaints.
```

> *"I'll submit a real requirement."*

`[Foundry IQ Alert card appears]`

> *"Before Stage 1 even starts —
> the system found similar historical cases.
> Including a hotel kiosk incident from last year."*

`// Point at a specific pitfall on the card`

> *"The pitfall: the vendor blamed network latency,
> but the real cause was a synchronous API lock.
> This team now knows to profile the full call chain first."*

---

## SEGMENT 4 — S1 GATEKEEPING (1:25–1:55)

`[Stage 1 editable card appears]`

> *"Stage 1 — Gatekeeper.
> The AI extracted four structured fields from that one sentence.
> Who needs it, the scenario, the problem, and the expected outcome."*

`[Edit the Expected Outcome field — add "during peak check-in hours"]`

> *"I can edit any field before confirming —
> here I'll refine the expected outcome."*

`// Show the edit visibly, then click confirm`

`[Click: Confirm & Continue]`

---

## SEGMENT 5 — S2 PM REVIEW (1:55–2:15)

`// LLM is running — talk while waiting`

> *"Stage 2 — Value Transform.
> While the AI generates acceptance criteria and test cases..."*

`[S2 card appears]`

> *"...the PM can review and adjust the priority
> and success metrics before it goes to engineering."*

`[Click: Confirm]`

---

## SEGMENT 6 — S3 ROLLBACK DEMO (2:15–3:00)

`[S3a card appears]`

> *"Stage 3 — R&D Estimate.
> Engineering fills in the technical plan and workload."*

`[Fill in a field briefly, then click: Send Back to PM]`

> *"Now — I'm going to deliberately send this back.
> Maybe the acceptance criteria from Stage 2 were unclear."*

`[Feedback capture card appears]`

> *"The system asks why.
> This isn't just a workflow gate —
> the reason gets written to Foundry IQ immediately."*

`[Fill in feedback reason, click: Submit Feedback]`

`[Rollback notice card appears]`

`// Pause — let viewer read the card`

> *"Rollback notice.
> Stage 3 sent back to Stage 2. Rework count: 1.
> The PM sees exactly why it came back —
> and can choose to retry, escalate further, or abandon."*

`// Point at the "Why it was sent back" section`

`[Click: Modify & Resubmit]`

> *"Back to Stage 2. The loop is closed."*

`[Re-confirm S2, then confirm S3]`

---

## SEGMENT 7 — S4 HARD GATE (3:00–3:30)

`[S4 card appears]`

> *"Stage 4 — Release Review.
> I'm going to try submitting without verifying the scenario."*

`[Leave scenario_verified unchecked — click Submit]`

`// Pause — let the block message appear`

> *"Blocked."*

`// Pause 1 second`

> *"This is a hard gate enforced in code.
> Not a warning. Not a checkbox you can skip.
> The requirement cannot go to production
> until the scenario is actually tested and verified.
> No exceptions."*

`[Check scenario_verified — resubmit]`

> *"Now it passes."*

---

## SEGMENT 8 — S5 / S6 + SELF-IMPROVING LOOP (3:30–4:15)

`// Accelerate S5/S6 waiting time with FFmpeg — narrate over it`

> *"Stage 5 collects customer feedback.
> Stage 6 — the retrospective —
> analyzes the full pipeline run
> and writes structured knowledge back to Foundry IQ."*

`[After S6 completes, paste new requirement:]`

```
The hotel concierge app needs to show room availability updates in real time —
the current 30-second delay is causing double-booking incidents.
```

`[Foundry IQ Alert appears — matches the just-completed requirement]`

`// Point at the matched req_id`

> *"Different requirement. Same hotel domain.
> The alert already knows:
> a similar requirement just went through this pipeline,
> got sent back at Stage 3, and here's why.
> The system remembered."*

> *"Every run makes the next team smarter.
> Without retraining any model.
> Without asking anyone to document anything manually."*

---

## SEGMENT 9 — CLOSING (4:15–4:45)

> *"Six AI agents.
> Human verification at every stage.
> A rollback chain that captures the reason for every rejection
> and writes it to organizational memory.
> A hard gate that enforces quality in code — not in policy."*

`// Pause`

> *"The engineers who figured this out before you —
> even if they've left —
> they're still here."*

`// Pause 1 second`

> *"IQ Relay."*

`[Show GitHub URL: github.com/JackyCufe/IQ Relay]`

---

## Delivery Tips

| Moment | What to do |
|---|---|
| While typing | Stay silent — let the action speak |
| Waiting for AI | Say one sentence about what's coming next |
| Card appears | Pause 1 second before speaking — let viewer read |
| Before clicking Reject/Block | Say your intent first: *"I'm going to deliberately..."* |
| When blocked | Say *"Blocked."* — then pause — then explain |
| Rollback card | Point at specific fields, don't read every word |

---

## FFmpeg Speed-Up Reference

```bash
# Speed up seconds 180-220 (S5/S6 wait) by 10x
ffmpeg -i input.mov \
  -filter_complex "\
    [0:v]trim=0:180,setpts=PTS-STARTPTS[v1];\
    [0:v]trim=180:220,setpts=(PTS-STARTPTS)/10[v2];\
    [0:v]trim=220:9999,setpts=PTS-STARTPTS[v3];\
    [0:a]atrim=0:180,asetpts=PTS-STARTPTS[a1];\
    [0:a]atrim=180:220,asetpts=(PTS-STARTPTS)/10,volume=0[a2];\
    [0:a]atrim=220:9999,asetpts=PTS-STARTPTS[a3];\
    [v1][v2][v3]concat=n=3:v=1:a=0[v];\
    [a1][a2][a3]concat=n=3:v=0:a=1[a]" \
  -map "[v]" -map "[a]" output.mp4
```

> Replace `180` / `220` with your actual timestamps after recording.
> `volume=0` mutes the sped-up segment (no chipmunk audio).
