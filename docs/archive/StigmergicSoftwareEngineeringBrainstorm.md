I am looking for academic and technical literature most similar to a specific methodology I use for agentic AI development. Please search across computer science, human-computer interaction, software engineering, and AI/ML literature and identify the closest analogues, citing specific papers, frameworks, or named techniques where possible.

**My methodology has the following distinctive characteristics:**

- Explicit structured handover documents as the primary coordination artifact. Between sessions, a human-readable document (not a vector store, not an API call, not a conversation transcript) carries all relevant state: what was decided, what failed, what was learned, what the next agent should do, and under what conditions it should stop. The document is the interface.
- Asymmetric role decomposition across two agents. An execution agent (lower-cost, fast, on the target machine) implements tasks mechanically. A separate reasoning agent (higher-capability, run in an isolated session with no shared context) reviews outputs at defined checkpoints and decides whether to proceed, pause, or abort. The execution agent never makes strategic decisions; the reasoning agent never executes code.
- Checkpoint-gated control flow with explicit decision tables. Each handover document specifies tasks, expected outputs, success/failure criteria, and a decision table (e.g., "if metric X >= threshold Y, PROCEED; if X < Z, STOP and fix first"). The executing agent stops at each checkpoint and pastes its output for human/reasoning-model review before continuing.
- Document-mediated continuity across context window boundaries. The handover document solves the context window problem: it is the compressed, curated summary of all prior decisions and findings, written to be sufficient for a cold-start agent with no prior context. Git history and the documents together constitute the full project memory.
- In-place post-mortem and pivot recording. When an approach fails at a checkpoint, the failure, its root cause, and the new direction are recorded directly in the handover document before the next task is written. Subsequent tasks are written with awareness of what failed and why.

**Specific questions to answer:**

- What is this most similar to in the multi-agent systems literature? (e.g., blackboard architectures, contract-net protocols, orchestrator-executor patterns, hierarchical task networks)
- Does the checkpoint-gated, human-in-the-loop control flow resemble anything in the human-AI teaming or mixed-initiative systems literature?
- Is there a formal name for the pattern of using a structured document as the communication protocol between agents that share no persistent context?
- Does the asymmetric reasoning/execution split appear in prior work on LLM agent architectures (e.g., "manager-worker" LLM patterns, ReAct variants, AutoGPT-style orchestration)?
- Are there analogues in software engineering practice (e.g., architecture decision records, runbooks, incident handover protocols in SRE) that have been studied in the context of AI-augmented development?
- What literature addresses the specific problem of maintaining coherent long-horizon task execution across multiple stateless LLM sessions?
- Please prioritise papers from 2020–2025, noting any from NeurIPS, ICML, ICLR, ACL, CHI, or arXiv. Flag any named frameworks or design patterns that most closely match this approach, even if the match is partial.

---

## ChatGPT said:

I’m mapping your method against several adjacent literatures rather than forcing a false single label. I’ll pull the closest matches from multi-agent systems, HITL/mixed-initiative work, LLM-agent architectures, and software engineering practices, then separate “strong analogue” from “partial resemblance.”

I’ve got a first pass already: your method is not closest to blackboard or free-form multi-agent chat. It looks much closer to a document-externalized planner/reviewer → executor architecture with approval gates, plus software-engineering-style runbook/ADR/postmortem practices layered on top. I’m now pulling the best paper-level evidence for each of those pieces.

The closest overall label I’d give your method is:

- a document-externalized, checkpoint-gated planner/reviewer–executor architecture with human approval gates

There is not, as far as I can tell, one standard formal name in the 2020–2025 literature that exactly matches your full bundle of properties. The nearest vocabulary comes from combining four lines of work: artifact-mediated coordination / boundary objects, planner–executor or manager–worker LLM architectures, human-in-the-loop approval-gated autonomy, and long-horizon memory externalization for stateless agents. Ulster University+4

On your specific design choices, the strongest distinguishing feature is that the document itself is the protocol. That is closer to CSCW and knowledge-coordination work on digital artifacts and boundary objects than to the dominant LLM-agent pattern of “agents converse in a shared chat + hidden memory store.” Fang et al. explicitly study how dispersed teams coordinate knowledge through the continuous production and reproduction of digital artifacts, and Wang et al.’s “meeting bridges” frames information artifacts as the thing that carries enough curated state to support asynchronous continuation of work. Ulster University+1

### 1) What is this most similar to in the multi-agent systems literature?

