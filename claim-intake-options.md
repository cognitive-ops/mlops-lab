# Agentic Claims Intake: Solution Options for Davies

Draft content for the slide deck. Source: existing `Slide.pptx` (Option A / B1 / B2 slides). Options are renamed here to match the new framing.

| New name | Old slide | One-line summary |
|---|---|---|
| **Option 1** | Option A | Keep Davies OutSystems as the front end; FPT Agentic AI is the backend |
| **Option 2A** | Option B1 | FPT Agentic AI on Azure end to end; OutSystems removed |
| **Option 2B** | Option B2 | Agentic AI built inside OutSystems (ODC), with FPT AI add-ons |

---

## Slide 1. Title

**Agentic Claims Intake: Three Ways to Build It**
Options, trade-offs and recommendation
Davies / FPT Software, Insurance Practice

---

## Slide 2. Executive summary

- The goal is the same in every option: automate FNOL and claim intake with specialist AI agents. Payment, denial and settlement stay with humans.
- The real choice is **where the agents and the orchestration live**, and **who owns the user experience**.
- **Option 1** adds AI without touching what adjusters already use. It carries the lowest change risk and is the strongest fit for the agentic model.
- **Option 2A** gives the cleanest and most flexible architecture. It also carries the highest change, cost and delivery risk, because it replaces the application layer.
- **Option 2B** is the fastest to fit into today's platform. It trades away agentic flexibility and adds OutSystems cost and constraint exposure.
- **Recommendation:** start with Option 1. Design the backend API so Option 2A stays open as a later step. Keep Option 2B as a fallback if integration with the OutSystems workflow proves too hard.

---

## Slide 3. Requirements every option must meet

| Area | Requirement |
|---|---|
| Intake | FNOL and attachments parsed and normalised automatically |
| Agents | Specialist tasks: FNOL intake, document intelligence, policy and coverage, severity, fraud, compliance, comms drafts, assignment |
| Control | Human gates for adjuster and SIU. No autonomous payment, denial or settlement |
| Security | PII / PHI masked before any model call. Prompt-injection and output filtering |
| Audit | Every model call, tool call and decision recorded and replayable |
| Integration | Read-only, allow-listed access to PAS, core claims and CommHub |
| Resilience | Deadlines, retries and surge handling for peak claim volumes |

---

## Slide 4. Option 1: FPT Agentic backend + Davies OutSystems front end

**Idea:** Davies keeps the OutSystems application layer (UI, event router, workflow, rules, CommHub). FPT's agentic platform on Azure runs the AI and orchestration behind an API.

**How it works**

1. A claim event in OutSystems triggers a task through the **Command API**.
2. The **Claims Intake Orchestrator** (Azure Durable Functions state machine) calls each agent as an activity. Agents never message each other.
3. Every model call goes through **Azure API Management as the AI gateway**: PII/PHI masking, injection and output filters, model-tier routing, audit.
4. Agents use **Microsoft AI Foundry** models. Case state sits in **Cosmos DB** (`caseState`), and each agent reads and writes only its own path.
5. Results and claim state return to OutSystems through the **Read API**. Adjusters review in the UI they already know.

**Layers**

| Layer | Owner | Technology |
|---|---|---|
| Experience and workflow | Davies | OutSystems web app, event router, workflow |
| Integration | Shared | Command API, Read API, API gateway |
| Orchestration and agents | FPT | Durable Functions, 8 specialist agents |
| AI and safety | FPT | APIM AI gateway, AI Foundry |
| State and audit | FPT | Cosmos DB, Task Hub checkpoints, audit ledger |

### Pros

- **Lowest change for users.** Adjusters keep the same UI and workflow.
- **Full agentic design.** Orchestration, guardrails and agent behaviour are not limited by OutSystems.
- **Fast, low-risk start.** Davies' existing application keeps running while AI is added behind an API.
- **Easy to extend.** New claims use cases become new agents and new API calls.
- **Low OutSystems dependency.** OutSystems only calls APIs. Licence growth is not tied to AI workload.
- **Clear exit path.** The same backend can later serve a new UI (Option 2A).

### Cons

- **Integration work.** Command and Read APIs must connect cleanly to Davies' existing workflows and event router.
- **Two platforms to run.** OutSystems and Azure each need support, monitoring and release management.
- **Shared ownership is harder to manage.** Deployment, support and incident responsibility must be agreed with Davies.
- **FPT carries more platform engineering and operations** than in Option 2B.
- **UI is limited to what OutSystems can show.** Agent-specific experiences such as explainability views need OutSystems changes.
- **Latency and failure at the boundary.** Async patterns, retries and idempotency are needed between the two platforms.

---

## Slide 5. Option 2A: FPT Agentic AI on Azure, OutSystems removed

**Idea:** Replace the OutSystems application layer. FPT delivers the UI, workflow, rules and agents on Azure.

**How it works**

- A new web front end (for example React or Power Apps) replaces the OutSystems UI.
- The orchestrator, agents, AI gateway and state store are the same as Option 1, now with no OutSystems hop.
- The OutSystems event router, workflow, assessment rules and CommHub integration are rebuilt on Azure.
- Facade APIs reach PAS, core claims and CommHub read-only.

### Pros

- **Cleanest architecture.** One platform, one deployment model, one security and audit boundary.
- **Maximum flexibility.** UX, workflow and agents can be designed around AI from the start.
- **No OutSystems licence or platform constraints.** Costs follow Azure usage.
- **Simplest operations once live.** One stack to monitor, with fewer integration failure points.
- **Best long-term fit** for a growing set of agentic claims use cases.

### Cons