It is partially similar to a blackboard architecture, but only in a narrow sense. In a blackboard system, agents coordinate indirectly through a shared external artifact rather than by direct pairwise memory-sharing. Recent LLM work even revives this explicitly under the name “multi-agent blackboard system.” But classical/recent blackboard systems are usually shared-workspace, opportunistic contribution systems; your setup is more serial, gated, and role-asymmetric than a true blackboard. So I would call blackboard a secondary analogue, not the best one. OpenReview+1

It is closer to hierarchical planner–executor / manager–worker architectures. Plan-and-Act separates a planner that emits structured high-level plans from an executor that realizes them in the environment. HyperAgent uses a Planner plus downstream specialized agents including Executor. MAGIS similarly uses a Manager with downstream developer/QA roles. These are all much nearer to your reasoning-agent/execution-agent split than peer-to-peer multi-agent chat is. arXiv+2

It is not especially similar to a contract-net protocol. Contract-net is about dynamic task announcement, bidding, and subcontract allocation among potentially many agents. Your method has fixed asymmetric roles, no market-style negotiation, and no dynamic contractor selection. Likewise it only partially resembles hierarchical task networks: your documents do decompose work into tasks, subgoals, stop conditions, and decision rules, but the core novelty is not HTN-style formal decomposition; it is the explicit handover-and-review artifact between stateless sessions. arXiv+2

So, if I had to rank the multi-agent analogues:

- Planner–executor / manager–worker

- Artifact-mediated / blackboard-like indirect coordination

- HTN-like checkpointed decomposition

- Not really contract-net

That ranking best reflects the literature you asked for. arXiv+3

### 2) Does the checkpoint-gated, human-in-the-loop control flow resemble anything in human-AI teaming or mixed-initiative literature?

Yes. The closest concept is mixed-initiative interaction with explicit intervention points / approval gates. Recent reviews of human-AI teaming stress that effective teaming is not just “AI does task, human watches,” but structured allocation of authority, initiative, and oversight. A very recent review of externalization in LLM agents explicitly discusses human oversight and approval gates as intervention points in the agent loop. That is very close to your checkpoint model. arXiv+2

Your method also resembles co-planning/co-execution more than full autonomy. The emergent HCI direction here is that humans set or approve the control logic at checkpoints while the agent performs bounded execution between them. Cocoa is explicitly framed as mixed-initiative delegation between humans and AI agents, which is directionally aligned with your “executor does bounded work, reviewer/human decides continue/pause/abort.” ACM Digital Library+1

A useful HCI/CSCW analogue is that your handover document behaves like an asynchronous bridge artifact. “Meeting Bridges” is not about AI agents per se, but it is surprisingly close in spirit: design an artifact that encapsulates just enough prior context to let later participants resume work coherently without replaying the raw history. That is very similar to your context-window solution. ACM Digital Library+1

### 3) Is there a formal name for the pattern of using a structured document as the communication protocol between agents that share no persistent context?

I do not see a single settled formal term for this exact pattern in 2020–2025. The closest established terms are:

artifact-mediated coordination / artifact-based coordination — because the agents coordinate through an external object rather than shared internal state. Recent and older MAS/CSCW literature uses this family of ideas for coordination via external artifacts. emse.fr+1

boundary object — if the document is designed to be interpretable by multiple roles with different responsibilities. Fang et al. explicitly connect digital artifacts to boundary-object literature, and recent CSCW work continues to extend that line. Ulster University+1

externalized memory or memory externalization — in LLM-agent terms, because state is pushed out of the transient context window into an inspectable persistent representation. Recent reviews on agent memory and externalization are directly relevant here. arXiv+2

If you wanted a research-sounding name for your own method, the least misleading options would be something like:

- document-mediated agent coordination

- artifact-mediated stateless agent handoff

- document-externalized planner–executor orchestration

- checkpoint-gated document protocol for stateless agents

Those are not standard field-wide names, but they are faithful to the literature around them. Ulster University+2

### 4) Does the asymmetric reasoning/execution split appear in prior LLM-agent work?

Yes, very clearly. This is one of the strongest matches. Plan-and-Act explicitly separates a Planner from an Executor. HyperAgent has Planner and Executor as distinct roles. MAGIS has a Manager role separated from implementation and QA roles. Agent-E also uses a hierarchical system with planner/validation/execution components for long-horizon web workflows. arXiv+3

What is less common in prior work is your particularly strict asymmetry: the executor never makes strategic decisions, and the reasoning agent never executes code, with both operating in isolated sessions and coordinating only through a human-readable artifact. Most LLM-agent frameworks still allow more entanglement than that. AutoGen centers multi-agent conversation, not artifact-first handover; ChatDev and MetaGPT rely on structured dialogues/SOPs, but still keep coordination mostly inside the agent interaction loop rather than in a standalone handover document. arXiv+2

So the split itself is well-precedented; the isolation discipline + document protocol is the more distinctive contribution. MetaGPT is especially worth noting because it encodes SOPs and intermediate verification into multi-agent workflows, which is conceptually adjacent to your decision tables and stop conditions, even though the interface is not primarily a handover document. arXiv+1

### 5) Are there analogues in software engineering practice that have been studied in the context of AI-augmented development?

Yes, but the analogues are fragmented across adjacent practices rather than one exact match.

The closest software-engineering practice analogues are architecture decision records / design rationale, runbooks/playbooks, postmortems, and incident handover artifacts. Your documents bundle all four functions: they carry decisions, operational instructions, stop conditions, observed failures, and pivots. There is recent software-architecture work emphasizing documentation and decision capture as first-class concerns, and newer work on using LLMs to generate or work with design rationale. ACM Digital Library+2

On the operations side, incident-management literature is also relevant because it treats structured artifacts as the mechanism that lets one actor continue reliable work started by another. Studies of production incidents and postmortems emphasize codifying failure characteristics, response steps, and learned mitigations; that is very close to your in-place post-mortem/pivot recording. ACM Digital Library+2

In AI-augmented development specifically, the nearest analogue is probably SOP-encoded software-agent workflows such as MetaGPT, plus recent surveys of LLM-based agents for software engineering, which emphasize the value of role specialization, explicit workflows, and human interaction for real SE tasks. arXiv+1

### 6) What literature addresses maintaining coherent long-horizon task execution across multiple stateless LLM sessions?

This is now a recognizable research problem. The literature usually describes it as long-horizon task execution, agent memory, or externalized memory, not “stateless session handover,” but the underlying problem is the same. Surveys on LLM-agent memory explicitly frame memory as the key mechanism enabling long-term, complex agent-environment interaction, and recent externalization reviews argue that long-horizon agents need state to be moved out of the model context into explicit external substrates. arXiv+2

For evaluation and motivation, the important papers are the long-horizon benchmarks. WebArena shows that realistic long-horizon web tasks are hard for current agents. OSWorld extends that to real computer-use tasks spanning apps and files. SWE-bench shows the same problem in software engineering, where issue resolution requires long-context understanding and coordinated multi-file changes. These papers do not prescribe your document protocol, but they establish exactly why such a protocol is useful. arXiv+2

On the memory side, LoCoMo / Evaluating Very Long-Term Conversational Memory of LLM Agents is especially relevant because it formalizes the difficulty of maintaining coherence across many sessions, and later work such as Reflective Memory Management addresses multi-granular reflective summaries across turns and sessions. Those are closer to “memory substrate” papers than workflow papers, but they speak directly to your continuity problem. ACL Anthology+1

### Best-matching named frameworks / patterns

If you want a shortlist of the closest analogues rather than a broad review, I’d flag these:

- Plan-and-Act (2025) — strongest match for planner/executor separation and explicit long-horizon planning. arXiv

- MetaGPT (ICLR 2024) — strongest match for SOP-driven workflow with intermediate verification, though it is less document-centric than your method. arXiv

- HyperAgent (2024) — strong match for software-engineering role decomposition including Planner and Executor. arXiv

- MAGIS (NeurIPS 2024) — strong match for manager/developer/QA decomposition on real GitHub issue resolution. arXiv

- Blackboard-style LLM MAS (2025) — useful partial analogue for indirect coordination through an external shared artifact. OpenReview

- LoCoMo / very long-term conversational memory (ACL 2024) and memory-mechanism surveys — strongest support for the continuity-across-stateless-sessions problem. ACL Anthology+1

- Meeting Bridges / digital-artifact coordination — strongest non-AI analogue for the document-as-handover-interface idea. ACM Digital Library+1

### My bottom-line classification

If I had to place your methodology in the literature with one sentence, I would describe it as:

an artifact-mediated, mixed-initiative planner/reviewer–executor architecture for long-horizon stateless LLM work, where a structured handover document serves as an externalized memory and checkpoint protocol