- **Largest scope and highest delivery risk.** UI, workflow, rules and CommHub integration all have to be rebuilt.
- **Highest change impact.** Adjusters, training, processes and testing all change.
- **Loses the existing OutSystems investment** and its low-code operating model.
- **Longer time to first value.** Little can go live until the replacement layer is ready.
- **Migration risk.** Parallel running, cut-over and regression of existing claims logic are all needed.
- **Davies needs the skills to own a custom stack**, or depends on FPT for ongoing support.
- **Needs strong Davies sponsorship** because it replaces a platform the business already runs on.

---

## Slide 6. Option 2B: Agentic AI built on OutSystems (ODC)

**Idea:** Davies ODC stays as designed. FPT adds AI components where the design has gaps, and agents run as ODC modules.

**How it works**

- The ODC event hub, event router and workflow trigger an **ODC Agent Module**.
- Inside the module: input JSON and files go to the **AI Parser Service** (Azure Document Intelligence). Parsed content goes to **Agent Storage** (instruction prompts, parsed docs, business-rule checklists). **Core Agents** and **Support Agents** run on Azure OpenAI GPT-4.1 through Foundry. **Logic Tool Services** handle third-party calls and CommHub messages.
- Each agent task is called with JSON and returns Output JSON.
- FPT adds an OutSystems-compatible integration layer and AI gateway (PII/PHI protection, context optimisation). It also adds confidence scoring with human-review routing, and better audit-log protection.

### Pros

- **Fits Davies' current platform.** The same tooling, skills and operating model carry on.
- **Low disruption.** The existing business workflow stays as is.
- **Potentially fastest integration** with the current Claims application.
- **Davies team can maintain it** using existing low-code skills.
- **One application platform** to govern.

### Cons

- **Agentic design is bent to the ODC stack.** Orchestration, state and agent-to-agent patterns are less flexible.
- **More exposure to OutSystems licensing and technical limits** (runtime, timeouts, long-running work, concurrency).
- **Platform cost grows with users, apps, capacity and environments.** Official pricing and Davies sizing are not available yet.
- **Weaker agentic controls.** Retries, durable state, surge mode and replayable audit are harder than in Durable Functions plus Cosmos DB.
- **Harder to extend.** Each new agent or use case adds OutSystems modules and cost.
- **Tied to OutSystems' AI roadmap** and to how well ODC supports AI workloads.

---

## Slide 7. Side-by-side comparison

Rating: ● strong, ◐ partial, ○ weak. Ratings are qualitative architect judgements, not measured results.

| Criterion | Option 1: FPT backend + OutSystems UI | Option 2A: FPT on Azure, no OutSystems | Option 2B: Agents on OutSystems |
|---|---|---|---|
| Fit with full agentic model | ● | ● | ◐ |
| Agent and orchestration flexibility | ● | ● | ○ |
| Change impact on adjusters | ● Low | ○ High | ● Low |
| Time to first value | ◐ | ○ | ● |
| Delivery risk | ◐ | ○ | ◐ |
| Integration complexity | ◐ API boundary | ● Single stack | ● Single platform |
| Dependency on OutSystems | ◐ UI and workflow only | ● None | ○ Full |
| Licence cost exposure | ◐ Unchanged | ● Removed | ○ Grows with use |
| Security and audit control | ● | ● | ◐ |
| Ease of extending to new use cases | ● | ● | ○ |
| Operating model | ◐ Two platforms | ● One platform | ● One platform |
| Reuse of Davies investment | ● | ○ | ● |

---

## Slide 8. Cost, effort and risk view

Qualitative only. Sizing and pricing need Davies' volumes, which are not available yet.

| Dimension | Option 1 | Option 2A | Option 2B |
|---|---|---|---|
| Build effort | Medium: backend and APIs | High: backend, UI, workflow, rules, comms | Medium: ODC modules plus AI add-ons |
| Run cost driver | Azure consumption plus current OutSystems | Azure consumption only | OutSystems capacity and licence plus Azure AI |
| Biggest risk | Boundary integration and shared ownership | Scope and migration | Platform limits and cost surprises |
| Reversibility | High. Can move to 2A later | Low. Hard to go back to OutSystems | Medium. Agent logic is locked into ODC |

Open items for Davies:

- Current OutSystems licence terms and renewal date.
- Claim volume and peak (surge) profile.
- Latency target for intake.
- Who owns production support.

---

## Slide 9. Recommendation

**Go with Option 1 first.**

1. It delivers the full agentic design without disturbing the adjuster experience.
2. It avoids the delivery risk of a rebuild (2A) and the platform lock-in of 2B.
3. The Command and Read API contract lets us swap the front end later, so **2A stays available as a phase 2** if Davies chooses to retire OutSystems.
4. **2B is the fallback** only if the OutSystems event router or workflow cannot call external APIs reliably.

**Decision triggers**

| If... | Then... |
|---|---|
| Davies wants minimal user change and fast value | Option 1 |
| Davies plans to exit OutSystems within 2-3 years | Option 1 now, then 2A |
| Davies requires everything inside OutSystems, with no Azure backend | Option 2B, accepting reduced agentic scope |

---

## Slide 10. Next steps

1. Confirm the option with Davies sponsors and architects.
2. Run a short discovery on the OutSystems integration points: event router, workflow, CommHub.
3. Agree the Command API and Read API contract.
4. Agree the ownership and support model (RACI).
5. Get OutSystems pricing and Davies sizing to complete the cost view.
6. Plan a pilot on one claim type with human gates on.

---

## Speaker-note facts to verify before presenting

- Agent count and names (8 agents) come from the Option A slide. Confirm they are still current.
- GPT-4.1 on Foundry is from the Option B2 slide. Confirm the target model.
- All ratings and effort levels are qualitative judgements, not quantified estimates.