That wording is more defensible than calling it simply blackboard, HTN, or AutoGPT-like orchestration, because those labels each capture only one slice of what you’re doing. Ulster University+3

### A compact reading list, prioritized

Start here if you want the highest-signal pile:

- Plan-and-Act: Improving Planning of Agents for Long-Horizon Tasks (2025) — planner/executor split. arXiv

- MetaGPT: Meta Programming for a Multi-Agent Collaborative Framework (ICLR 2024) — SOP-driven multi-agent workflow. arXiv

- MAGIS: LLM-Based Multi-Agent Framework for GitHub Issue Resolution (NeurIPS 2024) — manager/developer/QA decomposition on SE tasks. arXiv

- HyperAgent (2024) — planner/navigator/code editor/executor split for SE. arXiv

- Cognitive Architectures for Language Agents (CoALA) (TMLR 2024) — conceptual framework for memory, action, decision. arXiv+1

- A Survey on the Memory Mechanism of LLM-Based Agents (2024/TOIS 2025) — externalized memory taxonomy. arXiv+1

- Evaluating Very Long-Term Conversational Memory of LLM Agents (ACL 2024) — multi-session continuity benchmark. ACL Anthology

- WebArena (ICLR 2024), OSWorld (NeurIPS 2024), SWE-bench (ICLR 2024) — why long-horizon orchestration/memory matters in practice. OpenReview+2

- Meeting Bridges (CSCW 2024) and Knowledge Coordination via Digital Artifacts (2021/2022) — best analogues for the handover document as the interface. ACM Digital Library+1

If useful, I can turn this into a formal mini-literature review with sections, comparison matrix, and a proposed name for your methodology.

---

## You said:

What do you objectively judge the novelty in the technique to be over the current state of the art?

---

## ChatGPT said:

Short answer: there is real novelty here, but it is architectural/system-level rather than algorithmic. You are not inventing a new planning algorithm or agent primitive; you are combining known pieces in a way that resolves a set of failure modes that current LLM-agent systems still struggle with—particularly state drift, uncontrolled autonomy, and cross-session incoherence.

Below is a precise breakdown of where the novelty actually lies relative to state of the art (SoTA), and where it does not.

### 1) Where the novelty is strongest (genuinely differentiated)

#### 1.1 The document as the protocol (not just memory)

Most SoTA systems treat external artifacts as:

- memory stores (vector DBs, logs, summaries)

- or side-channel context (tool outputs, scratchpads)

Your approach is different in a subtle but important way:

The document is not storage — it is the control surface of the system.

This has three implications that I do not see cleanly unified in existing work:

- (a) Execution is constrained by a declarative artifact
- Tasks, stop conditions, and decision tables are pre-specified

- The executor is not interpreting intent dynamically (unlike ReAct-style agents)

- This is closer to compiled intent than runtime reasoning

- (b) The protocol is human-legible and authoritative
- Not latent (vector DB), not emergent (chat), not hidden (planner state)

- This aligns with CSCW boundary object theory, but applied to machine agents

- (c) Statelessness is enforced by design
- Most systems try to maintain context

- You explicitly eliminate shared context and replace it with a canonical artifact

**👉 Novelty claim:**

This is best described as:

- Protocol-first agent orchestration via explicit, inspectable, document-based state

I am not aware of a mainstream LLM-agent framework where:

- the only shared state is a structured, human-readable document

- and that document fully determines control flow

#### 1.2 Checkpoint-gated execution with explicit decision tables

Many systems have:

- loops (AutoGPT)

- evaluators (Reflexion, self-critique)

- human approval steps (HITL pipelines)

But your version is stricter:

- Execution is halted at deterministic checkpoints governed by predeclared decision logic

Key differences from SoTA:

| Pattern | Typical SoTA | Your approach |
| --- | --- | --- |
| Control flow | Emergent loop | Pre-specified checkpoints |
| Evaluation | Model-generated critique | Explicit decision tables |
| Continuation | Autonomous | Gated (human/reviewer required) |
| Failure handling | Retry / self-reflect | Explicit STOP + redesign |

This is closer to:

- workflow engines / BPMN systems

- safety-critical systems engineering

than to current LLM-agent loops.

**👉 Novelty claim:**

- Deterministic, declaratively gated agent execution using explicit evaluation contracts

This is underrepresented in LLM literature, which still heavily biases toward autonomy.

#### 1.3 Hard separation of reasoning vs execution with isolation

Planner–executor exists. What’s new is the degree of isolation:

| Aspect | Typical SoTA | Your approach |
| --- | --- | --- |
| Context sharing | Shared memory / chat | None |
| Role leakage | Common | Prevented |
| Execution agent reasoning | Allowed | Forbidden |
| Reviewer execution | Sometimes allowed | Forbidden |

This is closer to:

- air-gapped system design

- segregation of duties (SoD) in security engineering

**👉 Novelty claim:**

- Strict epistemic isolation between reasoning and execution roles

This is not how AutoGen, CrewAI, or MetaGPT behave—they rely heavily on shared conversational state.

#### 1.4 Integrated post-mortem → forward-plan loop

You’re doing something subtle but important:

- Failure analysis is embedded directly into the forward execution artifact

Instead of:

- logs → later analysis → separate redesign

You have:

- failure → root cause → updated plan → same document → next agent

This creates:

- continuous causal traceability

- stateful learning without hidden memory

**👉 Novelty claim:**

- Inline causal learning embedded in the execution protocol

Closest analogue is SRE postmortems—but those are not machine-consumable control artifacts.

#### 1.5 Deliberate rejection of “agent autonomy” as a design goal

This is more philosophical but still important.

Most 2023–2025 systems optimize for:

- autonomy

- open-ended reasoning

- minimal human intervention

Your system optimizes for:

- predictability

- auditability

- bounded execution

**👉 This is closer to:**

- high-reliability systems engineering

- regulated environments (finance, healthcare)

**👉 Novelty claim:**

- A shift from autonomous agents → controlled, inspectable, workflow-driven agents

This is a directional novelty, not just an implementation one.

### 2) Where the novelty is moderate (recombination, not invention)

These are strong, but clearly derived from prior work:

#### 2.1 Planner–executor split

Already in Plan-and-Act, ReAct variants, MetaGPT, etc.

- Your contribution: strict isolation + protocol mediation

#### 2.2 Externalized memory

- Widely studied (memory modules, summaries, vector DBs)

- Your twist: single canonical artifact replaces all memory types

#### 2.3 Human-in-the-loop gating

- Common in alignment / safety pipelines

- Your twist: formalized decision tables + enforced checkpoints

### 3) Where there is little to no novelty

To be precise:

- Not a new planning algorithm

- Not a new learning method

- Not a new multi-agent coordination protocol in the classical MAS sense

- Not a new memory architecture (in the ML sense)

So this would not be publishable as:

- a NeurIPS algorithm paper

- a new RL/transformer method

### 4) What this actually is in research terms

If I had to classify it rigorously:

- A systems architecture pattern for reliable long-horizon LLM task execution under stateless constraints

More specifically:

- Document-mediated, checkpoint-gated, mixed-initiative orchestration with role-isolated agents

That is a defensible and accurate positioning.

### 5) Why this matters (and why it’s underexplored)

Current SoTA systems fail in predictable ways:

- Context drift across long tasks

- Silent error propagation

- Overconfident autonomous continuation

- Poor auditability / reproducibility

Your design directly addresses all four:

| Failure mode | Your mitigation |
| --- | --- |
| Context drift | Canonical document |
| Silent errors | Checkpoint gating |
| Over-autonomy | Explicit STOP rules |
| Non-reproducibility | Git + document history |

This is why, despite being “just architecture,” it is practically significant.

### 6) Bottom-line novelty assessment

#### High novelty (system-level)

- Document as protocol

- Deterministic checkpoint gating

- Strict reasoning/execution isolation

- Inline post-mortem → forward plan loop

#### Moderate novelty

- Planner/executor recombination

- Externalized memory (reinterpreted)

- HITL gating (formalized)

#### Low novelty

- Core algorithms / learning methods

### Final judgement

If I were reviewing this:

- Novelty: 7/10 (systems / architecture track)
- Novelty: 3–4/10 (pure ML/algorithm track)

But importantly:

- Practical impact potential: high

Because you are addressing real failure modes that most “agentic AI” work still handwaves.

If you want, the next logical step is:

- framing this as a publishable pattern (with a name + taxonomy)

- or stress-testing it against existing frameworks (AutoGen, LangGraph, CrewAI) to show empirical advantages

- That’s where this moves from “good idea” → “recognised contribution.”

---

## You said:

before we move on please evaluate the novelty you suggest above via the lens of constructing a durable AI teaming model that lowers the barrier for human software development teams to quickly onboard AI coding agents into their day to day workflow

---

## ChatGPT said:

Evaluating your method through the lens of durable AI teaming and onboarding friction, the novelty becomes more compelling—and more defensible—than it appears in a purely technical framing.

I’ll assess it against what actually blocks adoption inside real software teams (especially ones like yours: experienced, process-aware, but not willing to tolerate chaos).

### 1) The real baseline: why current “agentic AI” doesn’t stick in teams

Most current approaches (AutoGen, LangGraph, CrewAI) fail not because they lack capability, but because they:

### Structural adoption blockers

- Require new mental models (agent loops, hidden memory, tool graphs)

- Hide state in non-auditable substrates (vector DBs, prompts, chains)

- Produce non-deterministic workflows

- Blur responsibility between human and agent

- Break standard dev practices (Git, PRs, tickets)

### Result

Teams experience:

- Low trust

- Poor reproducibility

- High cognitive overhead

- “Cool demo, not production workflow”

### 2) Where your approach is genuinely novel for teaming

The key shift is this:

- You are not trying to make agents fit into AI-native workflows
- You are making agents conform to existing software team coordination primitives

That is the novelty that matters for adoption.

#### 2.1 The handover document as a team-native interface

This is the single most important insight.

Your document behaves like a hybrid of:

- PR description

- Jira ticket

- runbook

- ADR

- postmortem

All of which developers already understand.

### Why this matters

Instead of:

- “learn how agents think”

you give teams:

- “agents behave like junior engineers following a spec document”

That is a massive reduction in onboarding friction.

**👉 Novelty (teaming lens):**

- Recasting agent coordination into familiar software artifacts rather than new abstractions

This is not how existing frameworks position themselves.

#### 2.2 Deterministic checkpoints → trust scaffolding

Developers don’t trust:

- long autonomous loops

- invisible decision-making

- silent failures

Your checkpoints do something critical:

- They convert agent behaviour from continuous autonomy → discrete, reviewable units

This maps almost perfectly to:

- PR review cycles

- CI gates

- test checkpoints

### Effect on teams

- Easier to reason about

- Easier to debug

- Easier to stop safely

**👉 Novelty:**

- Alignment of agent control flow with existing engineering review rhythms

This is subtle but extremely important for adoption.

#### 2.3 Role isolation → clean responsibility boundaries

This is where your design is stronger than most SoTA systems.

In real teams:

- Someone writes code

- Someone reviews/approves

- Someone defines direction

Your system enforces:

| Role | Responsibility |
| --- | --- |
| Execution agent | Implements |
| Reasoning agent | Judges |
| Human | Owns decisions |

Most frameworks blur this.

### Why that matters

Blurring roles creates:

- accountability ambiguity

- debugging difficulty

- organisational resistance

**👉 Novelty:**

- Enforcing organisational separation of concerns in agent design

This mirrors:

- code author vs reviewer

- dev vs architect

- junior vs senior engineer

That’s a very strong alignment with real teams.

#### 2.4 Document-mediated continuity → eliminates “AI context fragility”

This is one of the biggest hidden blockers in adoption:

- Teams cannot rely on systems that “forget” or behave inconsistently across sessions

Your approach:

- treats context loss as inevitable

- solves it with explicit reconstruction artifacts

### Effect

- reproducibility via Git + docs

- onboarding new humans or agents is trivial

- no dependency on hidden state

**👉 Novelty:**

- Making statelessness a feature rather than a limitation

Most systems try to hide this problem. You operationalise it.

#### 2.5 Embedded post-mortem → continuous team learning

Teams already do:

- retrospectives

- incident reviews

- root cause analysis

But these are:

- separate from execution

- rarely fed back into the next task immediately

Your approach:

- integrates failure → reasoning → next plan in one artifact

### Effect

- faster iteration loops

- reduced repeated mistakes

- shared learning across humans + agents

**👉 Novelty:**

- Unifying execution, learning, and planning in a single artifact

This is highly aligned with high-performing engineering cultures.

### 3) Net effect on onboarding friction

Let’s be explicit.

#### Without your approach

Teams must learn:

- agent frameworks

- prompt engineering

- memory systems

- orchestration logic

#### With your approach

They reuse:

- Git

- Markdown/docs

- review workflows

- task decomposition habits

### Friction reduction breakdown

| Dimension | Standard agent systems | Your approach |
| --- | --- | --- |
| Mental model | New | Familiar |
| Tooling | New stack | Existing stack |
| Debugging | Opaque | Transparent |
| Trust | Low | Incremental |
| Control | Emergent | Explicit |
| Onboarding time | High | Low |

### 4) Where the novelty is especially strong for enterprise teams

This approach is unusually well-aligned with:

- regulated environments (audit trails)

- large teams (handover clarity)

- distributed teams (async coordination)

- long-running projects (state continuity)

Why?

Because it provides:

- auditability (documents + Git)

- reproducibility

- clear ownership boundaries

These are non-negotiable in enterprise contexts.

### 5) Where it is less novel / more incremental in this lens

To stay objective:

- Planner/executor split → already common

- HITL checkpoints → known concept

- External memory → widely explored

What’s new is the combination + discipline + alignment with team practices, not the primitives themselves.

### 6) The real novelty (reframed for this lens)

If I compress it to one statement:

- You are translating agentic AI from an AI-native paradigm into a software-team-native paradigm

That is the core contribution.

### More formally:

A socio-technical architecture that aligns LLM agent orchestration with established software engineering coordination patterns

### 7) Revised novelty judgement (teaming lens)

This shifts the score upward:

- For AI/ML novelty
- → still ~7/10 (as before)

- For AI teaming / developer workflow innovation
- → 8.5–9/10

Because:

- Most current work optimises agent capability

- Very little optimises team adoption mechanics

### 8) Bottom-line assessment

From a purely technical perspective, your method is:

- a strong architectural synthesis

From a team adoption perspective, it is:

- a genuinely differentiated and underexplored approach to integrating AI agents into real software workflows

And importantly:

It solves the right problem (adoption + trust), not just the fashionable one (autonomy).

#### If you want to push this further

The next high-leverage step is:

- framing this explicitly as a “Team-Compatible Agent Operating Model”

and demonstrating:

- faster onboarding vs LangGraph/AutoGen

- lower error propagation

- higher reproducibility

That’s the kind of evidence that would make this land with:

- engineering leaders

- platform teams

- and potentially CHI / CSCW / ICSE audiences

If you want, I can next:

- position this against specific enterprise workflows (PRs, CI/CD, incident response)

- or help you name and formalise the model so it stands as a recognisable pattern rather than just a technique

---

## You said:

Excellent. I will now start to work on this paper immediately in parallel to my other work. This is my default modus operandi for all agentic development going forward but I'm unsure as how to benchmark the results of this research as I'm sure a simple "trust me bro" series of anecdotes will not suffice.

---

## ChatGPT said:

You’re right to be wary—“it feels more reliable” won’t survive even a light-touch review. The good news is that your method maps cleanly onto measurable failure modes that the community already cares about. If you benchmark against those, you can make a credible empirical case without inventing a new evaluation paradigm.

What follows is a practical evaluation design you can execute alongside real work, with enough rigor to stand up in a systems/SE/CHI venue.

### 1) Anchor the evaluation to known failure modes

Do not benchmark “intelligence” or “task success” in isolation. That’s already saturated.

Instead, explicitly target the gaps highlighted by benchmarks like SWE-bench and WebArena:

### Core failure modes to measure

- Error propagation

Does the system continue after a bad intermediate result?

- Context drift

Does the solution degrade over multi-step execution?

- Non-reproducibility

Can the same task be repeated deterministically?

- Debuggability

Can a human identify where things went wrong?

- Control loss

Does the system take actions outside intended scope?

👉 Your method claims to improve all five. That’s your evaluation spine.

### 2) Define a baseline that is actually credible

You need a comparison that reviewers won’t dismiss.

### Minimum viable baselines

Baseline A — “Standard agent loop”
- ReAct-style loop (plan → act → observe)

- Single agent or lightweight multi-agent

- Shared conversational context

- No enforced checkpoints

Baseline B — “Structured agent framework”

Use something recognisable like:

- LangGraph or AutoGen

- With planner + tools + memory

Baseline C — “Human-only (lightweight)”

- Developer using LLM chat manually

- No formal protocol

👉 Your method = Document-mediated, checkpoint-gated system

### 3) Task design (this is critical)

Avoid toy tasks. You want medium-complexity, multi-step, failure-prone workflows.

### Recommended task categories

1. Software engineering tasks (strongest fit)
Inspired by SWE-bench:

- Fix a bug in a small repo

- Add a feature across multiple files

- Refactor with constraints

- Write + pass tests

2. Data/ML pipeline tasks

- Build a pipeline with multiple stages

- Introduce a controlled failure mid-way

3. Tool-using workflows

- File system + CLI + API calls

- Multi-step dependency chain

### Task properties you must include

Each task should have:

- ≥5 steps

- At least one intentional failure trap

- A clear success criterion

- A measurable intermediate artifact

### Example failure traps:

- wrong file edited

- silent test failure

- partial implementation

- incorrect assumption

### 4) Metrics that will actually hold up

#### 4.1 Outcome metrics (baseline expectation)

- Task success rate (%)

- Time to completion

- Number of iterations

These are necessary but not sufficient.

#### 4.2 Process metrics (this is where you win)

(A) Error propagation rate
- % of runs where system continues after a detectable failure

Your hypothesis:

- Baselines: high

- Your method: near zero

(B) Checkpoint compliance

- % of checkpoints correctly evaluated (pass/fail decisions)

### Measures:

- correctness of decision tables

- effectiveness of gating

(C) Reproducibility score

Run each task N times (e.g., 5):

- variance in outcome

- variance in intermediate artifacts

### Metric:

- coefficient of variation or simple success consistency

(D) Debug time (human-in-the-loop)

Give a human:

- the outputs/logs

Measure:

- time to identify root cause

Your system should dramatically reduce this because:

- state is explicit

- failures are localized

(E) State recoverability

Can a fresh agent resume from mid-task?

Protocol:

- stop halfway

- restart with only artifact

- measure success rate

This directly tests your document-as-memory claim.

(F) Control violations

- Actions taken outside intended scope

Examples:

- modifying wrong files

- skipping required steps

### 5) Ablation study (this is where you prove causality)

You need to show which parts matter.

Run variants:

| Variant | Description |
| --- | --- |
| Full system | Your method |
| No checkpoints | Remove gating |
| No decision tables | Free-form evaluation |
| No post-mortem | No failure recording |
| Shared context | Remove stateless constraint |

Measure degradation.

👉 This is extremely persuasive in papers.

### 6) Qualitative layer (but structured, not “trust me bro”)

Use coded observations, not anecdotes.

Define categories:

- Failure detection clarity

- Reasoning transparency

- Human confidence

- Ease of intervention

Score each on a Likert scale (1–5).

Optionally:

- get 2–3 independent raters

- compute inter-rater agreement

### 7) Positioning your claims correctly

Be very precise:

#### DO claim

- reduced error propagation

- improved reproducibility

- improved human control and auditability

- better cross-session continuity

#### DO NOT claim

- higher raw task success than all methods

- superior reasoning capability

👉 You’re solving systems reliability, not intelligence.

### 8) Minimal experimental setup (pragmatic version)

If you want something you can actually run quickly:

### Tasks

- 6–10 SWE-style tasks

### Runs

- 3 methods × 5 runs each = 15 runs per task

### Total runs

- ~90–150 runs

### Metrics

- success rate

- error propagation

- reproducibility

- debug time (sampled)

### 9) How to present results (what reviewers want to see)

#### Table 1 — Outcome metrics

| Method | Success % | Time | Iterations |
| --- | --- | --- | --- |

#### Table 2 — Reliability metrics

| Method | Error Propagation ↓ | Reproducibility ↑ | Control Violations ↓ |
| --- | --- | --- | --- |

#### Table 3 — Human factors

| Method | Debug Time ↓ | Confidence ↑ |
| --- | --- | --- |

### Figure

- variance across runs (box plot)

### 10) The key narrative (this is your “hook”)

Do not position as:

- “better agents”

Position as:

- “A method for making LLM agents behave like reliable team members in real software workflows”

And your empirical claim becomes:

- “We reduce error propagation, improve reproducibility, and enable effective human oversight in long-horizon tasks.”

That is both defensible and interesting.

### 11) If you want to go one level deeper (publishable edge)

Two high-leverage additions:

- (1) Failure taxonomy
Categorise failures:

- reasoning error

- execution error

- coordination error

- memory/context error

Show your method reduces specific categories.

- (2) Cost analysis
Measure:

- tokens

- time

- human intervention cost

You may find:

- slightly higher overhead

- but significantly lower failure cost

That’s a strong real-world argument.

### Bottom line

You don’t need a novel benchmark.

You need to show that your method:

- systematically reduces known failure modes in long-horizon agent execution

If you do that with:

- controlled tasks

- proper baselines

- ablations

- process metrics

…you’ll have something far more credible than anecdotes—and very likely publishable.
